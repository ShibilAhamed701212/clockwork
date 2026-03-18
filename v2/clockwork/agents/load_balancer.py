from typing import Dict, List
from agents.agent_registry import AgentRegistry, AgentRecord

class LoadBalancer:
    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    def distribute(self, tasks: List[Dict]) -> List[Dict]:
        assignments = []
        for task in tasks:
            agent = self._least_loaded()
            assignments.append({
                "task":  task,
                "agent": agent.name if agent else "general_agent",
            })
            if agent:
                self.registry.set_status(agent.name, "busy")
        return assignments

    def _least_loaded(self) -> AgentRecord:
        agents = [
            a for a in self.registry._agents.values()
            if a.status == "idle"
        ]
        if not agents:
            agents = list(self.registry._agents.values())
        return sorted(agents, key=lambda a: a.tasks_done)[0]

    def rebalance(self, assignments: List[Dict]) -> List[Dict]:
        all_agents = list(self.registry._agents.values())
        if not all_agents:
            return assignments
        for i, assignment in enumerate(assignments):
            idx = i % len(all_agents)
            assignments[i]["agent"] = all_agents[idx].name
        return assignments

    def stats(self) -> Dict:
        agents = self.registry.all()
        return {
            "total_agents": len(agents),
            "idle":   sum(1 for a in agents if a["status"] == "idle"),
            "busy":   sum(1 for a in agents if a["status"] == "busy"),
            "load":   {a["name"]: a["tasks_done"] for a in agents},
        }