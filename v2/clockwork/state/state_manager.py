import json
import time
import uuid
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from config.settings import Settings

@dataclass
class SystemState:
    session_id: str = ""
    mode: str = "safe"
    autonomy: str = "restricted"
    validation: str = "strict"
    current_task: Optional[str] = None
    agent_count: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    started_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    healthy: bool = True
    events: list = field(default_factory=list)

class StateManager:
    STATE_FILE = Path(".clockwork/state.json")

    def __init__(self, settings: Settings):
        self.settings = settings
        self.state = self._init_state(settings)
        self._ensure_dirs()

    def _init_state(self, settings: Settings) -> SystemState:
        return SystemState(
            session_id=str(uuid.uuid4()),
            mode=settings.mode,
            autonomy=settings.autonomy,
            validation=settings.validation,
        )

    def _ensure_dirs(self):
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    def get(self) -> SystemState:
        return self.state

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self.state, k):
                setattr(self.state, k, v)
        self.state.last_updated = time.time()

    def emit_event(self, event_type: str, payload: dict = {}):
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "payload": payload
        }
        self.state.events.append(event)
        print("[Event] " + event_type + " -> " + str(payload))

    def snapshot(self) -> dict:
        return asdict(self.state)

    def persist(self):
        with open(self.STATE_FILE, "w") as f:
            json.dump(self.snapshot(), f, indent=2)

    def mark_unhealthy(self, reason: str):
        self.state.healthy = False
        self.emit_event("system_unhealthy", {"reason": reason})

    def reset(self):
        self.state = self._init_state(self.settings)