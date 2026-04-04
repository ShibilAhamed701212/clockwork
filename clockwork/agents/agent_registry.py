from __future__ import annotations

import time
from dataclasses import dataclass, field

CAPABILITIES = {
    "code_generation": ["coding_agent", "general_agent"],
    "debugging": ["debug_agent", "coding_agent"],
    "refactoring": ["coding_agent", "general_agent"],
    "testing": ["test_agent", "coding_agent"],
    "architecture": ["reasoning_agent", "general_agent"],
    "frontend": ["frontend_agent", "coding_agent"],
    "backend": ["coding_agent", "general_agent"],
    "database": ["db_agent", "coding_agent"],
    "scan": ["scanner_agent", "general_agent"],
    "validation": ["validation_agent", "general_agent"],
    "analysis": ["reasoning_agent", "general_agent"],
}


@dataclass
class AgentRecord:
    name: str
    capabilities: list[str]
    mode: str = "safe"
    status: str = "idle"
    tasks_done: int = 0
    registered: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "capabilities": self.capabilities,
            "mode": self.mode,
            "status": self.status,
            "tasks_done": self.tasks_done,
            "registered": self.registered,
        }


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentRecord] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            AgentRecord("general_agent", list(CAPABILITIES.keys())),
            AgentRecord("coding_agent", ["code_generation", "debugging", "refactoring", "backend"]),
            AgentRecord("test_agent", ["testing", "validation"]),
            AgentRecord("reasoning_agent", ["architecture", "analysis"]),
            AgentRecord("frontend_agent", ["frontend", "code_generation"]),
            AgentRecord("db_agent", ["database"]),
            AgentRecord("scanner_agent", ["scan", "analysis"]),
            AgentRecord("validation_agent", ["validation"]),
            AgentRecord("debug_agent", ["debugging"]),
        ]
        for agent in defaults:
            self._agents[agent.name] = agent

    def register(self, agent: AgentRecord) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentRecord | None:
        return self._agents.get(name)

    def find_by_capability(self, capability: str) -> list[AgentRecord]:
        candidates = CAPABILITIES.get(capability, ["general_agent"])
        return [self._agents[name] for name in candidates if name in self._agents]

    def all(self) -> list[dict]:
        return [agent.to_dict() for agent in self._agents.values()]

    def set_status(self, name: str, status: str) -> None:
        if name in self._agents:
            self._agents[name].status = status

    def increment_done(self, name: str) -> None:
        if name in self._agents:
            self._agents[name].tasks_done += 1

