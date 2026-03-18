import time
import uuid
from typing import Dict, List, Optional
from brain.prioritization import PrioritizationEngine

class Task:
    def __init__(self, name: str, action: Dict, deps: List[str] = []):
        self.id        = str(uuid.uuid4())[:8]
        self.name      = name
        self.action    = action
        self.deps      = deps
        self.status    = "pending"
        self.created   = time.time()
        self.result    = None

    def to_dict(self) -> Dict:
        return {
            "id":      self.id,
            "name":    self.name,
            "action":  self.action,
            "deps":    self.deps,
            "status":  self.status,
            "created": self.created,
        }


class PlanningEngine:
    def __init__(self):
        self.prioritizer = PrioritizationEngine()
        self.tasks: List[Task] = []

    def decompose(self, goal: str, context: Dict) -> List[Task]:
        arch   = context.get("repository", {}).get("architecture", "unknown")
        skills = context.get("skills", {}).get("required", [])
        plan   = []

        plan.append(Task("scan_repository",   {"type": "scan",   "target": "."}))
        plan.append(Task("update_context",    {"type": "update", "target": ".clockwork/context.yaml"}, ["scan_repository"]))
        plan.append(Task("validate_rules",    {"type": "verify", "target": "rules"},                   ["update_context"]))
        plan.append(Task("build_graph",       {"type": "graph",  "target": "."},                       ["validate_rules"]))

        if "execute" in goal.lower() or "run" in goal.lower():
            plan.append(Task("execute_agents", {"type": "agent", "target": goal}, ["build_graph"]))

        self.tasks = plan
        return plan

    def order(self, tasks: List[Task]) -> List[Task]:
        ordered = []
        remaining = list(tasks)
        done_ids = set()
        max_iter = len(tasks) * 2
        i = 0
        while remaining and i < max_iter:
            i += 1
            for t in list(remaining):
                if all(dep in done_ids for dep in t.deps):
                    ordered.append(t)
                    done_ids.add(t.name)
                    remaining.remove(t)
        ordered.extend(remaining)
        return ordered

    def to_graph(self, tasks: List[Task]) -> Dict:
        return {
            "nodes": [t.to_dict() for t in tasks],
            "edges": [
                {"from": dep, "to": t.name}
                for t in tasks for dep in t.deps
            ],
        }

    def next_ready(self, tasks: List[Task], completed: List[str]) -> List[Task]:
        return [
            t for t in tasks
            if t.status == "pending" and all(d in completed for d in t.deps)
        ]