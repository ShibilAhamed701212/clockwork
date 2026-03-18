import time
from pathlib import Path
from rules.rule_engine import RuleEngine
from rules.validators.structure_rules import StructureRules
from context.context_validator import ContextValidator
from cli.utils import output as out

REQUIRED_DIRS  = ["cli","scanner","context","rules","brain","graph","agents",
                  "validation","state","recovery","security","packaging",
                  "registry","config","logs",".clockwork"]
REQUIRED_FILES = [".clockwork/context.yaml",".clockwork/tasks.json",".clockwork/agents.json"]

class VerifyCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, json_mode: bool = False, explain: bool = False):
        out.check_initialized()
        out.header("System Verification")
        t0 = time.time()
        passed, failed, issues = 0, 0, []
        for d in REQUIRED_DIRS:
            if Path(d).exists():
                out.verbose("OK DIR  " + d)
                passed += 1
            else:
                out.error("MISSING DIR: " + d)
                issues.append("Missing dir: " + d)
                failed += 1
        for f in REQUIRED_FILES:
            if Path(f).exists():
                out.verbose("OK FILE " + f)
                passed += 1
            else:
                out.error("MISSING FILE: " + f)
                issues.append("Missing file: " + f)
                failed += 1
        engine = RuleEngine()
        ok, errors = StructureRules().validate_structure()
        if ok:
            out.success("Structure rules passed.")
            passed += 1
        else:
            for e in errors:
                out.error(e)
                issues.append(e)
            failed += len(errors)
        ctx_ok, ctx_errors = ContextValidator().validate(self.context.snapshot())
        if ctx_ok:
            out.success("Context valid.")
            passed += 1
        else:
            for e in ctx_errors:
                out.warn("Context: " + e)
        elapsed = round(time.time() - t0, 3)
        status  = "passed" if failed == 0 else "failed"
        if explain and issues:
            out.section("Issues")
            for issue in issues:
                out.list_items([issue + " -> Fix this before proceeding."])
        if json_mode:
            out.json_output({"status": status, "passed": passed, "failed": failed, "issues": issues, "duration": elapsed})
        else:
            out.result("Passed",   passed)
            out.result("Failed",   failed)
            out.result("Duration", str(elapsed) + "s")
            if failed == 0:
                out.success("Verification PASSED.")
            else:
                out.error("Verification FAILED — " + str(failed) + " issue(s).")
                out.error_with_hint("", "Run: clockwork repair")
        if failed > 0:
            self.state.mark_unhealthy(str(failed) + " checks failed")
        else:
            self.state.emit_event("integrity_verified", {"passed": passed})
        return failed == 0