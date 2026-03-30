from __future__ import annotations

import time
from dataclasses import dataclass, field

RISK_THRESHOLDS = {"low": 0.33, "medium": 0.66, "high": 1.0}


@dataclass
class Decision:
    status: str = "VALID"
    confidence: float = 1.0
    risk_level: str = "low"
    risk_score: float = 0.0
    explanation: str = ""
    suggestion: str = ""
    scores: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def approved(self) -> bool:
        return self.status == "VALID"

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "scores": self.scores,
            "timestamp": self.timestamp,
        }


class DecisionEngine:
    def evaluate(self, action: dict, context: dict, rule_result: object | None = None) -> Decision:
        scores = self._score(action, context)
        risk_score = self._calc_risk(action, context, scores)
        confidence = self._calc_confidence(scores, rule_result)
        risk_level = self._classify_risk(risk_score)
        status, explanation, suggestion = self._decide(scores, risk_score, risk_level, rule_result)
        return Decision(
            status=status,
            confidence=confidence,
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            explanation=explanation,
            suggestion=suggestion,
            scores=scores,
        )

    def _score(self, action: dict, context: dict) -> dict:
        action_type = action.get("type", "unknown")
        target = action.get("target", "")
        correctness = 1.0
        consistency = 1.0
        intent = 1.0

        if action_type == "delete":
            correctness -= 0.3
        if "core" in target or ".clockwork" in target:
            correctness -= 0.5
            consistency -= 0.4

        architecture = context.get("repository", {}).get("architecture", "")
        if architecture and architecture not in target and action_type == "create":
            consistency -= 0.1

        return {
            "correctness": max(0.0, round(correctness, 3)),
            "consistency": max(0.0, round(consistency, 3)),
            "intent": max(0.0, round(intent, 3)),
        }

    def _calc_risk(self, action: dict, context: dict, scores: dict) -> float:
        del context
        base = 0.0
        action_type = action.get("type", "")
        if action_type == "delete":
            base += 0.5
        elif action_type == "overwrite":
            base += 0.3
        elif action_type == "modify":
            base += 0.15
        elif action_type == "create":
            base += 0.05
        base += (1.0 - scores["correctness"]) * 0.3
        base += (1.0 - scores["consistency"]) * 0.2
        return min(1.0, round(base, 3))

    def _calc_confidence(self, scores: dict, rule_result: object | None) -> float:
        base = (scores["correctness"] + scores["consistency"] + scores["intent"]) / 3
        if rule_result and not getattr(rule_result, "approved", True):
            base *= 0.5
        return max(0.0, round(base, 3))

    def _classify_risk(self, score: float) -> str:
        if score <= RISK_THRESHOLDS["low"]:
            return "low"
        if score <= RISK_THRESHOLDS["medium"]:
            return "medium"
        return "high"

    def _decide(self, scores: dict, risk_score: float, risk_level: str, rule_result: object | None) -> tuple[str, str, str]:
        del scores
        if rule_result and not getattr(rule_result, "approved", True):
            reason = getattr(rule_result, "reason", "rule violation")
            return ("REJECTED", "Rule engine blocked action: " + str(reason), "Fix rule violation before proceeding.")
        if risk_level == "high":
            return ("REJECTED", f"High risk action detected (score={risk_score})", "Review change carefully or use safe mode.")
        if risk_level == "medium":
            return ("WARNING", f"Medium risk detected (score={risk_score})", "Proceed with caution and validate output.")
        return ("VALID", f"Action approved (risk={risk_score})", "")

    def compare(self, decisions: list[Decision]) -> Decision:
        if not decisions:
            return Decision(status="REJECTED", explanation="No decisions to compare")
        return max(decisions, key=lambda decision: decision.confidence - decision.risk_score)

