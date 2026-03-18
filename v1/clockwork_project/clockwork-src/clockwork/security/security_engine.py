"""
clockwork/security/security_engine.py
---------------------------------------
Main entry point for the Security and Sandboxing subsystem (spec §13).

Provides:
  - FileGuard   — path + sensitive file + command validation
  - SecurityScanner — repo scan + audit
  - SecurityLogger  — event logging to security_log.json
  - PluginVerifier  — checksum + manifest validation (spec §12)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .file_guard import FileGuard, SecurityViolation
from .logger import SecurityLogger
from .models import Permission, PluginManifest, RiskLevel, SecurityScanResult
from .scanner import SecurityScanner


class PluginVerifier:
    """
    Verifies a plugin before installation (spec §12).

    Checks:
      - manifest exists and is valid
      - checksum matches declared value
      - permissions are within acceptable bounds
      - dangerous permissions flagged for confirmation
    """

    DANGEROUS_PERMISSIONS = {Permission.SYSTEM_COMMAND, Permission.NETWORK_ACCESS}
    MAX_ALLOWED_PERMISSIONS = {
        Permission.FILESYSTEM_READ,
        Permission.REPOSITORY_WRITE,
    }

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir
        self.logger        = SecurityLogger(clockwork_dir)

    def verify(self, plugin_dir: Path) -> tuple[bool, list[str]]:
        """
        Verify a plugin directory before installation.

        Returns (ok, [issues]).
        """
        issues: list[str] = []

        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            issues.append("plugin.yaml manifest not found")
            return False, issues

        try:
            import yaml  # type: ignore
            data     = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            manifest = PluginManifest.from_dict(data)
        except Exception as exc:
            issues.append(f"Invalid manifest: {exc}")
            return False, issues

        # name and version required
        if not manifest.name:
            issues.append("Plugin manifest missing 'name'")
        if not manifest.version:
            issues.append("Plugin manifest missing 'version'")

        # permission check
        for perm in manifest.permissions:
            if perm in self.DANGEROUS_PERMISSIONS:
                issues.append(
                    f"Plugin requests dangerous permission: '{perm}' — manual review required"
                )

        # checksum verification if provided
        if manifest.checksum:
            computed = self._checksum_dir(plugin_dir)
            if computed != manifest.checksum:
                issues.append(
                    f"Checksum mismatch — expected {manifest.checksum[:12]}..., "
                    f"got {computed[:12]}..."
                )

        return len(issues) == 0, issues

    def _checksum_dir(self, plugin_dir: Path) -> str:
        """Compute a deterministic SHA-256 over all plugin files."""
        h = hashlib.sha256()
        for fp in sorted(plugin_dir.rglob("*")):
            if fp.is_file() and fp.name != "plugin.yaml":
                try:
                    h.update(fp.read_bytes())
                except OSError:
                    pass
        return h.hexdigest()


class SecurityEngine:
    """
    Top-level facade for the Security subsystem.

    Usage::

        sec = SecurityEngine(repo_root=Path("."))

        # validate a path before accessing it
        sec.guard.check_path("/etc/passwd")   # raises SecurityViolation

        # scan the repo for issues
        result = sec.scan()

        # full audit
        report = sec.audit()

        # verify a plugin
        ok, issues = sec.verify_plugin(Path(".clockwork/plugins/my_plugin"))
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.logger        = SecurityLogger(self.clockwork_dir)
        self.guard         = FileGuard(
            self.repo_root, self.clockwork_dir, self.logger
        )
        self.scanner       = SecurityScanner(self.repo_root)
        self.verifier      = PluginVerifier(self.clockwork_dir)

    def scan(self) -> SecurityScanResult:
        """Run a security scan of the repository."""
        return self.scanner.scan()

    def audit(self) -> dict[str, Any]:
        """Produce a full security audit report."""
        return self.scanner.audit()

    def verify_plugin(self, plugin_dir: Path) -> tuple[bool, list[str]]:
        """Verify a plugin before installation."""
        return self.verifier.verify(plugin_dir)

    def check_proposed_changes(
        self,
        proposed_changes: list[str],
        agent: str = "",
    ) -> tuple[bool, list[str]]:
        """
        Security-filter a list of proposed changes (spec §7, §10).

        Returns (safe, [violations]).
        """
        guard    = FileGuard(self.repo_root, self.clockwork_dir, self.logger, agent)
        safe     = True
        violations: list[str] = []

        for change in proposed_changes:
            # extract file path: strip the first verb token only
            _parts = change.strip().split(" ", 1)
            fp = _parts[1].strip() if len(_parts) == 2 else change.strip()

            try:
                guard.check_sensitive(fp)
            except SecurityViolation as e:
                violations.append(str(e))
                safe = False
                continue

            try:
                guard.check_protected(fp)
            except SecurityViolation as e:
                violations.append(str(e))
                safe = False

        return safe, violations

    def alert(self, message: str) -> str:
        """
        Format a security alert string for CLI display (spec §15).

        Example output:
            WARNING: Attempt to modify protected file .clockwork/context.yaml
        """
        return f"WARNING: {message}"

