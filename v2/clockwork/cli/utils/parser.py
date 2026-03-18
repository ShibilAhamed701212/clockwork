import re
from typing import Dict, List, Optional, Tuple

INTENT_MAP = {
    "scan":    ["scan","analyze","inspect","index"],
    "update":  ["update","sync","refresh","merge"],
    "verify":  ["verify","check","validate","audit"],
    "repair":  ["repair","fix","heal","restore"],
    "graph":   ["graph","map","visualize","deps"],
    "agent":   ["agent","run","execute","task","do","automate"],
    "pack":    ["pack","package","export","snapshot"],
    "load":    ["load","import","restore","unpack"],
    "watch":   ["watch","monitor","observe","live"],
    "handoff": ["handoff","transfer","brief","next"],
    "init":    ["init","initialize","setup","bootstrap"],
    "status":  ["status","state","info","show"],
}

RISK_KEYWORDS = {
    "high":   ["delete","remove","drop","destroy","wipe"],
    "medium": ["modify","change","alter","edit"],
    "low":    ["scan","read","view","check","list"],
}

class IntentParser:
    def sanitize(self, text: str) -> str:
        return text.strip().strip('"').strip("'")

    def parse_intent(self, user_input: str) -> Optional[str]:
        lower = user_input.lower()
        for intent, keywords in INTENT_MAP.items():
            if any(kw in lower for kw in keywords):
                return intent
        return None

    def extract_goal(self, user_input: str) -> Optional[str]:
        patterns = [
            r"(?:fix|optimize|improve|analyze|check|scan|run)\s+(.+)",
            r"(?:goal|task|do)\s*[:=]?\s*(.+)",
        ]
        for p in patterns:
            m = re.search(p, user_input, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return user_input

    def extract_target(self, user_input: str) -> Optional[str]:
        m = re.search(r"(?:in|for|at|focus|target)\s+([^\s,]+)", user_input, re.IGNORECASE)
        return m.group(1) if m else None

    def parse_natural_language(self, user_input: str) -> Dict:
        return {
            "intent": self.parse_intent(user_input),
            "target": self.extract_target(user_input),
            "risk":   self.assess_risk(user_input),
            "raw":    user_input,
        }

    def assess_risk(self, user_input: str) -> str:
        lower = user_input.lower()
        for level in ["high","medium","low"]:
            if any(kw in lower for kw in RISK_KEYWORDS[level]):
                return level
        return "low"

    def suggest_command(self, partial: str) -> List[str]:
        return ["clockwork " + cmd for cmd in INTENT_MAP if partial.lower() in cmd][:5]

    def validate_command(self, command: str, valid: List[str]) -> Tuple[bool, str]:
        if command in valid:
            return True, ""
        suggestions = self.suggest_command(command)
        msg = "Unknown command: " + command
        if suggestions:
            msg += " | Did you mean: " + ", ".join(suggestions)
        return False, msg