import json
import time
from pathlib import Path
from typing import Dict, List, Set, Tuple

SECURITY_LOG = Path("security/logs/security_log.json")

PERMISSION_MATRIX: Dict[str, Set[str]] = {
    "read":    {"scanner_agent","general_agent","reasoning_agent","coding_agent",
                "test_agent","validation_agent","debug_agent","frontend_agent","db_agent"},
    "write":   {"coding_agent","general_agent","debug_agent"},
    "execute": {"general_agent"},
    "delete":  set(),
    "admin":   set(),
}

PROTECTED_PATHS = {
    ".clockwork/context.yaml",
    ".clockwork/rules.yaml",
    "config/config.yaml",
    "rules/rules.md",
    ".env",
    ".env.local",
}

PROTECTED_EXTENSIONS = {".pem",".key",".cert",".p12",".pfx"}

class AccessControl:
    def __init__(self):
        SECURITY_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not SECURITY_LOG.exists():
            SECURITY_LOG.write_text("[]")

    def can(self, agent: str, action: str, target: str = "") -> bool:
        allowed = PERMISSION_MATRIX.get(action, set())
        if agent not in allowed:
            self._log(agent, action, target, "DENIED", "No permission for: " + action)
            return False
        if target:
            ok, reason = self._check_target(action, target)
            if not ok:
                self._log(agent, action, target, "DENIED", reason)
                return False
        self._log(agent, action, target, "ALLOWED", "")
        return True

    def _check_target(self, action: str, target: str) -> Tuple[bool, str]:
        if action not in ("write","delete","execute","overwrite"):
            return True, ""
        norm = target.replace("\\","/")
        for pp in PROTECTED_PATHS:
            if norm.endswith(pp) or pp in norm:
                return False, "Protected path: " + pp
        ext = Path(target).suffix.lower()
        if ext in PROTECTED_EXTENSIONS:
            return False, "Protected file type: " + ext
        return True, ""

    def audit(self, agent: str, action: str, target: str, outcome: str):
        self._log(agent, action, target, outcome, "audit")

    def _log(self, agent: str, action: str, target: str, result: str, reason: str):
        entry = {"timestamp": time.time(), "agent": agent, "action": action,
                 "target": target, "result": result, "reason": reason}
        try:
            log = json.loads(SECURITY_LOG.read_text())
            log.append(entry)
            SECURITY_LOG.write_text(json.dumps(log[-1000:], indent=2))
        except Exception:
            pass

    def get_permissions(self, agent: str) -> List[str]:
        return [a for a, agents in PERMISSION_MATRIX.items() if agent in agents]

    def get_log(self, last_n: int = 50) -> List[Dict]:
        try:
            return json.loads(SECURITY_LOG.read_text())[-last_n:]
        except Exception:
            return []

    def denied_count(self) -> int:
        try:
            log = json.loads(SECURITY_LOG.read_text())
            return sum(1 for e in log if e.get("result") == "DENIED")
        except Exception:
            return 0