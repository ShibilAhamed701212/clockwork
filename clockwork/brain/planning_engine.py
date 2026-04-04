from __future__ import annotations

import time
import uuid

from clockwork.brain.prioritization import PrioritizationEngine


class Task:
    def __init__(self, name: str, action: dict, deps: list[str] | None = None) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.action = action
        self.deps = deps or []
        self.status = "pending"
        self.created = time.time()
        self.result = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "deps": self.deps,
            "status": self.status,
            "created": self.created,
        }


class PlanningEngine:
    def __init__(self) -> None:
        self.prioritizer = PrioritizationEngine()
        self.tasks: list[Task] = []

    def decompose(self, goal: str, context: dict) -> list[Task]:
        del context
        plan = [
            Task("scan_repository", {"type": "scan", "target": "."}),
            Task("update_context", {"type": "update", "target": ".clockwork/context.yaml"}, ["scan_repository"]),
            Task("validate_rules", {"type": "verify", "target": "rules"}, ["update_context"]),
            Task("build_graph", {"type": "graph", "target": "."}, ["validate_rules"]),
        ]
        if "execute" in goal.lower() or "run" in goal.lower():
            plan.append(Task("execute_agents", {"type": "agent", "target": goal}, ["build_graph"]))
        self.tasks = plan
        return plan

    def order(self, tasks: list[Task]) -> list[Task]:
        ordered: list[Task] = []
        remaining = list(tasks)
        done_ids: set[str] = set()
        max_iter = len(tasks) * 2
        idx = 0
        while remaining and idx < max_iter:
            idx += 1
            for task in list(remaining):
                if all(dep in done_ids for dep in task.deps):
                    ordered.append(task)
                    done_ids.add(task.name)
                    remaining.remove(task)
        ordered.extend(remaining)
        return ordered

    def to_graph(self, tasks: list[Task]) -> dict:
        return {
            "nodes": [task.to_dict() for task in tasks],
            "edges": [{"from": dep, "to": task.name} for task in tasks for dep in task.deps],
        }

    def next_ready(self, tasks: list[Task], completed: list[str]) -> list[Task]:
        return [task for task in tasks if task.status == "pending" and all(dep in completed for dep in task.deps)]

