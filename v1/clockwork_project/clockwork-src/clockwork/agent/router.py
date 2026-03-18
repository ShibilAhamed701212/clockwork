"""
clockwork/agent/router.py
--------------------------
Task router and validation pipeline for the Agent Runtime (spec §7, §10).

Routing algorithm (spec §7):
    1. match capability
    2. select highest priority agent
    3. dispatch task

Validation pipeline (spec §10):
    Agent Proposal
        ↓
    Rule Engine
        ↓
    Brain Analysis
        ↓
    Context Validation
        ↓
    Repository Update
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .models import Agent, Task, TaskStatus, ValidationResult
from .registry import AgentRegistry


class TaskRouter:
    """
    Routes pending tasks to the best-fit registered agent.

    Usage::

        router = TaskRouter(registry)
        agent  = router.route(task)
        if agent:
            task.assign(agent.name)
            registry.update_task(task)
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def route(self, task: Task) -> Optional[Agent]:
        """
        Find the best agent for *task* based on capability + priority.

        Returns None if no suitable agent is registered.
        """
        candidates = self._registry.agents_for_capability(
            task.required_capability
        )
        if not candidates:
            return None

        # exclude agents that already have too many active tasks (>3)
        active = self._registry.active_tasks()
        busy: dict[str, int] = {}
        for t in active:
            busy[t.assigned_agent] = busy.get(t.assigned_agent, 0) + 1

        available = [a for a in candidates if busy.get(a.name, 0) < 3]
        if not available:
            # fall back to least-busy agent
            available = sorted(candidates, key=lambda a: busy.get(a.name, 0))

        return available[0]

    def dispatch(self, task: Task) -> Optional[str]:
        """
        Route and assign a task in one step.

        Returns the assigned agent name, or None if no agent available.
        """
        agent = self.route(task)
        if agent is None:
            return None
        task.assign(agent.name)
        self._registry.update_task(task)
        self._registry.log(agent.name, task, TaskStatus.ASSIGNED)
        return agent.name


class ValidationPipeline:
    """
    Runs the spec §10 validation pipeline on a task's proposed changes.

    Pipeline stages:
        1. Rule Engine validation
        2. Brain Analysis
        3. Context validation

    Each stage may add errors or warnings to the result.
    Gracefully skips stages whose subsystems are not available.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root
        self.clockwork_dir = repo_root / ".clockwork"

    def validate(self, task: Task) -> ValidationResult:
        """
        Run all pipeline stages against the task's proposed_changes.

        Returns a ValidationResult with passed=True only when all
        stages pass with no errors.
        """
        t0     = time.perf_counter()
        errors:   list[str] = []
        warnings: list[str] = []

        # ── Stage 1: Rule Engine ───────────────────────────────────────────
        rule_errors, rule_warnings = self._run_rule_engine(task)
        errors.extend(rule_errors)
        warnings.extend(rule_warnings)

        # ── Stage 2: Brain Analysis ────────────────────────────────────────
        brain_errors, brain_warnings = self._run_brain(task)
        errors.extend(brain_errors)
        warnings.extend(brain_warnings)

        # ── Stage 3: Context Validation ────────────────────────────────────
        ctx_errors = self._run_context_validation(task)
        errors.extend(ctx_errors)

        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed > 200:
            warnings.append(
                f"Validation took {elapsed:.0f} ms (target: <200 ms)"
            )

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ── Stage implementations ──────────────────────────────────────────────

    def _run_rule_engine(self, task: Task) -> tuple[list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []
        try:
            from clockwork.rules import RuleEngine
            engine = RuleEngine(self.repo_root)
            report = engine.evaluate(list(task.proposed_changes))
            if not report.passed:
                errors.extend([str(v) for v in report.blocking_violations])
            warnings.extend([str(v) for v in report.warnings])
        except ImportError:
            warnings.append("Rule Engine not available — skipping rule checks.")
        except Exception as exc:
            warnings.append(f"Rule Engine error: {exc}")
        return errors, warnings

    def _run_brain(self, task: Task) -> tuple[list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []

        # check if any proposed change would delete a file that other
        # modules depend on (uses knowledge graph if available)
        db_path = self.clockwork_dir / "knowledge_graph.db"
        if db_path.exists():
            try:
                from clockwork.graph import GraphEngine
                engine = GraphEngine(self.repo_root)
                try:
                    q = engine.query()
                    for change in task.proposed_changes:
                        if change.lower().startswith("delete "):
                            fp = change[7:].strip()
                            safe, reasons = q.is_safe_to_delete(fp)
                            if not safe:
                                errors.extend(reasons)
                finally:
                    engine.close()
            except Exception as exc:
                warnings.append(f"Brain graph check error: {exc}")
        return errors, warnings

    def _run_context_validation(self, task: Task) -> list[str]:
        errors: list[str] = []
        try:
            from clockwork.context import ContextEngine
            engine = ContextEngine(self.clockwork_dir)
            issues = engine.validate()
            if issues:
                errors.extend(issues)
        except ImportError:
            pass
        except Exception as exc:
            errors.append(f"Context validation error: {exc}")
        return errors

