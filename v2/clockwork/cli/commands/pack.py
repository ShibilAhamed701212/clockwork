import time
from pathlib import Path
from packaging.packer import Packer
from rules.rule_engine import RuleEngine
from context.context_validator import ContextValidator

class PackCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, label: str = ""):
        print("[Pack] Starting packaging pipeline...")
        self.state.emit_event("pack_started", {})

        print("[Pack] Step 1: Validating context...")
        ctx = self.context.snapshot()
        validator = ContextValidator()
        ok, errors = validator.validate(ctx)
        if not ok:
            print("[Pack] Context validation failed:")
            for e in errors:
                print("  - " + e)
            if self.settings.is_safe_mode():
                print("[Pack] Aborting — safe mode requires valid context.")
                return None

        print("[Pack] Step 2: Rule engine check...")
        rule_engine = RuleEngine()
        action = {"type": "pack", "target": ".clockwork/"}
        result = rule_engine.validate(action)
        if not result.approved:
            print("[Pack] Rule engine blocked packaging: " + result.reason)
            return None

        print("[Pack] Step 3: Taking context snapshot...")
        snap = self.context.take_snapshot("pre_pack")
        print("[Pack] Snapshot: " + snap)

        print("[Pack] Step 4: Assembling package...")
        project_name = ctx.get("project", {}).get("name", "clockwork_project")
        packer = Packer()
        pkg_path = packer.pack(project_name=project_name, label=label)

        self.context.record_action("system_packaged", agent="pack_command")
        self.state.emit_event("pack_completed", {"path": str(pkg_path)})

        print("[Pack] Package ready: " + str(pkg_path))
        pkgs = packer.list_packages()
        print("[Pack] Total packages stored: " + str(len(pkgs)))
        return pkg_path

    def list_packages(self):
        packer = Packer()
        pkgs   = packer.list_packages()
        if not pkgs:
            print("[Pack] No packages found.")
            return []
        print("[Pack] Available packages:")
        for p in pkgs:
            print("  " + p["name"] + " (" + str(p["size_kb"]) + " KB)")
        return pkgs