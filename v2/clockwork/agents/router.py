from typing import Dict, List, Optional
from agents.agent_registry import AgentRegistry, AgentRecord

ACTION_CAPABILITY_MAP = {
    "scan":     "scan",
    "analyze":  "analysis",
    "create":   "code_generation",
    "modify":   "refactoring",
    "delete":   "code_generation",
    "test":     "testing",
    "verify":   "validation",
    "debug":    "debugging",
    "update":   "analysis",
    "graph":    "architecture",
}

class Router:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def route(self, task: Dict, mode: str = "safe") -> Optional[AgentRecord]:
        capability = self._infer_capability(task)
        candidates = self.registry.find_by_capability(capability)
        if not candidates:
            candidates = self.registry.find_by_capability("analysis")
        if not candidates:
            return None
        selected = self._select(candidates, mode)
        print("[Router] Task '" + task.get("name","?") + "' -> " + selected.name + " (" + capability + ")")
        return selected

    def _infer_capability(self, task: Dict) -> str:
        action_type = task.get("action", {}).get("type", "").lower()
        name        = task.get("name", "").lower()
        cap = ACTION_CAPABILITY_MAP.get(action_type, "")
        if cap:
            return cap
        for keyword, capability in ACTION_CAPABILITY_MAP.items():
            if keyword in name:
                return capability
        return "analysis"

    def _select(self, candidates: List[AgentRecord], mode: str) -> AgentRecord:
        idle = [a for a in candidates if a.status == "idle"]
        pool = idle if idle else candidates
        if mode == "aggressive":
            return pool[0]
        return sorted(pool, key=lambda a: a.tasks_done)[0]

    def explain(self, task: Dict) -> Dict:
        cap      = self._infer_capability(task)
        agents   = self.registry.find_by_capability(cap)
        selected = self._select(agents, "safe") if agents else None
        return {
            "task":        task.get("name", ""),
            "capability":  cap,
            "selected":    selected.name if selected else "none",
            "candidates":  [a.name for a in agents],
        }