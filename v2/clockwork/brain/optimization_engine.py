from typing import Dict, List

class OptimizationEngine:
    def optimize_plan(self, tasks: List[Dict], mode: str = "safe") -> List[Dict]:
        if mode == "safe":
            return self._safe_order(tasks)
        elif mode == "aggressive":
            return self._parallel_groups(tasks)
        return tasks

    def _safe_order(self, tasks: List[Dict]) -> List[Dict]:
        return sorted(tasks, key=lambda t: t.get("priority_score", 0), reverse=True)

    def _parallel_groups(self, tasks: List[Dict]) -> List[Dict]:
        groups: Dict[int, List[Dict]] = {}
        for t in tasks:
            depth = len(t.get("deps", []))
            groups.setdefault(depth, []).append(t)
        result = []
        for depth in sorted(groups.keys()):
            result.extend(groups[depth])
        return result

    def deduplicate(self, tasks: List[Dict]) -> List[Dict]:
        seen = set()
        unique = []
        for t in tasks:
            key = t.get("name", "") + str(t.get("action", {}))
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique

    def estimate_duration(self, tasks: List[Dict], mode: str = "safe") -> float:
        base_costs = {"scan": 2.0, "update": 1.0, "verify": 0.5,
                      "graph": 1.5, "agent": 3.0, "repair": 2.0}
        total = sum(base_costs.get(t.get("action", {}).get("type", ""), 1.0) for t in tasks)
        if mode == "aggressive":
            total *= 0.6
        return round(total, 2)

    def generate_alternatives(self, action: Dict) -> List[Dict]:
        alternatives = []
        base = dict(action)
        alternatives.append({**base, "label": "fast",     "mode": "aggressive"})
        alternatives.append({**base, "label": "safe",     "mode": "safe"})
        alternatives.append({**base, "label": "balanced", "mode": "balanced"})
        return alternatives