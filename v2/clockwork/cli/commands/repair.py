import json
from pathlib import Path
from rules.rule_engine      import RuleEngine
from recovery.recovery_engine import RecoveryEngine
from recovery.rollback      import RollbackManager
from cli.utils              import output as out

REQUIRED_DIRS = [
    "cli/commands","cli/utils","scanner/output","context/live_index",
    "context/schemas","rules/validators","brain","graph/storage",
    "agents/swarm","agents/sandbox","validation","state/snapshots",
    "recovery/logs","security/logs","packaging/format","registry/cache",
    "registry/api","config","logs",".clockwork",".clockwork/packages",
    ".clockwork/handoff",".clockwork/snapshots",".clockwork/rollback",
    "tests","docs",
]
REQUIRED_FILES = {
    ".clockwork/context.yaml":  "",
    ".clockwork/repo_map.json": "{}",
    ".clockwork/tasks.json":    "[]",
    ".clockwork/agents.json":   "[]",
    ".clockwork/failure_log.json": "[]",
}

class RepairCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self):
        out.check_initialized()
        out.header("Clockwork Repair")
        self.state.emit_event("repair_started", {})
        fixed = 0

        out.info("Step 1: Rebuilding directory structure...")
        for d in REQUIRED_DIRS:
            p = Path(d)
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                out.success("Fixed dir: " + d)
                fixed += 1

        out.info("Step 2: Restoring missing state files...")
        for fpath, default in REQUIRED_FILES.items():
            p = Path(fpath)
            if not p.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(default)
                out.success("Fixed file: " + fpath)
                fixed += 1

        out.info("Step 3: Running self-healing recovery engine...")
        recovery = RecoveryEngine(context=self.context, state=self.state)
        issues_found = []
        for check_path in [".clockwork/context.yaml",".clockwork/repo_map.json"]:
            p = Path(check_path)
            if p.exists():
                try:
                    import yaml, json as _json
                    content = p.read_text()
                    if check_path.endswith(".yaml"):
                        yaml.safe_load(content)
                    else:
                        _json.loads(content)
                except Exception as e:
                    issues_found.append(check_path)
                    recovery.on_failure("invalid_context", str(e), path=check_path, severity="high")
                    out.warn("Healed corrupt file: " + check_path)
                    fixed += 1

        out.info("Step 4: Rebuilding live index...")
        try:
            from context.live_index.incremental_processor import IncrementalProcessor
            processor = IncrementalProcessor(context_engine=self.context)
            count = processor.rebuild_index(".")
            out.success("Index rebuilt: " + str(count) + " files")
        except Exception as e:
            out.warn("Index rebuild: " + str(e))

        out.info("Step 5: Running safety scan...")
        engine     = RuleEngine()
        violations = []
        try:
            from scanner.directory_walker import DirectoryWalker
            files      = DirectoryWalker(".").walk()
            violations = engine.scan_repository(files)
            if violations:
                out.warn("Safety violations: " + str(len(violations)))
                for v in violations[:5]:
                    out.error(v)
            else:
                out.success("No safety violations.")
        except Exception as e:
            out.warn("Safety scan: " + str(e))

        out.info("Step 6: Checking rollback checkpoints...")
        rollback = RollbackManager()
        cps      = rollback.list_checkpoints()
        out.info("Checkpoints available: " + str(len(cps)))
        rollback.cleanup_old(keep=5)

        recovery_stats = recovery.stats()
        self.state.emit_event("repair_completed", {
            "fixed":      fixed,
            "violations": len(violations),
            "recovery":   recovery_stats,
        })
        out.success("Repair complete. Fixed: " + str(fixed) +
                    " | Violations: " + str(len(violations)) +
                    " | Failures resolved: " + str(recovery_stats.get("resolved",0)))
        return {"fixed": fixed, "violations": len(violations), "recovery": recovery_stats}

    def rollback_last(self):
        out.header("Rollback")
        rollback = RollbackManager()
        latest   = rollback.latest()
        if not latest:
            out.error("No checkpoints available.")
            return False
        out.info("Rolling back to: " + latest)
        ok = rollback.rollback(latest)
        if ok:
            self.context.load()
            out.success("Rollback complete.")
        else:
            out.error("Rollback failed.")
        return ok