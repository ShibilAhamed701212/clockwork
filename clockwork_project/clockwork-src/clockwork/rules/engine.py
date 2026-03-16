from __future__ import annotations
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from clockwork.rules.evaluators import ArchitectureEvaluator, ContextEvaluator, DevelopmentEvaluator, SafetyEvaluator
from clockwork.rules.loader import RuleLoader
from clockwork.rules.models import RuleConfig, RuleReport, RuleSeverity, RuleViolation

logger = logging.getLogger(__name__)


class RuleEngine:
    _EVALUATOR_CLASSES = [SafetyEvaluator, ArchitectureEvaluator, DevelopmentEvaluator, ContextEvaluator]

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path.cwd()
        self._clockwork_dir = self._repo_root / ".clockwork"
        self._rule_log_path = self._clockwork_dir / "rule_log.json"
        self._override_log_path = self._clockwork_dir / "override_log.json"
        self._config: RuleConfig = RuleLoader(self._clockwork_dir).load()
        self._evaluators = [cls(self._config, self._repo_root) for cls in self._EVALUATOR_CLASSES]

    def evaluate(self, changed_files: list[str], deleted_files: list[str] | None = None) -> RuleReport:
        deleted_files = deleted_files or []
        all_files = list(set(changed_files + deleted_files))
        start = time.perf_counter()
        violations: list[RuleViolation] = []
        for evaluator in self._evaluators:
            try:
                violations.extend(evaluator.evaluate(changed_files, deleted_files))
            except Exception as exc:
                logger.error("Evaluator %s error: %s", evaluator.__class__.__name__, exc)
        duration_ms = (time.perf_counter() - start) * 1000
        violations = self._resolve_conflicts(violations)
        report = RuleReport(violations=violations, evaluated_files=all_files, duration_ms=duration_ms)
        self._log_report(report)
        return report

    def record_override(self, rule_id: str, reason: str, operator: str = "user") -> None:
        entry = {"timestamp": datetime.utcnow().isoformat(), "rule_id": rule_id, "reason": reason, "operator": operator}
        log = []
        if self._override_log_path.exists():
            try:
                log = json.loads(self._override_log_path.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(entry)
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._override_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    @property
    def config(self) -> RuleConfig:
        return self._config

    @staticmethod
    def _resolve_conflicts(violations: list[RuleViolation]) -> list[RuleViolation]:
        by_file: dict = {}
        for v in violations:
            by_file.setdefault(v.file_path, []).append(v)
        resolved = []
        for file_violations in by_file.values():
            if len(file_violations) <= 1:
                resolved.extend(file_violations)
                continue
            sorted_v = sorted(file_violations, key=lambda v: v.category.priority)
            top_priority = sorted_v[0].category.priority
            for v in sorted_v:
                if v.category.priority > top_priority and v.severity == RuleSeverity.BLOCK:
                    resolved.append(RuleViolation(rule_id=v.rule_id, category=v.category, severity=RuleSeverity.WARN, message=v.message + " [demoted]", file_path=v.file_path, timestamp=v.timestamp))
                else:
                    resolved.append(v)
        return resolved

    def _log_report(self, report: RuleReport) -> None:
        entry = {"timestamp": datetime.utcnow().isoformat(), "passed": report.passed, "duration_ms": round(report.duration_ms, 2), "violations": [v.to_dict() for v in report.violations]}
        log = []
        if self._rule_log_path.exists():
            try:
                log = json.loads(self._rule_log_path.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(entry)
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._rule_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
