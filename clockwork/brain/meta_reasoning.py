from __future__ import annotations

import time


class MetaReasoning:
    def __init__(self) -> None:
        self.history: list[dict] = []

    def evaluate_decision(self, decision: object, action: dict, outcome: str | None = None) -> dict:
        quality = self._score_quality(decision)
        improvement = self._suggest_improvement(decision, action)
        entry = {
            "timestamp": time.time(),
            "action": action,
            "decision": decision.to_dict() if hasattr(decision, "to_dict") else str(decision),
            "quality": quality,
            "improvement": improvement,
            "outcome": outcome,
        }
        self.history.append(entry)
        return entry

    def _score_quality(self, decision: object) -> str:
        confidence = getattr(decision, "confidence", 0)
        risk = getattr(decision, "risk_score", 1)
        score = confidence - risk
        if score >= 0.6:
            return "excellent"
        if score >= 0.3:
            return "good"
        if score >= 0.0:
            return "acceptable"
        return "poor"

    def _suggest_improvement(self, decision: object, action: dict) -> str:
        del action
        risk = getattr(decision, "risk_score", 0)
        confidence = getattr(decision, "confidence", 1)
        if risk > 0.7:
            return "Switch to safe mode - risk is very high."
        if confidence < 0.4:
            return "Run additional validation before proceeding."
        if getattr(decision, "status", "") == "WARNING":
            return "Consider running in dry-run mode first."
        return "Decision quality is acceptable."

    def detect_pattern(self) -> str | None:
        if len(self.history) < 3:
            return None
        recent = self.history[-5:]
        rejected = sum(1 for entry in recent if entry.get("decision", {}).get("status") == "REJECTED")
        if rejected >= 3:
            return "HIGH_REJECTION_RATE - review rules or input quality."
        poor = sum(1 for entry in recent if entry.get("quality") == "poor")
        if poor >= 3:
            return "POOR_DECISION_QUALITY - consider switching brain mode."
        return None

    def summary(self) -> dict:
        total = len(self.history)
        if total == 0:
            return {"total": 0, "pattern": None}
        approved = sum(1 for entry in self.history if entry.get("decision", {}).get("status") == "VALID")
        rejected = sum(1 for entry in self.history if entry.get("decision", {}).get("status") == "REJECTED")
        avg_conf = sum(entry.get("decision", {}).get("confidence", 0) for entry in self.history) / total
        return {
            "total": total,
            "approved": approved,
            "rejected": rejected,
            "avg_confidence": round(avg_conf, 3),
            "pattern": self.detect_pattern(),
        }

