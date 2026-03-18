from pathlib import Path
from packaging.loader import Loader

class LoadCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, package_path: str, merge: bool = False):
        print("[Load] Loading package: " + package_path)
        self.state.emit_event("load_started", {"path": package_path})

        print("[Load] Step 1: Taking safety snapshot before restore...")
        snap = self.context.take_snapshot("pre_load")
        print("[Load] Safety snapshot: " + snap)

        loader = Loader()

        print("[Load] Step 2: Inspecting package...")
        info = loader.inspect(package_path)
        if not info.get("valid"):
            print("[Load] Package invalid:")
            for e in info.get("errors", []):
                print("  - " + e)
            return None

        print("[Load] Package valid. Files: " + str(len(info.get("files",[]))))
        print("[Load] Project: " + info.get("metadata",{}).get("project_name","unknown"))

        print("[Load] Step 3: Restoring system state...")
        result = loader.load(package_path, merge=merge)

        print("[Load] Step 4: Reloading context engine...")
        self.context.load()

        self.context.record_action("package_loaded", agent="load_command")
        self.state.emit_event("load_completed", {"path": package_path})

        print("[Load] System restored successfully.")
        print("[Load] Architecture: " + self.context.get_architecture())
        print("[Load] Skills: " + ", ".join(self.context.get_skills()))
        return result

    def inspect(self, package_path: str):
        loader = Loader()
        info   = loader.inspect(package_path)
        print("[Load] Package inspection:")
        print("  Name:    " + info.get("name",""))
        print("  Valid:   " + str(info.get("valid",False)))
        print("  Size:    " + str(info.get("size_kb","?")) + " KB")
        print("  Files:   " + str(len(info.get("files",[]))))
        meta = info.get("metadata",{})
        print("  Project: " + meta.get("project_name","?"))
        print("  Version: " + meta.get("clockwork_version","?"))
        return info