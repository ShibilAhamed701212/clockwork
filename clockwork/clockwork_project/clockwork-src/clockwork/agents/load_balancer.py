"""
clockwork/agents/load_balancer.py
-----------------------------------
v2 compatibility facade — round-robin / least-loaded task distributor.

Provides the v2 ``LoadBalancer`` interface over the v2 ``AgentRegistry``.
Core agent-selection and priority dispatch lives in ``clockwork.agent.router``;
this module is a thin distribution helper for v2 callers.
"""
from __future__ import annotations

from clockwork.agents.agent_registry import AgentRecord, AgentRegistry


class LoadBalancer:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def distribute(self, tasks: list[dict]) -> list[dict]:
        assignments: list[dict] = []
        for task in tasks:
            agent = self._least_loaded()
            assignments.append({"task": task, "agent": agent.name if agent else "general_agent"})
            if agent:
                self.registry.set_status(agent.name, "busy")
        return assignments

    def _least_loaded(self) -> AgentRecord:
        agents = [agent for agent in self.registry._agents.values() if agent.status == "idle"]
        if not agents:
            agents = list(self.registry._agents.values())
        return sorted(agents, key=lambda agent: agent.tasks_done)[0]

    def rebalance(self, assignments: list[dict]) -> list[dict]:
        all_agents = list(self.registry._agents.values())
        if not all_agents:
            return assignments
        for idx, assignment in enumerate(assignments):
            assignment["agent"] = all_agents[idx % len(all_agents)].name
        return assignments

    def stats(self) -> dict:
        agents = self.registry.all()
        return {
            "total_agents": len(agents),
            "idle": sum(1 for agent in agents if agent["status"] == "idle"),
            "busy": sum(1 for agent in agents if agent["status"] == "busy"),
            "load": {agent["name"]: agent["tasks_done"] for agent in agents},
        }

