"""
clockwork/security/logger.py
-----------------------------
Security event logger (spec §11).

All security events are written to .clockwork/security_log.json
so developers can audit what Clockwork blocked or flagged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import RiskLevel, SecurityEvent, SecurityLogEntry


class SecurityLogger:
    """
    Appends security events to .clockwork/security_log.json.

    Usage::

        logger = SecurityLogger(clockwork_dir)
        logger.log_blocked_file("/etc/passwd", agent="claude")
        logger.log_sensitive_access(".env")
    """

    def __init__(self, clockwork_dir: Path) -> None:
        self.log_path = clockwork_dir / "security_log.json"

    # ── write ──────────────────────────────────────────────────────────────

    def log(self, entry: SecurityLogEntry) -> None:
        """Append one entry to security_log.json."""
        entries = self._read()
        entries.append(entry.to_dict())
        self.log_path.write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )

    def log_blocked_file(
        self, file_path: str, agent: str = "", detail: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.BLOCKED_FILE_ACCESS,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=detail or f"Access to restricted path blocked: {file_path}",
        ))

    def log_sensitive_access(
        self, file_path: str, agent: str = "", blocked: bool = True
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.SENSITIVE_FILE_ACCESS,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=f"Attempt to access sensitive file: {file_path}",
            blocked=blocked,
        ))

    def log_dangerous_command(
        self, command: str, agent: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.DANGEROUS_COMMAND,
            risk_level=RiskLevel.CRITICAL,
            detail=f"Dangerous command blocked: {command}",
            agent=agent,
        ))

    def log_protected_file_attempt(
        self, file_path: str, agent: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PROTECTED_FILE_ATTEMPT,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=f"Attempt to modify protected file: {file_path}",
        ))

    def log_permission_denied(
        self, permission: str, agent: str = "", detail: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PERMISSION_DENIED,
            risk_level=RiskLevel.MEDIUM,
            agent=agent,
            detail=detail or f"Permission denied: {permission}",
        ))

    def log_path_traversal(self, path: str, agent: str = "") -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PATH_TRAVERSAL,
            risk_level=RiskLevel.CRITICAL,
            file=path,
            agent=agent,
            detail=f"Path traversal attempt detected: {path}",
        ))

    # ── read ───────────────────────────────────────────────────────────────

    def read_log(self) -> list[dict[str, Any]]:
        return self._read()

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return self._read()[-n:]

    def _read(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            return []

