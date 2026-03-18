import time
from typing import Dict, List, Optional

CAPABILITIES = {
    "code_generation":   ["coding_agent", "general_agent"],
    "debugging":         ["debug_agent",  "coding_agent"],
    "refactoring":       ["coding_agent", "general_agent"],
    "testing":           ["test_agent",   "coding_agent"],
    "architecture":      ["reasoning_agent", "general_agent"],
    "frontend":          ["frontend_agent",  "coding_agent"],
    "backend":           ["coding_agent",    "general_agent"],
    "database":          ["db_agent",        "coding_agent"],
    "scan":              ["scanner_agent",   "general_agent"],
    "validation":        ["validation_agent","general_agent"],
    "analysis":          ["reasoning_agent", "general_agent"],
}

class AgentRecord:
    def __init__(self, name: str, capabilities: List[str], mode: str = "safe"):
        self.name         = name
        self.capabilities = capabilities
        self.mode         = mode
        self.status       = "idle"
        self.tasks_done   = 0
        self.registered   = time.time()

    def to_dict(self) -> Dict:
        return {
            "name":         self.name,
            "capabilities": self.capabilities,
            "mode":         self.mode,
            "status":       self.status,
            "tasks_done":   self.tasks_done,
            "registered":   self.registered,
        }


class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentRecord] = {}
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            AgentRecord("general_agent",    list(CAPABILITIES.keys())),
            AgentRecord("coding_agent",     ["code_generation","debugging","refactoring","backend"]),
            AgentRecord("test_agent",       ["testing","validation"]),
            AgentRecord("reasoning_agent",  ["architecture","analysis"]),
            AgentRecord("frontend_agent",   ["frontend","code_generation"]),
            AgentRecord("db_agent",         ["database"]),
            AgentRecord("scanner_agent",    ["scan","analysis"]),
            AgentRecord("validation_agent", ["validation"]),
            AgentRecord("debug_agent",      ["debugging"]),
        ]
        for a in defaults:
            self._agents[a.name] = a

    def register(self, agent: AgentRecord):
        self._agents[agent.name] = agent
        print("[AgentRegistry] Registered: " + agent.name)

    def get(self, name: str) -> Optional[AgentRecord]:
        return self._agents.get(name)

    def find_by_capability(self, capability: str) -> List[AgentRecord]:
        candidates = CAPABILITIES.get(capability, ["general_agent"])
        return [self._agents[n] for n in candidates if n in self._agents]

    def all(self) -> List[Dict]:
        return [a.to_dict() for a in self._agents.values()]

    def set_status(self, name: str, status: str):
        if name in self._agents:
            self._agents[name].status = status

    def increment_done(self, name: str):
        if name in self._agents:
            self._agents[name].tasks_done += 1