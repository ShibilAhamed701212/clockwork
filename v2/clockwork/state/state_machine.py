from typing import Dict, List, Optional, Callable

TRANSITIONS = {
    "idle":       ["scanning", "loading"],
    "scanning":   ["indexing", "failed"],
    "indexing":   ["ready", "failed"],
    "loading":    ["ready", "failed"],
    "ready":      ["executing", "idle"],
    "executing":  ["validating", "failed"],
    "validating": ["applying", "failed"],
    "applying":   ["ready", "failed"],
    "failed":     ["idle", "recovering"],
    "recovering": ["idle", "failed"],
}

class StateMachine:
    def __init__(self, initial: str = "idle"):
        self.state = initial
        self.history: List[Dict] = []
        self._hooks: Dict[str, List[Callable]] = {}

    def can_transition(self, target: str) -> bool:
        return target in TRANSITIONS.get(self.state, [])

    def transition(self, target: str) -> bool:
        if not self.can_transition(target):
            print("[StateMachine] Invalid: " + self.state + " -> " + target)
            return False
        prev = self.state
        self.state = target
        self.history.append({"from": prev, "to": target})
        print("[StateMachine] " + prev + " -> " + target)
        for hook in self._hooks.get(target, []):
            hook(prev, target)
        return True

    def on_enter(self, state: str, fn: Callable):
        self._hooks.setdefault(state, []).append(fn)

    def current(self) -> str:
        return self.state

    def is_ready(self) -> bool:
        return self.state == "ready"

    def is_failed(self) -> bool:
        return self.state == "failed"