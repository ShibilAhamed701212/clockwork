import json
import time
from pathlib import Path
from typing import Dict, List

SESSION_FILE = Path(".clockwork/sessions.json")

class SessionTracker:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.events: List[Dict] = []
        self._ensure_file()

    def _ensure_file(self):
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not SESSION_FILE.exists():
            SESSION_FILE.write_text("[]")

    def log(self, event_type: str, payload: Dict = {}):
        entry = {
            "session_id": self.session_id,
            "event": event_type,
            "timestamp": time.time(),
            "payload": payload,
        }
        self.events.append(entry)
        sessions = json.loads(SESSION_FILE.read_text())
        sessions.append(entry)
        SESSION_FILE.write_text(json.dumps(sessions[-1000:], indent=2))

    def duration(self) -> float:
        return round(time.time() - self.start_time, 2)

    def summary(self) -> Dict:
        return {
            "session_id": self.session_id,
            "duration_s": self.duration(),
            "events": len(self.events),
        }