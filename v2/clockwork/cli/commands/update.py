from scanner.scanner import Scanner
from context.context_validator import ContextValidator

class UpdateCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state = state
        self.context = context

    def execute(self, root: str = "."):
        print("[Update] Starting context update pipeline...")
        self.state.emit_event("update_started", {})

        print("[Update] Step 1: Scanning repository...")
        scanner = Scanner(root=root)
        repo_map = scanner.run()

        print("[Update] Step 2: Taking pre-update snapshot...")
        snap = self.context.take_snapshot("pre_update")
        print("[Update] Snapshot: " + snap)

        print("[Update] Step 3: Merging scanner data into context...")
        self.context.sync_from_scanner(repo_map)

        print("[Update] Step 4: Validating updated context...")
        ok = self.context.validate(repo_map)
        if not ok:
            print("[Update] Validation failed — restoring snapshot.")
            self.context.restore_snapshot(snap)
            self.state.mark_unhealthy("Context update failed validation")
            return False

        print("[Update] Step 5: Recording update action...")
        self.context.record_action("context_updated", agent="update_command")

        self.state.emit_event("update_completed", {
            "architecture": repo_map.get("architecture", {}).get("type", ""),
            "files": repo_map.get("meta", {}).get("total_files", 0),
        })

        print("[Update] Context update complete.")
        print("[Update] Architecture: " + self.context.get_architecture())
        print("[Update] Skills: " + ", ".join(self.context.get_skills()))
        return True