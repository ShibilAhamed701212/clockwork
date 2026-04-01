"""
clockwork/agent/registry.py
----------------------------
Persistent storage for agents and tasks.

Manages:
  .clockwork/agents.json  — registered agents  (spec §4)
  .clockwork/tasks.json   — task queue          (spec §6)
  .clockwork/agent_log.json — action log        (spec §11)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import Agent, AgentLogEntry, Task, TaskStatus
from clockwork.state import append_activity


class AgentRegistry:
    """
    Reads and writes the agent registry and task queue.

    All operations are file-based so multiple processes can share
    the same .clockwork directory safely (last-write-wins for now;
    distributed locking is a future enhancement).
    """

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir  = clockwork_dir
        self.agents_path    = clockwork_dir / "agents.json"
        self.tasks_path     = clockwork_dir / "tasks.json"
        self.log_path       = clockwork_dir / "agent_log.json"

    # ── initialise ─────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Create empty registry files if they don't exist."""
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        if not self.agents_path.exists():
            self._write_agents([])
        if not self.tasks_path.exists():
            self._write_tasks([])
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")

    # ── agent CRUD ─────────────────────────────────────────────────────────

    def list_agents(self) -> list[Agent]:
        """Return all registered agents."""
        return self._read_agents()

    def get_agent(self, name: str) -> Optional[Agent]:
        """Return agent by name, or None."""
        for a in self._read_agents():
            if a.name == name:
                return a
        return None

    def register_agent(self, agent: Agent) -> bool:
        """
        Register a new agent.  Returns False if name already exists.
        """
        agents = self._read_agents()
        if any(a.name == agent.name for a in agents):
            return False
        agents.append(agent)
        self._write_agents(agents)
        return True

    def update_agent(self, agent: Agent) -> bool:
        """Update an existing agent. Returns False if not found."""
        agents = self._read_agents()
        for i, a in enumerate(agents):
            if a.name == agent.name:
                agents[i] = agent
                self._write_agents(agents)
                return True
        return False

    def remove_agent(self, name: str) -> bool:
        """Remove an agent by name. Returns False if not found."""
        agents = self._read_agents()
        new    = [a for a in agents if a.name != name]
        if len(new) == len(agents):
            return False
        self._write_agents(new)
        return True

    def agents_for_capability(self, capability: str) -> list[Agent]:
        """
        Return agents that can handle the given capability,
        sorted by priority ascending (lower = higher priority).
        """
        return sorted(
            [a for a in self._read_agents() if a.can_handle(capability)],
            key=lambda a: a.priority,
        )

    # ── task CRUD ──────────────────────────────────────────────────────────

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        """Return all tasks, optionally filtered by status."""
        tasks = self._read_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self._read_tasks():
            if t.task_id == task_id:
                return t
        return None

    def add_task(self, task: Task) -> Task:
        """Append a task to the queue and return it."""
        tasks = self._read_tasks()
        tasks.append(task)
        self._write_tasks(tasks)
        return task

    def update_task(self, task: Task) -> bool:
        """Persist a modified task. Returns False if not found."""
        tasks = self._read_tasks()
        for i, t in enumerate(tasks):
            if t.task_id == task.task_id:
                tasks[i] = task
                self._write_tasks(tasks)
                return True
        return False

    def pending_tasks(self) -> list[Task]:
        return self.list_tasks(TaskStatus.PENDING)

    def active_tasks(self) -> list[Task]:
        return [
            t for t in self._read_tasks()
            if t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)
        ]

    def stats(self) -> dict[str, int]:
        """Return per-status task counts."""
        tasks = self._read_tasks()
        counts: dict[str, int] = {}
        for t in tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
        return counts

    # ── agent log ──────────────────────────────────────────────────────────

    def log(
        self,
        agent: str,
        task: Task,
        status: str,
        message: str = "",
    ) -> None:
        """Append one entry to agent_log.json."""
        try:
            entries = json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            entries = []

        entry = AgentLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            task_id=task.task_id,
            task_desc=task.description,
            status=status,
            message=message,
        )
        entries.append(entry.to_dict())

        self.log_path.write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )

        append_activity(
            self.clockwork_dir,
            actor=agent,
            action="task_status_update",
            status=status,
            details={
                "task_id": task.task_id,
                "task": task.description,
                "message": message,
            },
        )

    def read_log(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    # ── private I/O ────────────────────────────────────────────────────────

    def _read_agents(self) -> list[Agent]:
        if not self.agents_path.exists():
            return []
        try:
            data = json.loads(self.agents_path.read_text(encoding="utf-8"))
            raw  = data if isinstance(data, list) else data.get("agents", [])
            return [Agent.from_dict(a) for a in raw]
        except Exception:
            return []

    def _write_agents(self, agents: list[Agent]) -> None:
        self.agents_path.write_text(
            json.dumps({"agents": [a.to_dict() for a in agents]}, indent=2),
            encoding="utf-8",
        )

    def _read_tasks(self) -> list[Task]:
        if not self.tasks_path.exists():
            return []
        try:
            data = json.loads(self.tasks_path.read_text(encoding="utf-8"))
            raw  = data if isinstance(data, list) else data.get("tasks", [])
            return [Task.from_dict(t) for t in raw]
        except Exception:
            return []

    def _write_tasks(self, tasks: list[Task]) -> None:
        self.tasks_path.write_text(
            json.dumps({"tasks": [t.to_dict() for t in tasks]}, indent=2),
            encoding="utf-8",
        )

