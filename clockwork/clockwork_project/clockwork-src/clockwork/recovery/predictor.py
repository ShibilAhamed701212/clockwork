from __future__ import annotations

RISK_SIGNALS = {
    "circular_imports": 0.3,
    "missing_dependencies": 0.4,
    "high_coupling": 0.2,
    "architecture_violation": 0.5,
    "stale_context": 0.2,
    "no_tests": 0.15,
}


class FailurePredictor:
    def predict(self, repo_map: dict, context: dict) -> dict:
        risk_score = 0.0
        signals: list[str] = []

        relationships = repo_map.get("relationships", {})
        if relationships.get("circular_imports"):
            risk_score += RISK_SIGNALS["circular_imports"]
            signals.append(f"circular_imports: {len(relationships['circular_imports'])}")

        if relationships.get("anomalies"):
            risk_score += 0.1
            signals.append(f"anomalies: {len(relationships['anomalies'])}")

        architecture = repo_map.get("architecture", {})
        if architecture.get("confidence") == "low":
            risk_score += 0.2
            signals.append("low architecture confidence")

        context_arch = context.get("repository", {}).get("architecture", "")
        map_arch = architecture.get("type", "")
        if context_arch and map_arch and context_arch != map_arch:
            risk_score += RISK_SIGNALS["architecture_violation"]
            signals.append(f"architecture drift: {context_arch} vs {map_arch}")

        risk_level = "low"
        if risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"

        return {
            "risk_score": round(min(1.0, risk_score), 3),
            "risk_level": risk_level,
            "signals": signals,
            "recommendation": self._recommend(risk_level),
        }

    def _recommend(self, risk_level: str) -> str:
        if risk_level == "high":
            return "Run clockwork repair + verify before execution."
        if risk_level == "medium":
            return "Review anomalies and run clockwork verify."
        return "System looks healthy. Safe to proceed."

    def predict_task_risk(self, task: dict, context: dict) -> str:
        action = task.get("action", {})
        action_type = action.get("type", "")
        target = action.get("target", "")
        if action_type == "delete":
            return "high"
        if ".clockwork" in target or "config" in target:
            return "high"
        if action_type in ("modify", "overwrite"):
            return "medium"
        return "low"

