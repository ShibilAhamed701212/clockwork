import time
import json
from pathlib import Path
from typing import Dict, List, Tuple

from validation.output_validator   import OutputValidator
from validation.hallucination_guard import HallucinationGuard
from validation.reality_check       import RealityCheck

VALIDATION_LOG = Path(".clockwork/validation_log.json")

class ValidationResult:
    def __init__(self, passed: bool, errors: List[str], warnings: List[str] = [],
                 score: float = 1.0, stage: str = ""):
        self.passed   = passed
        self.errors   = errors
        self.warnings = warnings
        self.score    = score
        self.stage    = stage

    def to_dict(self) -> Dict:
        return {"passed": self.passed, "errors": self.errors,
                "warnings": self.warnings, "score": self.score, "stage": self.stage}


class ValidationPipeline:
    def __init__(self, context: Dict = {}, rule_engine=None):
        self.context      = context
        self.rule_engine  = rule_engine
        self.output_val   = OutputValidator()
        self.halluc_guard = HallucinationGuard()
        self.reality      = RealityCheck(repo_map={})
        VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)

    def run(self, agent_output: Dict, action: Dict = {}) -> ValidationResult:
        t0      = time.time()
        errors  = []
        warnings= []
        score   = 1.0

        # Stage 1 — Structure validation
        ok, errs = self.output_val.validate(agent_output)
        if not ok:
            self._log(action, "structure", False, errs)
            return ValidationResult(False, errs, [], 0.0, "structure")
        print("[Validation] Stage 1 PASS: structure")

        # Stage 2 — Rule engine
        if self.rule_engine and action:
            result = self.rule_engine.validate(action)
            if not result.approved:
                errs = ["Rule engine: " + result.reason]
                self._log(action, "rules", False, errs)
                return ValidationResult(False, errs, [], 0.0, "rules")
        print("[Validation] Stage 2 PASS: rules")

        # Stage 3 — Hallucination guard
        proposed = agent_output.get("proposed_changes",[])
        for change in proposed:
            content = change.get("content","") or change.get("change","")
            fpath   = change.get("file","")
            ok, errs2 = self.halluc_guard.check_content(content, fpath)
            if not ok:
                warnings.extend(errs2)
                score -= 0.1 * len(errs2)
        ok2, ref_errs = self.halluc_guard.check_file_references(proposed)
        if not ok2:
            warnings.extend(ref_errs)
        print("[Validation] Stage 3 PASS: hallucination guard (warnings=" + str(len(warnings)) + ")")

        # Stage 4 — Reality check
        ok3, reality_errs = self.reality.full_check(agent_output, self.context)
        if not ok3:
            errors.extend(reality_errs)
            score -= 0.2 * len(reality_errs)
        print("[Validation] Stage 4 PASS: reality check")

        passed  = len(errors) == 0
        elapsed = round((time.time() - t0) * 1000, 1)
        print("[Validation] Pipeline complete: " + ("PASS" if passed else "FAIL") +
              " | " + str(elapsed) + "ms | score=" + str(round(score,3)))

        self._log(action, "complete", passed, errors + warnings)
        return ValidationResult(passed, errors, warnings, max(0.0, round(score,3)), "complete")

    def _log(self, action: Dict, stage: str, passed: bool, issues: List[str]):
        entry = {
            "timestamp": time.time(),
            "stage":     stage,
            "passed":    passed,
            "action":    action.get("type",""),
            "target":    action.get("target",""),
            "issues":    issues[:10],
        }
        log = []
        if VALIDATION_LOG.exists():
            try:
                log = json.loads(VALIDATION_LOG.read_text())
            except Exception:
                log = []
        log.append(entry)
        VALIDATION_LOG.write_text(json.dumps(log[-500:], indent=2))