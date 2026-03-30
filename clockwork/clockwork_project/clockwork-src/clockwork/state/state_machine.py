from __future__ import annotations

from collections.abc import Callable

TRANSITIONS = {
    "idle": ["scanning", "loading"],
    "scanning": ["indexing", "failed"],
    "indexing": ["ready", "failed"],
    "loading": ["ready", "failed"],
    "ready": ["executing", "idle"],
    "executing": ["validating", "failed"],
    "validating": ["applying", "failed"],
    "applying": ["ready", "failed"],
    "failed": ["idle", "recovering"],
    "recovering": ["idle", "failed"],
}


class StateMachine:
    def __init__(self, initial: str = "idle") -> None:
        self.state = initial
        self.history: list[dict[str, str]] = []
        self._hooks: dict[str, list[Callable[[str, str], None]]] = {}

    def can_transition(self, target: str) -> bool:
        return target in TRANSITIONS.get(self.state, [])

    def transition(self, target: str) -> bool:
        if not self.can_transition(target):
            return False
        previous = self.state
        self.state = target
        self.history.append({"from": previous, "to": target})
        for hook in self._hooks.get(target, []):
            hook(previous, target)
        return True

    def on_enter(self, state: str, fn: Callable[[str, str], None]) -> None:
        self._hooks.setdefault(state, []).append(fn)

    def current(self) -> str:
        return self.state

    def is_ready(self) -> bool:
        return self.state == "ready"

    def is_failed(self) -> bool:
        return self.state == "failed"

