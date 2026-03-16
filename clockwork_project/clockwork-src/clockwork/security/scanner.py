"""
clockwork/security/scanner.py
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Any
from .file_guard import FileGuard
from .logger import SecurityLogger
from .models import RiskLevel, SecurityEvent, SecurityLogEntry, SecurityScanResult

_DANGEROUS_CODE_PATTERNS = [
    (r"exec\s*\(", "exec() call detected", RiskLevel.HIGH),
    (r"eval\s*\(", "eval() call detected", RiskLevel.HIGH),
    (r"__import__\s*\(", "Dynamic import detected", RiskLevel.MEDIUM),
    (r"subprocess\.call|subprocess\.run|os\.system", "Shell execution detected", RiskLevel.MEDIUM),
    (r"open\s*\(\s*['\"]\/etc", "Access to /etc in code", RiskLevel.HIGH),
    (r"socket\.connect", "Raw socket connection detected", RiskLevel.MEDIUM),
    (r"pickle\.loads", "Unsafe pickle.loads detected", RiskLevel.HIGH),
    (r"yaml\.load\s*\((?!.*Loader)", "Unsafe yaml.load (no Loader)", RiskLevel.MEDIUM),
]

_CODE_SCAN_SKIP: frozenset[str] = frozenset({
    "clockwork/security/scanner.py",
    "clockwork/security/file_guard.py",
    "tests/test_security.py",
})

PROTECTED_CLOCKWORK_FILES: frozenset[str] = frozenset({
    ".clockwork/context.yaml",
    ".clockwork/repo_map.json",
    ".clockwork/handoff/handoff.json",
})

def _compute_risk(issues, warnings):
    if len(issues) >= 5: return RiskLevel.CRITICAL
    if len(issues) >= 2: return RiskLevel.HIGH
    if len(issues) == 1: return RiskLevel.MEDIUM
    if warnings:         return RiskLevel.LOW
    return RiskLevel.LOW

class SecurityScanner:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.logger        = SecurityLogger(self.clockwork_dir)
        self.guard         = FileGuard(self.repo_root, self.clockwork_dir, self.logger)

    def scan(self) -> SecurityScanResult:
        t0 = time.perf_counter()
        issues: list[str] = []; warnings: list[str] = []; sensitive_found: list[str] = []
        for root_dir, dirs, files in os.walk(str(self.repo_root)):
            dirs[:] = [d for d in dirs if d not in {".git","__pycache__","node_modules",".venv","venv","dist","build"}]
            for fname in files:
                abs_path = os.path.join(root_dir, fname)
                try:
                    rel = str(Path(abs_path).relative_to(self.repo_root)).replace("\\", "/")
                except ValueError:
                    continue
                if self.guard.is_sensitive(rel):
                    sensitive_found.append(rel)
                    self.logger.log_sensitive_access(rel, blocked=False)
                    issues.append(f"Sensitive file found in repo: {rel}")
                if fname.endswith(".py") and rel not in _CODE_SCAN_SKIP:
                    try:
                        content = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
                        for pattern, msg, level in _DANGEROUS_CODE_PATTERNS:
                            if re.search(pattern, content):
                                entry = f"{msg} in {rel}"
                                if level == RiskLevel.HIGH: issues.append(entry)
                                else:                       warnings.append(entry)
                    except OSError:
                        pass
        protected_ok = self._check_protected_files(issues, warnings)
        elapsed = (time.perf_counter() - t0) * 1000
        self.logger.log(SecurityLogEntry.now(
            event=SecurityEvent.SCAN_COMPLETED,
            risk_level=RiskLevel.HIGH if issues else RiskLevel.LOW,
            detail=f"Scan completed: {len(issues)} issues, {len(warnings)} warnings",
            blocked=False,
        ))
        risk = _compute_risk(issues, warnings)
        return SecurityScanResult(passed=len(issues)==0, risk_level=risk, issues=issues,
            warnings=warnings, sensitive_files_found=sensitive_found,
            protected_files_ok=protected_ok, elapsed_ms=elapsed)

    def audit(self) -> dict[str, Any]:
        scan_result  = self.scan()
        recent_log   = self.logger.recent(50)
        plugin_issues = self._audit_plugins()
        agent_issues  = self._audit_agents()
        all_issues    = scan_result.issues + plugin_issues + agent_issues
        self.logger.log(SecurityLogEntry.now(
            event=SecurityEvent.AUDIT_COMPLETED,
            risk_level=RiskLevel.HIGH if all_issues else RiskLevel.LOW,
            detail=f"Audit: {len(all_issues)} total issues", blocked=False,
        ))
        return {"scan": scan_result.to_dict(), "plugin_issues": plugin_issues,
                "agent_issues": agent_issues, "recent_events": recent_log,
                "total_issues": len(all_issues), "risk_level": _compute_risk(all_issues, [])}

    def _audit_plugins(self) -> list[str]:
        issues: list[str] = []
        plugins_dir = self.clockwork_dir / "plugins"
        if not plugins_dir.exists(): return issues
        from .models import Permission
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir(): continue
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                issues.append(f"Plugin '{plugin_dir.name}' missing plugin.yaml manifest")
                continue
            try:
                import yaml
                data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            except Exception:
                issues.append(f"Plugin '{plugin_dir.name}' has invalid manifest")
                continue
            perms = data.get("permissions", [])
            dangerous = [p for p in perms if p in (Permission.SYSTEM_COMMAND, Permission.NETWORK_ACCESS)]
            if dangerous:
                issues.append(f"Plugin '{plugin_dir.name}' requests dangerous permissions: {', '.join(dangerous)}")
        return issues

    def _audit_agents(self) -> list[str]:
        issues: list[str] = []
        agents_path = self.clockwork_dir / "agents.json"
        if not agents_path.exists(): return issues
        try:
            data   = json.loads(agents_path.read_text(encoding="utf-8"))
            agents = data.get("agents", []) if isinstance(data, dict) else data
        except Exception:
            return issues
        for agent in agents:
            name = agent.get("name", "unknown")
            if "system_command" in agent.get("capabilities", []):
                issues.append(f"Agent '{name}' declares 'system_command' capability")
        return issues

    def _check_protected_files(self, issues, warnings) -> bool:
        ok = True
        for pf in PROTECTED_CLOCKWORK_FILES:
            full = self.repo_root / pf
            if not full.exists():
                warnings.append(f"Protected file missing: {pf}")
                ok = False
            else:
                try: full.read_text(encoding="utf-8")
                except Exception:
                    issues.append(f"Protected file unreadable: {pf}")
                    ok = False
        return ok
