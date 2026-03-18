import time
from typing import Dict, List

PRIORITY_WEIGHTS = {
    "urgency":    0.35,
    "impact":     0.30,
    "risk":       0.25,
    "alignment":  0.10,
}

class PrioritizationEngine:
    def score_task(self, task: Dict) -> float:
        urgency   = task.get("urgency", 0.5)
        impact    = task.get("impact", 0.5)
        risk      = 1.0 - task.get("risk", 0.5)
        alignment = task.get("alignment", 0.5)
        score = (
            urgency   * PRIORITY_WEIGHTS["urgency"]  +
            impact    * PRIORITY_WEIGHTS["impact"]   +
            risk      * PRIORITY_WEIGHTS["risk"]     +
            alignment * PRIORITY_WEIGHTS["alignment"]
        )
        return round(score, 4)

    def rank(self, tasks: List[Dict]) -> List[Dict]:
        for t in tasks:
            t["priority_score"] = self.score_task(t)
        return sorted(tasks, key=lambda t: t["priority_score"], reverse=True)

    def top(self, tasks: List[Dict], n: int = 1) -> List[Dict]:
        return self.rank(tasks)[:n]

    def classify(self, score: float) -> str:
        if score >= 0.75:
            return "critical"
        elif score >= 0.50:
            return "high"
        elif score >= 0.25:
            return "medium"
        return "low"