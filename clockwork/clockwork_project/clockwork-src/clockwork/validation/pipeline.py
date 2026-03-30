from __future__ import annotations

import json
import time
from pathlib import Path

from clockwork.validation.hallucination_guard import HallucinationGuard
from clockwork.validation.output_validator import OutputValidator
from clockwork.validation.reality_check import RealityCheck

VALIDATION_LOG = Path(".clockwork/validation_log.json")


class ValidationResult:
    def __init__(
        self,
        passed: bool,
        errors: list[str],
        warnings: list[str] | None = None,
        score: float = 1.0,
        stage: str = "",
    ) -> None:
        self.passed = passed
        self.errors = errors
        self.warnings = warnings or []
        self.score = score
        self.stage = stage

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
            "stage": self.stage,
        }


class ValidationPipeline:
    def __init__(self, context: dict | None = None, rule_engine: object | None = None) -> None:
        self.context = context or {}
        self.rule_engine = rule_engine
        self.output_validator = OutputValidator()
        self.hallucination_guard = HallucinationGuard()
        self.reality_check = RealityCheck(repo_map={})
        VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)

    def run(self, agent_output: dict, action: dict | None = None) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        score = 1.0

        ok, structure_errors = self.output_validator.validate(agent_output)
        if not ok:
            errors.extend(structure_errors)
            score -= 0.3

        proposed = agent_output.get("proposed_changes", [])
        for change in proposed:
            content = str(change.get("content", "") or change.get("change", ""))
            file_path = str(change.get("file", ""))
            content_ok, content_issues = self.hallucination_guard.check_content(content, file_path)
            if not content_ok:
                warnings.extend(content_issues)
                score -= 0.1 * len(content_issues)

        refs_ok, reference_issues = self.hallucination_guard.check_file_references(proposed)
        if not refs_ok:
            warnings.extend(reference_issues)

        reality_ok, reality_issues = self.reality_check.full_check(agent_output, self.context)
        if not reality_ok:
            errors.extend(reality_issues)
            score -= 0.2 * len(reality_issues)

        passed = len(errors) == 0
        result = ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            score=max(0.0, round(score, 3)),
            stage="complete",
        )
        self._log(action or {}, "complete", passed, errors + warnings)
        return result

    def _log(self, action: dict, stage: str, passed: bool, issues: list[str]) -> None:
        entry = {
            "timestamp": time.time(),
            "stage": stage,
            "passed": passed,
            "action": action.get("type", ""),
            "target": action.get("target", ""),
            "issues": issues[:10],
        }
        log: list[dict] = []
        if VALIDATION_LOG.exists():
            try:
                log = json.loads(VALIDATION_LOG.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(entry)
        VALIDATION_LOG.write_text(json.dumps(log[-500:], indent=2), encoding="utf-8")

