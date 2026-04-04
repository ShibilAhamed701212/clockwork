from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from clockwork.config.settings import Settings


@dataclass
class SystemState:
    session_id: str = ""
    mode: str = "safe"
    autonomy: str = "restricted"
    validation: str = "strict"
    current_task: str | None = None
    agent_count: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    started_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    healthy: bool = True
    events: list[dict] = field(default_factory=list)


class StateManager:
    STATE_FILE = Path(".clockwork/state.json")

    def __init__(self, settings: Settings, repo_root: Path | None = None) -> None:
        self.settings = settings
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.state_file = self.repo_root / self.STATE_FILE
        self.state = self._init_state(settings)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _init_state(self, settings: Settings) -> SystemState:
        return SystemState(
            session_id=str(uuid.uuid4()),
            mode=settings.mode,
            autonomy=settings.autonomy,
            validation=settings.validation,
        )

    def get(self) -> SystemState:
        return self.state

    def update(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.last_updated = time.time()

    def emit_event(self, event_type: str, payload: dict | None = None) -> None:
        self.state.events.append(
            {"type": event_type, "timestamp": time.time(), "payload": payload or {}}
        )

    def snapshot(self) -> dict:
        return asdict(self.state)

    def persist(self) -> None:
        self.state_file.write_text(json.dumps(self.snapshot(), indent=2), encoding="utf-8")

    def mark_unhealthy(self, reason: str) -> None:
        self.state.healthy = False
        self.emit_event("system_unhealthy", {"reason": reason})

    def reset(self) -> None:
        self.state = self._init_state(self.settings)

