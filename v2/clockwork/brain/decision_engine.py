import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field

RISK_THRESHOLDS = {"low": 0.33, "medium": 0.66, "high": 1.0}

@dataclass
class Decision:
    status:      str     = "VALID"
    confidence:  float   = 1.0
    risk_level:  str     = "low"
    risk_score:  float   = 0.0
    explanation: str     = ""
    suggestion:  str     = ""
    scores:      Dict    = field(default_factory=dict)
    timestamp:   float   = field(default_factory=time.time)

    def approved(self) -> bool:
        return self.status == "VALID"

    def to_dict(self) -> Dict:
        return {
            "status":      self.status,
            "confidence":  self.confidence,
            "risk_level":  self.risk_level,
            "risk_score":  self.risk_score,
            "explanation": self.explanation,
            "suggestion":  self.suggestion,
            "scores":      self.scores,
            "timestamp":   self.timestamp,
        }


class DecisionEngine:
    def evaluate(self, action: Dict, context: Dict, rule_result=None) -> Decision:
        scores = self._score(action, context)
        risk_score = self._calc_risk(action, context, scores)
        confidence = self._calc_confidence(scores, rule_result)
        risk_level = self._classify_risk(risk_score)
        status, explanation, suggestion = self._decide(
            scores, risk_score, risk_level, rule_result
        )
        return Decision(
            status=status,
            confidence=confidence,
            risk_level=risk_level,
            risk_score=round(risk_score, 3),
            explanation=explanation,
            suggestion=suggestion,
            scores=scores,
        )

    def _score(self, action: Dict, context: Dict) -> Dict:
        action_type = action.get("type", "unknown")
        target      = action.get("target", "")
        correctness = 1.0
        consistency = 1.0
        intent      = 1.0

        if action_type == "delete":
            correctness -= 0.3
        if "core" in target or ".clockwork" in target:
            correctness -= 0.5
            consistency -= 0.4

        arch = context.get("repository", {}).get("architecture", "")
        if arch and arch not in target and action_type == "create":
            consistency -= 0.1

        return {
            "correctness": max(0.0, round(correctness, 3)),
            "consistency": max(0.0, round(consistency, 3)),
            "intent":      max(0.0, round(intent, 3)),
        }

    def _calc_risk(self, action: Dict, context: Dict, scores: Dict) -> float:
        base = 0.0
        atype = action.get("type", "")
        if atype == "delete":
            base += 0.5
        elif atype == "overwrite":
            base += 0.3
        elif atype == "modify":
            base += 0.15
        elif atype == "create":
            base += 0.05
        base += (1.0 - scores["correctness"]) * 0.3
        base += (1.0 - scores["consistency"]) * 0.2
        return min(1.0, round(base, 3))

    def _calc_confidence(self, scores: Dict, rule_result) -> float:
        base = (scores["correctness"] + scores["consistency"] + scores["intent"]) / 3
        if rule_result and not rule_result.approved:
            base *= 0.5
        return max(0.0, round(base, 3))

    def _classify_risk(self, score: float) -> str:
        if score <= RISK_THRESHOLDS["low"]:
            return "low"
        elif score <= RISK_THRESHOLDS["medium"]:
            return "medium"
        return "high"

    def _decide(self, scores, risk_score, risk_level, rule_result):
        if rule_result and not rule_result.approved:
            return (
                "REJECTED",
                "Rule engine blocked action: " + rule_result.reason,
                "Fix rule violation before proceeding.",
            )
        if risk_level == "high":
            return (
                "REJECTED",
                "High risk action detected (score=" + str(risk_score) + ")",
                "Review change carefully or use safe mode.",
            )
        if risk_level == "medium":
            return (
                "WARNING",
                "Medium risk detected (score=" + str(risk_score) + ")",
                "Proceed with caution and validate output.",
            )
        return ("VALID", "Action approved (risk=" + str(risk_score) + ")", "")

    def compare(self, decisions: List[Decision]) -> Decision:
        if not decisions:
            return Decision(status="REJECTED", explanation="No decisions to compare")
        return max(decisions, key=lambda d: d.confidence - d.risk_score)