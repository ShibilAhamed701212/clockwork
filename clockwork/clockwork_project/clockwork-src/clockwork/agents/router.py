from __future__ import annotations

from clockwork.agents.agent_registry import AgentRecord, AgentRegistry

ACTION_CAPABILITY_MAP = {
    "scan": "scan",
    "analyze": "analysis",
    "create": "code_generation",
    "modify": "refactoring",
    "delete": "code_generation",
    "test": "testing",
    "verify": "validation",
    "debug": "debugging",
    "update": "analysis",
    "graph": "architecture",
}


class Router:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def route(self, task: dict, mode: str = "safe") -> AgentRecord | None:
        capability = self._infer_capability(task)
        candidates = self.registry.find_by_capability(capability)
        if not candidates:
            candidates = self.registry.find_by_capability("analysis")
        if not candidates:
            return None
        return self._select(candidates, mode)

    def _infer_capability(self, task: dict) -> str:
        action_type = str(task.get("action", {}).get("type", "")).lower()
        name = str(task.get("name", "")).lower()
        capability = ACTION_CAPABILITY_MAP.get(action_type, "")
        if capability:
            return capability
        for keyword, mapped in ACTION_CAPABILITY_MAP.items():
            if keyword in name:
                return mapped
        return "analysis"

    def _select(self, candidates: list[AgentRecord], mode: str) -> AgentRecord:
        idle = [agent for agent in candidates if agent.status == "idle"]
        pool = idle if idle else candidates
        if mode == "aggressive":
            return pool[0]
        return sorted(pool, key=lambda agent: agent.tasks_done)[0]

    def explain(self, task: dict) -> dict:
        capability = self._infer_capability(task)
        agents = self.registry.find_by_capability(capability)
        selected = self._select(agents, "safe") if agents else None
        return {
            "task": task.get("name", ""),
            "capability": capability,
            "selected": selected.name if selected else "none",
            "candidates": [agent.name for agent in agents],
        }

