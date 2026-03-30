"""
clockwork/agents/runtime.py
-----------------------------
v2 compatibility facade over the canonical v1 ``AgentRuntime``.

``clockwork.agents.AgentRuntime`` is a **subclass** of
``clockwork.agent.runtime.AgentRuntime`` (the authoritative implementation).
It adds the v2-style ``submit`` / ``run_pipeline`` surface while inheriting all
spec-level behaviour from the v1 core unchanged.

Rule: never add business logic here.  All agent orchestration, routing, locking,
validation, and monitoring logic lives exclusively in ``clockwork.agent.*``.
"""
from __future__ import annotations

from pathlib import Path

from clockwork.agent.runtime import AgentRuntime as LegacyAgentRuntime


class AgentRuntime(LegacyAgentRuntime):
    """v2 import-compatible runtime facade over the stable v1 runtime."""

    def __init__(self, settings: object | None = None, context: object | None = None, brain: object | None = None, rule_engine: object | None = None, repo_root: Path | None = None) -> None:
        self.settings = settings
        self.context = context
        self.brain = brain
        self.rule_engine = rule_engine
        super().__init__(repo_root=(repo_root or Path.cwd()))

    def submit(self, name: str, action: dict, priority: float = 0.5, deps: list[str] | None = None) -> dict:
        capability = str(action.get("type", "coding"))
        task = self.add_task(description=name, capability=capability)
        result = self.run_task(task.task_id)
        return {
            "success": result.passed,
            "errors": result.errors,
            "warnings": result.warnings,
            "task_id": task.task_id,
        }

    def run_pipeline(self, goal: str) -> dict:
        return {
            "goal": goal,
            "total": 0,
            "success": 0,
            "failed": 0,
            "note": "Compatibility runtime delegates to core AgentRuntime; use CLI commands for full workflows.",
        }

