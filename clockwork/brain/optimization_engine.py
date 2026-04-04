from __future__ import annotations


class OptimizationEngine:
    def optimize_plan(self, tasks: list[dict], mode: str = "safe") -> list[dict]:
        if mode == "safe":
            return self._safe_order(tasks)
        if mode == "aggressive":
            return self._parallel_groups(tasks)
        return tasks

    def _safe_order(self, tasks: list[dict]) -> list[dict]:
        return sorted(tasks, key=lambda task: task.get("priority_score", 0), reverse=True)

    def _parallel_groups(self, tasks: list[dict]) -> list[dict]:
        groups: dict[int, list[dict]] = {}
        for task in tasks:
            depth = len(task.get("deps", []))
            groups.setdefault(depth, []).append(task)
        result: list[dict] = []
        for depth in sorted(groups):
            result.extend(groups[depth])
        return result

    def deduplicate(self, tasks: list[dict]) -> list[dict]:
        seen: set[str] = set()
        unique: list[dict] = []
        for task in tasks:
            key = task.get("name", "") + str(task.get("action", {}))
            if key not in seen:
                seen.add(key)
                unique.append(task)
        return unique

    def estimate_duration(self, tasks: list[dict], mode: str = "safe") -> float:
        base_costs = {"scan": 2.0, "update": 1.0, "verify": 0.5, "graph": 1.5, "agent": 3.0, "repair": 2.0}
        total = sum(base_costs.get(task.get("action", {}).get("type", ""), 1.0) for task in tasks)
        if mode == "aggressive":
            total *= 0.6
        return round(total, 2)

    def generate_alternatives(self, action: dict) -> list[dict]:
        base = dict(action)
        return [
            {**base, "label": "fast", "mode": "aggressive"},
            {**base, "label": "safe", "mode": "safe"},
            {**base, "label": "balanced", "mode": "balanced"},
        ]

