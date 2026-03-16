"""
clockwork/security/file_guard.py
----------------------------------
File access guard (spec §5, §6, §8).

Enforces:
  - allowed path restrictions (repo root + .clockwork only)
  - sensitive file protection (.env, credentials, keys)
  - protected core file detection
  - dangerous command blocking
  - path traversal prevention
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from .logger import SecurityLogger
from .models import RiskLevel, SecurityEvent


# ── Sensitive file patterns (spec §6) ─────────────────────────────────────

SENSITIVE_FILENAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.staging", ".env.test",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.json", "secrets.yaml", "secrets.yml",
    "secret.json", "secret.yaml",
    ".netrc", ".htpasswd",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "id_rsa.pub", "id_ed25519.pub",
    "private_key.pem", "private.pem", "privkey.pem",
    "server.key", "client.key",
    "aws_credentials", "gcloud_credentials.json",
    "service_account.json",
})

SENSITIVE_EXTENSIONS: frozenset[str] = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".pkcs12",
    ".cer", ".crt",
})

SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\.env(\.|$)"),          # .env, .env.local, etc.
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_\-]?key", re.IGNORECASE),
]

# ── Protected Clockwork core files ─────────────────────────────────────────

PROTECTED_CLOCKWORK_FILES: frozenset[str] = frozenset({
    ".clockwork/context.yaml",
    ".clockwork/repo_map.json",
    ".clockwork/rules.yaml",
    ".clockwork/rules.md",
    ".clockwork/handoff/handoff.json",
})

# ── Dangerous command fragments (spec §8) ─────────────────────────────────

DANGEROUS_COMMANDS: list[re.Pattern] = [
    re.compile(r"rm\s+-rf\s*/"),
    re.compile(r"rm\s+-rf\s+[~\\]"),
    re.compile(r"chmod\s+[0-7]{3,4}\s+/"),
    re.compile(r"chown\s+.*\s+/"),
    re.compile(r"mkfs"),
    re.compile(r"dd\s+if="),
    re.compile(r":\(\)\s*\{.*\}"),          # fork bomb
    re.compile(r"nmap\b"),
    re.compile(r"netcat\b|nc\s+-[lLe]"),
    re.compile(r"curl.*\|\s*(?:ba)?sh"),    # curl | bash
    re.compile(r"wget.*\|\s*(?:ba)?sh"),
    re.compile(r"eval\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"/etc/passwd"),
    re.compile(r"/etc/shadow"),
]

# ── System restricted paths ────────────────────────────────────────────────

SYSTEM_RESTRICTED_PREFIXES: tuple[str, ...] = (
    "/etc/", "/sys/", "/proc/", "/boot/", "/dev/",
    "/usr/bin/", "/usr/lib/", "/usr/sbin/",
    "/bin/", "/sbin/", "/lib/",
    "C:\\Windows\\", "C:\\Program Files\\",
    "C:\\ProgramData\\",
)


class FileGuard:
    """
    Validates file paths and commands against security policies.

    Usage::

        guard = FileGuard(repo_root, clockwork_dir)
        guard.check_path("/etc/passwd")        # raises SecurityViolation
        guard.check_sensitive("credentials.json")  # raises SecurityViolation
        guard.check_command("rm -rf /")        # raises SecurityViolation
    """

    def __init__(
        self,
        repo_root: Path,
        clockwork_dir: Path,
        logger: Optional[SecurityLogger] = None,
        agent: str = "",
    ) -> None:
        self.repo_root    = repo_root.resolve()
        self.clockwork_dir = clockwork_dir.resolve()
        self.logger       = logger
        self.agent        = agent

    # ── path validation (spec §5) ──────────────────────────────────────────

    def is_allowed_path(self, path: str) -> bool:
        """Return True if path is within the allowed scope."""
        try:
            resolved = Path(path).resolve()
        except Exception:
            return False

        # must be under repo root or .clockwork
        if str(resolved).startswith(str(self.repo_root)):
            return True
        if str(resolved).startswith(str(self.clockwork_dir)):
            return True
        return False

    def check_path(self, path: str) -> None:
        """
        Raise SecurityViolation if path is outside allowed scope
        or is a system restricted path.
        """
        # path traversal check
        if ".." in path and not self.is_allowed_path(path):
            if self.logger:
                self.logger.log_path_traversal(path, self.agent)
            raise SecurityViolation(
                f"Path traversal attempt blocked: {path}"
            )

        # system restricted prefixes
        norm = path.replace("\\", "/")
        for prefix in SYSTEM_RESTRICTED_PREFIXES:
            if norm.startswith(prefix.replace("\\", "/")):
                if self.logger:
                    self.logger.log_blocked_file(path, self.agent)
                raise SecurityViolation(
                    f"Access to system path blocked: {path}"
                )

        if not self.is_allowed_path(path):
            if self.logger:
                self.logger.log_blocked_file(path, self.agent)
            raise SecurityViolation(
                f"Path outside allowed scope: {path}"
            )

    # ── sensitive file detection (spec §6) ────────────────────────────────

    def is_sensitive(self, file_path: str) -> bool:
        """Return True if the file is sensitive and should be protected."""
        name = Path(file_path).name.lower()
        ext  = Path(file_path).suffix.lower()

        if name in SENSITIVE_FILENAMES:
            return True
        if ext in SENSITIVE_EXTENSIONS:
            return True
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(name):
                return True
        return False

    def check_sensitive(self, file_path: str) -> None:
        """Raise SecurityViolation if file_path is sensitive."""
        if self.is_sensitive(file_path):
            if self.logger:
                self.logger.log_sensitive_access(file_path, self.agent)
            raise SecurityViolation(
                f"Access to sensitive file blocked: {file_path}"
            )

    # ── protected file detection ───────────────────────────────────────────

    def is_protected(self, file_path: str) -> bool:
        """Return True if file_path is a protected Clockwork core file."""
        norm = file_path.replace("\\", "/")
        return any(norm.endswith(pf) for pf in PROTECTED_CLOCKWORK_FILES)

    def check_protected(self, file_path: str) -> None:
        """Raise SecurityViolation if attempting to modify a protected file."""
        if self.is_protected(file_path):
            if self.logger:
                self.logger.log_protected_file_attempt(file_path, self.agent)
            raise SecurityViolation(
                f"Modification of protected file blocked: {file_path}"
            )

    # ── command validation (spec §8) ──────────────────────────────────────

    def is_dangerous_command(self, command: str) -> bool:
        """Return True if command matches a dangerous pattern."""
        for pattern in DANGEROUS_COMMANDS:
            if pattern.search(command):
                return True
        return False

    def check_command(self, command: str) -> None:
        """Raise SecurityViolation if command is dangerous."""
        if self.is_dangerous_command(command):
            if self.logger:
                self.logger.log_dangerous_command(command, self.agent)
            raise SecurityViolation(
                f"Dangerous command blocked: {command[:80]}"
            )

    # ── permission check (spec §13) ───────────────────────────────────────

    def check_permission(
        self,
        requested: str,
        granted: set[str],
    ) -> None:
        """Raise SecurityViolation if requested permission not in granted set."""
        if requested not in granted:
            if self.logger:
                self.logger.log_permission_denied(requested, self.agent)
            raise SecurityViolation(
                f"Permission '{requested}' not granted to agent '{self.agent}'"
            )


class SecurityViolation(Exception):
    """Raised when a security policy is violated."""

