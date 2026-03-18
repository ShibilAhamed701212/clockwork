import time
from typing import Dict, List, Optional

RISK_SIGNALS = {
    "circular_imports":      0.3,
    "missing_dependencies":  0.4,
    "high_coupling":         0.2,
    "architecture_violation":0.5,
    "stale_context":         0.2,
    "no_tests":              0.15,
}

class FailurePredictor:
    def predict(self, repo_map: Dict, context: Dict) -> Dict:
        risk_score = 0.0
        signals    = []

        rels = repo_map.get("relationships",{})
        if rels.get("circular_imports"):
            risk_score += RISK_SIGNALS["circular_imports"]
            signals.append("circular_imports: " + str(len(rels["circular_imports"])))

        if rels.get("anomalies"):
            risk_score += 0.1
            signals.append("anomalies: " + str(len(rels["anomalies"])))

        arch_conf = repo_map.get("architecture",{}).get("confidence","")
        if arch_conf == "low":
            risk_score += 0.2
            signals.append("low architecture confidence")

        ctx_arch = context.get("repository",{}).get("architecture","")
        map_arch = repo_map.get("architecture",{}).get("type","")
        if ctx_arch and map_arch and ctx_arch != map_arch:
            risk_score += RISK_SIGNALS["architecture_violation"]
            signals.append("architecture drift: " + ctx_arch + " vs " + map_arch)

        risk_level = "low"
        if risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"

        return {
            "risk_score":  round(min(1.0, risk_score), 3),
            "risk_level":  risk_level,
            "signals":     signals,
            "recommendation": self._recommend(risk_level),
        }

    def _recommend(self, risk_level: str) -> str:
        if risk_level == "high":
            return "Run clockwork repair + verify before execution."
        elif risk_level == "medium":
            return "Review anomalies and run clockwork verify."
        return "System looks healthy. Safe to proceed."

    def predict_task_risk(self, task: Dict, context: Dict) -> str:
        action = task.get("action",{})
        atype  = action.get("type","")
        target = action.get("target","")
        if atype == "delete":
            return "high"
        if ".clockwork" in target or "config" in target:
            return "high"
        if atype in ("modify","overwrite"):
            return "medium"
        return "low"