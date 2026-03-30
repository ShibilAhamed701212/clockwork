"""
clockwork/agent/runtime.py
---------------------------
Main Agent Runtime engine (spec §2, §13, §14).

Orchestrates:
  - AgentRegistry   (agents.json + tasks.json)
  - TaskRouter      (capability matching + priority dispatch)
  - LockManager     (conflict prevention)
  - ValidationPipeline (rule + brain + context checks)
  - Monitoring metrics

Spec §2 flow:
    Agent Task
        ↓
    Clockwork Runtime
        ↓
    Rule Engine Validation
        ↓
    Brain Analysis
        ↓
    Repository Update
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .lock_manager import FileLockError, LockManager
from .models import Agent, Capability, Task, TaskStatus, ValidationResult
from .registry import AgentRegistry
from .router import TaskRouter, ValidationPipeline


class AgentRuntime:
    """
    Top-level facade for the Agent Runtime subsystem.

    Usage::

        rt = AgentRuntime(repo_root=Path("."))
        rt.initialise()

        rt.register_agent(Agent("claude_code", ["coding", "testing"], priority=1))
        task = rt.add_task("Implement login API", capability="coding")
        result = rt.run_task(task.task_id)
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root      = repo_root.resolve()
        self.clockwork_dir  = self.repo_root / ".clockwork"
        self.registry       = AgentRegistry(self.clockwork_dir)
        self.lock_manager   = LockManager(self.clockwork_dir)
        self.router         = TaskRouter(self.registry)
        self.pipeline       = ValidationPipeline(self.repo_root)

    # ── setup ──────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Create registry files and directory structure."""
        self.registry.initialise()
        (self.clockwork_dir / "locks").mkdir(parents=True, exist_ok=True)

    # ── agent management ───────────────────────────────────────────────────

    def register_agent(self, agent: Agent) -> bool:
        """Register a new agent. Returns False if name already taken."""
        return self.registry.register_agent(agent)

    def list_agents(self) -> list[Agent]:
        return self.registry.list_agents()

    def get_agent(self, name: str) -> Optional[Agent]:
        return self.registry.get_agent(name)

    def remove_agent(self, name: str) -> bool:
        return self.registry.remove_agent(name)

    # ── task management ────────────────────────────────────────────────────

    def add_task(
        self,
        description: str,
        capability: str = Capability.CODING,
    ) -> Task:
        """
        Create and queue a new task.

        Automatically routes it to the best available agent.
        """
        task = Task.new(description, capability)
        self.registry.add_task(task)

        # auto-dispatch if an agent is available
        assigned = self.router.dispatch(task)
        if assigned:
            pass   # task updated in registry by dispatch()

        return task

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        return self.registry.list_tasks(status)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.registry.get_task(task_id)

    # ── task execution ─────────────────────────────────────────────────────

    def run_task(self, task_id: str) -> ValidationResult:
        """
        Execute the validation pipeline for a task (spec §10).

        This represents the "controlled execution environment" — agents
        propose changes, Clockwork validates them before applying.

        Returns the ValidationResult.
        """
        task = self.registry.get_task(task_id)
        if task is None:
            return ValidationResult(
                passed=False, errors=[f"Task '{task_id}' not found."]
            )

        if task.status == TaskStatus.PENDING:
            # try to route if not yet assigned
            self.router.dispatch(task)
            task = self.registry.get_task(task_id)

        agent_name = task.assigned_agent or "unassigned"

        # acquire locks on proposed files
        locked_files: list[str] = []
        try:
            for fp in task.proposed_changes:
                clean = fp.replace("modify ", "").replace("delete ", "").strip()
                if clean:
                    try:
                        self.lock_manager.acquire(clean, agent_name)
                        locked_files.append(clean)
                    except FileLockError as e:
                        task.fail(str(e))
                        self.registry.update_task(task)
                        self.registry.log(agent_name, task, TaskStatus.FAILED, str(e))
                        return ValidationResult(passed=False, errors=[str(e)])

            # mark running
            task.start()
            self.registry.update_task(task)

            # run validation pipeline
            result = self.pipeline.validate(task)

            if result.passed:
                task.complete("Validation passed — changes approved.")
                self.registry.log(agent_name, task, TaskStatus.COMPLETED)
            else:
                task.reject(result.errors)
                self.registry.log(
                    agent_name, task, TaskStatus.REJECTED,
                    "; ".join(result.errors),
                )

            self.registry.update_task(task)
            return result

        finally:
            # always release locks
            for fp in locked_files:
                self.lock_manager.release(fp, agent_name)

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """Manually mark a task as failed (spec §14)."""
        task = self.registry.get_task(task_id)
        if task is None:
            return False
        task.fail(reason)
        self.registry.update_task(task)
        self.registry.log(task.assigned_agent or "system", task, TaskStatus.FAILED, reason)
        return True

    def retry_task(self, task_id: str) -> Optional[str]:
        """
        Retry a failed task with a different agent if available (spec §14).

        Returns the newly assigned agent name, or None.
        """
        task = self.registry.get_task(task_id)
        if task is None or task.status not in (TaskStatus.FAILED, TaskStatus.REJECTED):
            return None

        task.retry_count += 1
        task.status       = TaskStatus.PENDING
        task.result       = ""
        task.validation_errors = []
        self.registry.update_task(task)

        # exclude previous agent from routing
        old_agent = task.assigned_agent
        task.assigned_agent = ""

        assigned = self.router.dispatch(task)
        if assigned == old_agent:
            # try to find a different one
            candidates = self.registry.agents_for_capability(
                task.required_capability
            )
            others = [a for a in candidates if a.name != old_agent]
            if others:
                task.assign(others[0].name)
                self.registry.update_task(task)
                assigned = others[0].name

        return assigned

    # ── monitoring (spec §13) ──────────────────────────────────────────────

    def stats(self) -> dict:
        """Return runtime metrics."""
        task_counts = self.registry.stats()
        agents      = self.registry.list_agents()
        locks       = self.lock_manager.list_locks()
        log         = self.registry.read_log()

        return {
            "agents":          len(agents),
            "tasks_by_status": task_counts,
            "total_tasks":     sum(task_counts.values()),
            "active_locks":    len(locks),
            "log_entries":     len(log),
        }

