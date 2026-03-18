from typing import Dict, List, Optional
from agents.task_queue import TaskItem

class TaskGraph:
    def __init__(self):
        self.nodes: Dict[str, TaskItem] = {}
        self.edges: List[Dict]          = []

    def add(self, task: TaskItem):
        self.nodes[task.name] = task
        for dep in task.deps:
            self.edges.append({"from": dep, "to": task.name})

    def get(self, name: str) -> Optional[TaskItem]:
        return self.nodes.get(name)

    def roots(self) -> List[TaskItem]:
        dependent = {e["to"] for e in self.edges}
        return [t for name, t in self.nodes.items() if name not in dependent]

    def ready(self, completed: List[str]) -> List[TaskItem]:
        return [
            t for t in self.nodes.values()
            if t.status == "pending" and all(d in completed for d in t.deps)
        ]

    def topological_order(self) -> List[TaskItem]:
        visited  = set()
        ordered  = []
        def visit(name):
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

    def to_dict(self) -> Dict:
        return {
            "nodes": [t.to_dict() for t in self.nodes.values()],
            "edges": self.edges,
        }

    def summary(self) -> Dict:
        total     = len(self.nodes)
        completed = sum(1 for t in self.nodes.values() if t.status == "completed")
        failed    = sum(1 for t in self.nodes.values() if t.status == "failed")
        return {
            "total": total, "completed": completed,
            "failed": failed, "pending": total - completed - failed,
        }