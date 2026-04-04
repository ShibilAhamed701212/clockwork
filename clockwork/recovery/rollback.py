from __future__ import annotations

import shutil
import time
from pathlib import Path

ROLLBACK_DIR = Path(".clockwork/rollback")


class RollbackManager:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.rollback_dir = self.repo_root / ROLLBACK_DIR
        self.rollback_dir.mkdir(parents=True, exist_ok=True)

    def checkpoint(self, label: str = "") -> str:
        ts = str(int(time.time()))
        name = f"{label}_{ts}" if label else ts
        destination = self.rollback_dir / name
        destination.mkdir(parents=True, exist_ok=True)
        for critical in [
            ".clockwork/context.yaml",
            ".clockwork/repo_map.json",
            ".clockwork/tasks.json",
            ".clockwork/agents.json",
        ]:
            source = self.repo_root / critical
            if source.exists():
                shutil.copy2(source, destination / source.name)
        return str(destination)

    def rollback(self, checkpoint_path: str) -> bool:
        path = Path(checkpoint_path)
        if not path.exists():
            return False
        for file_path in path.iterdir():
            target = self.clockwork_dir / file_path.name
            shutil.copy2(file_path, target)
        return True

    def list_checkpoints(self) -> list[dict]:
        checkpoints: list[dict] = []
        for path in sorted(self.rollback_dir.iterdir()):
            if path.is_dir():
                checkpoints.append(
                    {
                        "name": path.name,
                        "path": str(path),
                        "files": len(list(path.iterdir())),
                        "created": path.stat().st_mtime,
                    }
                )
        return checkpoints

    def latest(self) -> str | None:
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None
        return sorted(checkpoints, key=lambda item: item["created"])[-1]["path"]

    def cleanup_old(self, keep: int = 5) -> None:
        checkpoints = sorted(self.list_checkpoints(), key=lambda item: item["created"])
        for checkpoint in checkpoints[:-keep]:
            shutil.rmtree(checkpoint["path"], ignore_errors=True)

