"""
clockwork/security/__init__.py
--------------------------------
Security and Sandboxing subsystem (spec §13).

Protects the repository, developer machine, and Clockwork runtime
from malicious plugins, unsafe agent output, sensitive data exposure,
and repository corruption.

Public API::

    from clockwork.security import SecurityEngine, SecurityViolation

    sec = SecurityEngine(repo_root=Path("."))

    # validate a path
    sec.guard.check_path("/etc/passwd")       # raises SecurityViolation

    # scan for issues
    result = sec.scan()

    # full audit
    report = sec.audit()

    # check proposed changes from an agent
    safe, violations = sec.check_proposed_changes(
        ["modify backend/auth.py", "delete .env"],
        agent="claude_code",
    )

CLI commands added:
    clockwork security scan
    clockwork security audit
    clockwork security log
    clockwork security verify <plugin_path>
"""

from clockwork.security.security_engine import SecurityEngine, PluginVerifier
from clockwork.security.file_guard import FileGuard, SecurityViolation
from clockwork.security.logger import SecurityLogger
from clockwork.security.access_control import AccessControl
from clockwork.security.command_filter import CommandFilter, SecurityAlert
from clockwork.security.secrets_protection import SecretsProtection
from clockwork.security.plugin_security import PluginSecurity
from clockwork.security.sandbox import Sandbox, SandboxResult, SandboxViolation
from clockwork.security.models import (
    Permission, RiskLevel, SecurityEvent,
    SecurityLogEntry, SecurityScanResult, PluginManifest,
)

__all__ = [
    "SecurityEngine",
    "PluginVerifier",
    "FileGuard",
    "SecurityViolation",
    "SecurityLogger",
    "AccessControl",
    "CommandFilter",
    "SecurityAlert",
    "SecretsProtection",
    "PluginSecurity",
    "Sandbox",
    "SandboxResult",
    "SandboxViolation",
    "Permission",
    "RiskLevel",
    "SecurityEvent",
    "SecurityLogEntry",
    "SecurityScanResult",
    "PluginManifest",
]

