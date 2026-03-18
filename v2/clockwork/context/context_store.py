import yaml
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

CONTEXT_FILE  = Path(".clockwork/context.yaml")
HISTORY_FILE  = Path(".clockwork/context_history.json")
LOCK_FILE     = Path(".clockwork/context.lock")
SNAPSHOT_DIR  = Path(".clockwork/snapshots")

class ContextStore:
    def __init__(self):
        self._data: Dict = {}
        self._ensure_dirs()

    def _ensure_dirs(self):
        for p in [CONTEXT_FILE.parent, SNAPSHOT_DIR]:
            p.mkdir(parents=True, exist_ok=True)

    # ── Lock management ──────────────────────────────────────────
    def acquire_lock(self) -> bool:
        if LOCK_FILE.exists():
            print("[ContextStore] Lock already held — skipping.")
            return False
        LOCK_FILE.write_text(str(time.time()))
        return True

    def release_lock(self):
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()

    # ── Load ─────────────────────────────────────────────────────
    def load(self) -> Dict:
        if CONTEXT_FILE.exists():
            with open(CONTEXT_FILE, "r") as f:
                self._data = yaml.safe_load(f) or {}
        else:
            self._data = self._default_structure()
            self.persist(self._data)
        return self._data

    def _default_structure(self) -> Dict:
        return {
            "project": {"name": "", "type": "", "version": ""},
            "repository": {"architecture": "", "languages": {}, "frameworks": [], "dependencies": [], "components": {}},
            "context_state": {"summary": "", "current_task": "", "next_tasks": [], "blockers": [], "confidence": "low"},
            "memory": {"past_actions": [], "decisions": [], "failures": [], "patterns": []},
            "skills": {"required": []},
            "meta": {
                "context_version": 1,
                "clockwork_version": "2.0",
                "created_at": time.time(),
                "last_updated": time.time(),
                "initialized": False,
            }
        }

    # ── Persist ──────────────────────────────────────────────────
    def persist(self, data: Dict):
        if not self.acquire_lock():
            return
        try:
            data.setdefault("meta", {})["last_updated"] = time.time()
            with open(CONTEXT_FILE, "w") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            self._data = data
        finally:
            self.release_lock()

    # ── History tracking ─────────────────────────────────────────
    def record_change(self, change: str, agent: str = "system"):
        history = []
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE) as f:
                history = json.load(f)
        history.append({"timestamp": time.time(), "change": change, "agent": agent})
        with open(HISTORY_FILE, "w") as f:
            json.dump(history[-500:], f, indent=2)

    def get_history(self) -> List[Dict]:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE) as f:
                return json.load(f)
        return []

    # ── Snapshots ────────────────────────────────────────────────
    def snapshot(self, label: str = "") -> str:
        ts = str(int(time.time()))
        name = (label + "_" if label else "") + ts + ".yaml"
        snap_path = SNAPSHOT_DIR / name
        with open(snap_path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False)
        print("[ContextStore] Snapshot saved: " + name)
        return str(snap_path)

    def restore_snapshot(self, snap_path: str) -> Dict:
        p = Path(snap_path)
        if not p.exists():
            raise FileNotFoundError("Snapshot not found: " + snap_path)
        with open(p) as f:
            data = yaml.safe_load(f) or {}
        self.persist(data)
        print("[ContextStore] Snapshot restored: " + snap_path)
        return data

    def list_snapshots(self) -> List[str]:
        return sorted([str(p) for p in SNAPSHOT_DIR.glob("*.yaml")])

    # ── Direct access ────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def all(self) -> Dict:
        return dict(self._data)