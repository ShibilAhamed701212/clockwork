from __future__ import annotations

from clockwork.agents.agent_registry import AgentRegistry
from clockwork.agents.router import Router
from clockwork.agents.sandbox.executor import SandboxExecutor
from clockwork.agents.task_graph import TaskGraph
from clockwork.agents.task_queue import TaskItem


class SwarmCoordinator:
    def __init__(self, registry: AgentRegistry, dry_run: bool = False) -> None:
        self.registry = registry
        self.router = Router(registry)
        self.executor = SandboxExecutor(dry_run=dry_run)
        self.results: list[dict] = []

    def run(self, tasks: list[TaskItem], mode: str = "safe") -> list[dict]:
        graph = TaskGraph()
        for task in tasks:
            graph.add(task)

        ordered = graph.topological_order()
        for task in ordered:
            agent = self.router.route(task.to_dict(), mode=mode)
            agent_name = agent.name if agent else "general_agent"
            result = self.executor.execute(task.to_dict(), agent_name=agent_name)
            if result.success:
                task.status = "completed"
                task.result = result.to_dict()
                self.registry.increment_done(agent_name)
                self.registry.set_status(agent_name, "idle")
            else:
                task.status = "failed"
                if mode == "safe":
                    break

            self.results.append(
                {
                    "task": task.name,
                    "agent": agent_name,
                    "success": result.success,
                    "explanation": result.explanation,
                }
            )
        return self.results

    def parallel_run(self, task_groups: list[list[TaskItem]]) -> list[dict]:
        # Keep compatibility surface simple and deterministic in this adapter.
        all_results: list[dict] = []
        for group in task_groups:
            all_results.extend(self.run(group, mode="aggressive"))
        return all_results

