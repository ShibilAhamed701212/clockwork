import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

ROLLBACK_DIR = Path(".clockwork/rollback")

class RollbackManager:
    def __init__(self):
        ROLLBACK_DIR.mkdir(parents=True, exist_ok=True)

    def checkpoint(self, label: str = "") -> str:
        ts    = str(int(time.time()))
        name  = (label + "_" if label else "") + ts
        dest  = ROLLBACK_DIR / name
        dest.mkdir(parents=True, exist_ok=True)
        backed = 0
        for critical in [".clockwork/context.yaml",".clockwork/repo_map.json",
                         ".clockwork/tasks.json",".clockwork/agents.json"]:
            src = Path(critical)
            if src.exists():
                shutil.copy2(src, dest / src.name)
                backed += 1
        print("[Rollback] Checkpoint created: " + name + " (" + str(backed) + " files)")
        return str(dest)

    def rollback(self, checkpoint_path: str) -> bool:
        p = Path(checkpoint_path)
        if not p.exists():
            print("[Rollback] Checkpoint not found: " + checkpoint_path)
            return False
        restored = 0
        for f in p.iterdir():
            target = Path(".clockwork") / f.name
            shutil.copy2(f, target)
            restored += 1
        print("[Rollback] Restored " + str(restored) + " files from: " + p.name)
        return True

    def list_checkpoints(self) -> List[Dict]:
        checkpoints = []
        for p in sorted(ROLLBACK_DIR.iterdir()):
            if p.is_dir():
                checkpoints.append({
                    "name":    p.name,
                    "path":    str(p),
                    "files":   len(list(p.iterdir())),
                    "created": p.stat().st_mtime,
                })
        return checkpoints

    def latest(self) -> Optional[str]:
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None
        return sorted(checkpoints, key=lambda c: c["created"])[-1]["path"]

    def cleanup_old(self, keep: int = 5):
        checkpoints = sorted(self.list_checkpoints(), key=lambda c: c["created"])
        to_remove   = checkpoints[:-keep] if len(checkpoints) > keep else []
        for cp in to_remove:
            shutil.rmtree(cp["path"], ignore_errors=True)
        if to_remove:
            print("[Rollback] Cleaned " + str(len(to_remove)) + " old checkpoints.")