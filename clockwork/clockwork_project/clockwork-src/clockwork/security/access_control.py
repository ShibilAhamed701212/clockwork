from __future__ import annotations

import json
import time
from pathlib import Path

SECURITY_LOG = Path(".clockwork/security_access_log.json")

PERMISSION_MATRIX: dict[str, set[str]] = {
    "read": {"scanner_agent", "general_agent", "reasoning_agent", "coding_agent", "test_agent", "validation_agent", "debug_agent", "frontend_agent", "db_agent"},
    "write": {"coding_agent", "general_agent", "debug_agent"},
    "execute": {"general_agent"},
    "delete": set(),
    "admin": set(),
}

PROTECTED_PATHS = {
    ".clockwork/context.yaml",
    ".clockwork/rules.yaml",
    "config/config.yaml",
    "rules/rules.md",
    ".env",
    ".env.local",
}

PROTECTED_EXTENSIONS = {".pem", ".key", ".cert", ".p12", ".pfx"}


class AccessControl:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.security_log = self.repo_root / SECURITY_LOG
        self.security_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.security_log.exists():
            self.security_log.write_text("[]", encoding="utf-8")

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

    def _check_target(self, action: str, target: str) -> tuple[bool, str]:
        if action not in ("write", "delete", "execute", "overwrite"):
            return True, ""
        normalized = target.replace("\\", "/")
        for protected in PROTECTED_PATHS:
            if normalized.endswith(protected) or protected in normalized:
                return False, "Protected path: " + protected
        extension = Path(target).suffix.lower()
        if extension in PROTECTED_EXTENSIONS:
            return False, "Protected file type: " + extension
        return True, ""

    def audit(self, agent: str, action: str, target: str, outcome: str) -> None:
        self._log(agent, action, target, outcome, "audit")

    def _log(self, agent: str, action: str, target: str, result: str, reason: str) -> None:
        entry = {"timestamp": time.time(), "agent": agent, "action": action, "target": target, "result": result, "reason": reason}
        try:
            log = json.loads(self.security_log.read_text(encoding="utf-8"))
            log.append(entry)
            self.security_log.write_text(json.dumps(log[-1000:], indent=2), encoding="utf-8")
        except Exception:
            return

    def get_permissions(self, agent: str) -> list[str]:
        return [action for action, agents in PERMISSION_MATRIX.items() if agent in agents]

    def get_log(self, last_n: int = 50) -> list[dict]:
        try:
            return json.loads(self.security_log.read_text(encoding="utf-8"))[-last_n:]
        except Exception:
            return []

    def denied_count(self) -> int:
        try:
            log = json.loads(self.security_log.read_text(encoding="utf-8"))
            return sum(1 for entry in log if entry.get("result") == "DENIED")
        except Exception:
            return 0

