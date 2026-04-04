from __future__ import annotations

import json
import time
from pathlib import Path

SESSION_FILE = Path(".clockwork/sessions.json")


class SessionTracker:
    def __init__(self, session_id: str, repo_root: Path | None = None) -> None:
        self.session_id = session_id
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.session_file = self.repo_root / SESSION_FILE
        self.start_time = time.time()
        self.events: list[dict] = []
        self._ensure_file()

    def _ensure_file(self) -> None:
        self.session_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.session_file.exists():
            self.session_file.write_text("[]", encoding="utf-8")

    def log(self, event_type: str, payload: dict | None = None) -> None:
        entry = {
            "session_id": self.session_id,
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload or {},
        }
        self.events.append(entry)
        sessions = json.loads(self.session_file.read_text(encoding="utf-8"))
        sessions.append(entry)
        self.session_file.write_text(json.dumps(sessions[-1000:], indent=2), encoding="utf-8")

    def duration(self) -> float:
        return round(time.time() - self.start_time, 2)

    def summary(self) -> dict:
        return {
            "session_id": self.session_id,
            "duration_s": self.duration(),
            "events": len(self.events),
        }

