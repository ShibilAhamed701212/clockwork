"""
clockwork/security/models.py
-----------------------------
Data models for the Security and Sandboxing subsystem (spec §13).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ── Permission constants (spec §13) ───────────────────────────────────────

class Permission:
    FILESYSTEM_READ   = "filesystem_read"
    REPOSITORY_WRITE  = "repository_write"
    NETWORK_ACCESS    = "network_access"
    PLUGIN_EXECUTE    = "plugin_execute"
    SYSTEM_COMMAND    = "system_command"

    # safe default set — no write, no network, no system commands
    SAFE_DEFAULT = {FILESYSTEM_READ}
    ALL = {FILESYSTEM_READ, REPOSITORY_WRITE, NETWORK_ACCESS, PLUGIN_EXECUTE, SYSTEM_COMMAND}


# ── Security event types ───────────────────────────────────────────────────

class SecurityEvent:
    BLOCKED_FILE_ACCESS    = "blocked_file_access"
    SENSITIVE_FILE_ACCESS  = "sensitive_file_access"
    DANGEROUS_COMMAND      = "dangerous_command_blocked"
    PERMISSION_DENIED      = "permission_denied"
    PROTECTED_FILE_ATTEMPT = "protected_file_modification_attempt"
    PLUGIN_BLOCKED         = "plugin_blocked"
    PATH_TRAVERSAL         = "path_traversal_attempt"
    SCAN_COMPLETED         = "security_scan_completed"
    AUDIT_COMPLETED        = "security_audit_completed"


# ── Risk levels ────────────────────────────────────────────────────────────

class RiskLevel:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ── Security log entry (spec §11) ──────────────────────────────────────────

@dataclass
class SecurityLogEntry:
    """One record written to .clockwork/security_log.json."""

    timestamp:   str
    event:       str           # SecurityEvent constant
    risk_level:  str           # RiskLevel constant
    file:        str = ""
    agent:       str = ""
    detail:      str = ""
    blocked:     bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp":  self.timestamp,
            "event":      self.event,
            "risk_level": self.risk_level,
            "file":       self.file,
            "agent":      self.agent,
            "detail":     self.detail,
            "blocked":    self.blocked,
        }

    @classmethod
    def now(
        cls,
        event: str,
        risk_level: str = RiskLevel.MEDIUM,
        **kwargs: Any,
    ) -> "SecurityLogEntry":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            risk_level=risk_level,
            **kwargs,
        )


# ── Security scan result ───────────────────────────────────────────────────

@dataclass
class SecurityScanResult:
    """Result of `clockwork security scan`."""

    passed:        bool
    risk_level:    str                    = RiskLevel.LOW
    issues:        list[str]              = field(default_factory=list)
    warnings:      list[str]              = field(default_factory=list)
    sensitive_files_found: list[str]      = field(default_factory=list)
    protected_files_ok:    bool           = True
    elapsed_ms:    float                  = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":               self.passed,
            "risk_level":           self.risk_level,
            "issues":               self.issues,
            "warnings":             self.warnings,
            "sensitive_files_found": self.sensitive_files_found,
            "protected_files_ok":   self.protected_files_ok,
            "elapsed_ms":           round(self.elapsed_ms, 1),
        }


# ── Plugin manifest (spec §12) ─────────────────────────────────────────────

@dataclass
class PluginManifest:
    """Declared metadata every plugin must supply."""

    name:               str
    version:            str
    author:             str         = ""
    description:        str         = ""
    requires_clockwork: str         = ">=0.1"
    permissions:        list[str]   = field(default_factory=list)
    checksum:           str         = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":               self.name,
            "version":            self.version,
            "author":             self.author,
            "description":        self.description,
            "requires_clockwork": self.requires_clockwork,
            "permissions":        self.permissions,
            "checksum":           self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PluginManifest":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            author=d.get("author", ""),
            description=d.get("description", ""),
            requires_clockwork=d.get("requires_clockwork", ">=0.1"),
            permissions=d.get("permissions", []),
            checksum=d.get("checksum", ""),
        )

