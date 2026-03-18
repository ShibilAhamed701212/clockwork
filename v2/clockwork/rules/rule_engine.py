import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rules.rule_parser import RuleParser
from rules.validators.structure_rules import StructureRules
from rules.validators.dependency_rules import DependencyRules
from rules.validators.safety_rules import SafetyRules

RULE_LOG     = Path(".clockwork/rule_log.json")
OVERRIDE_LOG = Path(".clockwork/override_log.json")

class RuleResult:
    def __init__(self, approved: bool, severity: str, reason: str, rule: str = ""):
        self.approved  = approved
        self.severity  = severity
        self.reason    = reason
        self.rule      = rule

    def __repr__(self):
        status = "APPROVED" if self.approved else "BLOCKED"
        return "[RuleEngine] " + status + " | " + self.severity + " | " + self.reason

class RuleEngine:
    def __init__(self, root: Path = Path(".")):
        self.root     = root
        self.parser   = RuleParser()
        self.rules    = self.parser.load()
        self.structure = StructureRules(root)
        self.dependency = DependencyRules(root)
        self.safety    = SafetyRules()
        self._cache: Dict[str, RuleResult] = {}
        self._ensure_logs()

    def _ensure_logs(self):
        RULE_LOG.parent.mkdir(parents=True, exist_ok=True)
        for log in [RULE_LOG, OVERRIDE_LOG]:
            if not log.exists():
                log.write_text("[]")

    # ── Primary validation gate ──────────────────────────────────
    def validate(self, action: Dict) -> RuleResult:
        action_type = action.get("type", "unknown")
        target      = action.get("target", "")
        content     = action.get("content", "")
        deps        = action.get("dependencies", [])

        results: List[RuleResult] = []

        # Layer 1 — Safety (highest priority)
        results.append(self._run_safety(action_type, target, content))

        # Layer 2 — Structure
        results.append(self._run_structure(action_type, target))

        # Layer 3 — Dependency
        if deps:
            results.append(self._run_dependency(deps))

        # Conflict resolution — highest priority violation wins
        results.sort(key=lambda r: self._severity_score(r.severity), reverse=True)

        final = results[0] if results else RuleResult(True, "none", "No rules evaluated")
        self._log(action, final)
        return final

    def _run_safety(self, action_type: str, target: str, content: str) -> RuleResult:
        if action_type in ("delete", "overwrite"):
            ok, msg = self.safety.validate_file_operation(action_type, target)
            if not ok:
                return RuleResult(False, "high", msg, "safety.file_operation")

        if content:
            ok, violations = self.safety.validate_code_content(content, target)
            if not ok:
                return RuleResult(False, "high", violations[0], "safety.code_content")

        return RuleResult(True, "none", "Safety checks passed", "safety")

    def _run_structure(self, action_type: str, target: str) -> RuleResult:
        if action_type in ("modify", "delete", "overwrite"):
            ok, severity, msg = self.structure.validate_change(target)
            if not ok:
                return RuleResult(False, severity, msg, "structure.protected_file")

        if action_type == "create" and target.endswith(".py"):
            ok, msg = self.structure.check_test_exists(target)
            if not ok and self.parser.is_enabled("development", "new_module_requires_test"):
                return RuleResult(False, "medium", msg, "structure.test_required")

        return RuleResult(True, "none", "Structure checks passed", "structure")

    def _run_dependency(self, deps: List[Dict]) -> RuleResult:
        ok, conflicts = self.dependency.validate_no_conflicts(deps)
        if not ok:
            return RuleResult(False, "medium", " | ".join(conflicts), "dependency.conflict")
        return RuleResult(True, "none", "Dependency checks passed", "dependency")

    # ── Consistency check ────────────────────────────────────────
    def enforce_consistency(self, context: Dict, repo_map: Dict) -> Tuple[bool, List[str]]:
        issues = []
        ctx_arch = context.get("repository", {}).get("architecture", "")
        map_arch = repo_map.get("architecture", {}).get("type", "")
        if ctx_arch and map_arch and ctx_arch != map_arch:
            issues.append("Architecture inconsistency: context=" + ctx_arch + " repo=" + map_arch)

        if self.parser.is_enabled("context", "context_must_match_repository"):
            ctx_langs = set(context.get("repository", {}).get("languages", {}).keys())
            map_langs = set(repo_map.get("languages", {}).get("languages", {}).keys())
            drift = ctx_langs - map_langs
            if drift:
                issues.append("Language drift: " + str(drift))

        return len(issues) == 0, issues

    # ── Override system ──────────────────────────────────────────
    def override(self, rule_name: str, reason: str, user: str = "developer") -> bool:
        entry = {
            "timestamp": time.time(),
            "rule": rule_name,
            "reason": reason,
            "user": user,
        }
        log = json.loads(OVERRIDE_LOG.read_text())
        log.append(entry)
        OVERRIDE_LOG.write_text(json.dumps(log, indent=2))
        print("[RuleEngine] Override logged: " + rule_name + " by " + user)
        return True

    def get_overrides(self) -> List[Dict]:
        return json.loads(OVERRIDE_LOG.read_text())

    # ── Logging ──────────────────────────────────────────────────
    def _log(self, action: Dict, result: RuleResult):
        entry = {
            "timestamp": time.time(),
            "action": action.get("type", ""),
            "target": action.get("target", ""),
            "rule": result.rule,
            "status": "allowed" if result.approved else "blocked",
            "severity": result.severity,
            "details": result.reason,
        }
        log = json.loads(RULE_LOG.read_text())
        log.append(entry)
        RULE_LOG.write_text(json.dumps(log[-2000:], indent=2))

    def get_log(self, last_n: int = 50) -> List[Dict]:
        log = json.loads(RULE_LOG.read_text())
        return log[-last_n:]

    # ── Severity scoring for conflict resolution ─────────────────
    def _severity_score(self, severity: str) -> int:
        return {"high": 3, "medium": 2, "low": 1, "none": 0}.get(severity, 0)

    # ── Scan all source files for safety violations ──────────────
    def scan_repository(self, files: List[Path]) -> List[str]:
        all_violations = []
        for f in files:
            if f.suffix in (".py", ".js", ".ts"):
                ok, violations = self.safety.scan_file(f)
                if not ok:
                    all_violations.extend(violations)
        return all_violations