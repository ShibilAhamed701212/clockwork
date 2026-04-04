from __future__ import annotations

from collections import deque


class EventQueue:
    def __init__(self) -> None:
        self._events: deque[dict] = deque()

    def push(self, event: dict) -> None:
        event = dict(event)
        event.setdefault("priority", _priority_for_path(str(event.get("path", ""))))
        self._events.append(event)

    def pop(self) -> dict:
        return self._events.popleft()

    def is_empty(self) -> bool:
        return len(self._events) == 0

    def size(self) -> int:
        return len(self._events)

    def drain_deduped(self) -> list[dict]:
        seen: dict[str, dict] = {}
        while self._events:
            event = self._events.popleft()
            key = str(event.get("path", ""))
            seen[key] = event
        return list(seen.values())

    def stats(self) -> dict:
        return {"pending": self.size()}


def _priority_for_path(path: str) -> str:
    lowered = path.lower()
    high_markers = ["requirements", "pyproject", "setup.py", ".clockwork", "config", "rules"]
    if any(marker in lowered for marker in high_markers):
        return "high"
    return "normal"


