import time
from pathlib import Path
from cli.utils import output as out

CLOCKWORK_DIR = Path(".clockwork")
REQUIRED_DIRS = [
    Path(".clockwork"), Path(".clockwork/plugins"),
    Path(".clockwork/packages"), Path(".clockwork/handoff"),
    Path(".clockwork/snapshots"), Path("logs"), Path("scanner/output"),
]
REQUIRED_FILES = {
    "context.yaml":  "",
    "repo_map.json": "{}",
    "tasks.json":    "[]",
    "agents.json":   "[]",
    "rules.yaml":    "",
}

class InitCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, json_mode: bool = False):
        out.header("Clockwork Init")
        for d in REQUIRED_DIRS:
            d.mkdir(parents=True, exist_ok=True)
        created = []
        for fname, default in REQUIRED_FILES.items():
            fp = CLOCKWORK_DIR / fname
            if not fp.exists():
                fp.write_text(default)
                created.append(str(fp))
                out.success("Created: " + str(fp))
            else:
                out.verbose("Exists:  " + str(fp))
        for lf in ["logs/system.log","logs/agent.log","logs/debug.log"]:
            p = Path(lf)
            if not p.exists():
                p.write_text("")
        self.state.emit_event("system_initialized", {"mode": self.settings.mode})
        self.context.initialize()
        self.state.persist()
        result = {"status": "initialized", "mode": self.settings.mode, "created": len(created), "time": time.time()}
        if json_mode:
            out.json_output(result)
        else:
            out.success("Clockwork initialized | Mode: " + self.settings.mode)
            out.info("Files created: " + str(len(created)))
        return result