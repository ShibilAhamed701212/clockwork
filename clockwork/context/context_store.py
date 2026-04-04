from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import yaml

CONTEXT_FILE = Path(".clockwork/context.yaml")
HISTORY_FILE = Path(".clockwork/context_history.json")
LOCK_FILE = Path(".clockwork/context.lock")
SNAPSHOT_DIR = Path(".clockwork/snapshots")


class ContextStore:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.context_file = self.repo_root / CONTEXT_FILE
        self.history_file = self.repo_root / HISTORY_FILE
        self.lock_file = self.repo_root / LOCK_FILE
        self.snapshot_dir = self.repo_root / SNAPSHOT_DIR
        self._data: dict = {}
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.context_file.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def acquire_lock(self) -> bool:
        if self.lock_file.exists():
            return False
        self.lock_file.write_text(str(time.time()), encoding="utf-8")
        return True

    def release_lock(self) -> None:
        if self.lock_file.exists():
            self.lock_file.unlink()

    def load(self) -> dict:
        if self.context_file.exists():
            self._data = yaml.safe_load(self.context_file.read_text(encoding="utf-8")) or {}
        else:
            self._data = {}
            self.persist(self._data)
        return self._data

    def persist(self, data: dict) -> None:
        if not self.acquire_lock():
            return
        try:
            self.context_file.write_text(yaml.safe_dump(data), encoding="utf-8")
            self._data = data
        finally:
            self.release_lock()

    def record_change(self, change: str, agent: str = "system") -> None:
        history = []
        if self.history_file.exists():
            history = json.loads(self.history_file.read_text(encoding="utf-8"))
        history.append({"timestamp": time.time(), "change": change, "agent": agent})
        self.history_file.write_text(json.dumps(history[-500:], indent=2), encoding="utf-8")

    def get_history(self) -> list[dict]:
        if self.history_file.exists():
            return json.loads(self.history_file.read_text(encoding="utf-8"))
        return []

    def snapshot(self, label: str = "") -> str:
        ts = str(int(time.time()))
        name = ((label + "_") if label else "") + ts + ".yaml"
        path = self.snapshot_dir / name
        path.write_text(yaml.safe_dump(self._data), encoding="utf-8")
        return str(path)

    def restore_snapshot(self, snap_path: str) -> dict:
        path = Path(snap_path)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {snap_path}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.persist(data)
        return data

    def list_snapshots(self) -> list[str]:
        return sorted(str(path) for path in self.snapshot_dir.glob("*.yaml"))

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def all(self) -> dict:
        return dict(self._data)

