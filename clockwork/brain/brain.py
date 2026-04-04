from __future__ import annotations

from clockwork.brain.brain_manager import BrainManager
from clockwork.brain.decision_engine import Decision, DecisionEngine
from clockwork.brain.meta_reasoning import MetaReasoning


class Brain:
    """v2-style coordinator that keeps existing BrainManager as execution backend."""

    def __init__(self, clockwork_dir=None) -> None:
        self.manager = BrainManager(clockwork_dir=clockwork_dir)
        self.decider = DecisionEngine()
        self.meta = MetaReasoning()

    def decide(self, action: dict, context: dict | None = None, rule_result: object | None = None) -> Decision:
        decision = self.decider.evaluate(action, context or {}, rule_result=rule_result)
        self.meta.evaluate_decision(decision, action)
        return decision

    def summary(self) -> dict:
        return self.meta.summary()

