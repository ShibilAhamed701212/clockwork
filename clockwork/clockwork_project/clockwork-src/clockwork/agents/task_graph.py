"""
clockwork/agents/task_graph.py
--------------------------------
v2 compatibility facade — topological dependency graph over ``TaskItem`` objects.

Provides the v2 ``TaskGraph`` interface for tracking inter-task dependencies.
Core task orchestration logic lives in ``clockwork.agent.runtime``; this module
is a lightweight dependency-resolution helper for v2 callers.
"""
from __future__ import annotations

from clockwork.agents.task_queue import TaskItem


class TaskGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, TaskItem] = {}
        self.edges: list[dict[str, str]] = []

    def add(self, task: TaskItem) -> None:
        self.nodes[task.name] = task
        for dep in task.deps:
            self.edges.append({"from": dep, "to": task.name})

    def get(self, name: str) -> TaskItem | None:
        return self.nodes.get(name)

    def roots(self) -> list[TaskItem]:
        dependent = {edge["to"] for edge in self.edges}
        return [task for name, task in self.nodes.items() if name not in dependent]

    def ready(self, completed: list[str]) -> list[TaskItem]:
        return [
            task
            for task in self.nodes.values()
            if task.status == "pending" and all(dep in completed for dep in task.deps)
        ]

    def topological_order(self) -> list[TaskItem]:
        visited: set[str] = set()
        ordered: list[TaskItem] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            task = self.nodes.get(name)
            if task:
                for dep in task.deps:
                    visit(dep)
                ordered.append(task)

        for name in self.nodes:
            visit(name)
        return ordered

    def to_dict(self) -> dict:
        return {"nodes": [task.to_dict() for task in self.nodes.values()], "edges": self.edges}

    def summary(self) -> dict:
        total = len(self.nodes)
        completed = sum(1 for task in self.nodes.values() if task.status == "completed")
        failed = sum(1 for task in self.nodes.values() if task.status == "failed")
        return {"total": total, "completed": completed, "failed": failed, "pending": total - completed - failed}

