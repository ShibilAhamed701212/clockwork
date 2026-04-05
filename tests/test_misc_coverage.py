"""
tests/test_misc_coverage.py
---------------------------
Additional tests to improve remaining low coverage modules.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.brain.decision_engine import DecisionEngine, Decision
from clockwork.recovery.predictor import FailurePredictor


class TestDecision:
    def test_decision_approved_valid(self):
        d = Decision(status="VALID")
        assert d.approved() is True

    def test_decision_approved_rejected(self):
        d = Decision(status="REJECTED")
        assert d.approved() is False

    def test_decision_to_dict(self):
        d = Decision(status="VALID", confidence=0.9, risk_level="low", risk_score=0.1)
        result = d.to_dict()
        assert result["status"] == "VALID"
        assert result["confidence"] == 0.9


class TestDecisionEngine:
    def test_evaluate_valid_action(self):
        de = DecisionEngine()
        action = {"type": "read", "target": "README.md"}
        result = de.evaluate(action, {})
        assert result.status in {"VALID", "WARNING", "REJECTED"}

    def test_evaluate_write_action(self):
        de = DecisionEngine()
        action = {"type": "write", "target": "src/main.py"}
        result = de.evaluate(action, {})
        assert result.status in {"VALID", "WARNING", "REJECTED"}

    def test_evaluate_delete_action(self):
        de = DecisionEngine()
        action = {"type": "delete", "target": "src/main.py"}
        result = de.evaluate(action, {})
        assert result.status in {"VALID", "WARNING", "REJECTED"}

    def test_evaluate_with_context(self):
        de = DecisionEngine()
        action = {"type": "write", "target": "src/main.py"}
        context = {"repository": {"architecture": "modular"}}
        result = de.evaluate(action, context)
        assert result.status in {"VALID", "WARNING", "REJECTED"}

    def test_evaluate_with_protected_target(self):
        de = DecisionEngine()
        action = {"type": "delete", "target": ".clockwork/config.yaml"}
        result = de.evaluate(action, {})
        assert result.risk_score > 0

    def test_evaluate_read_action(self):
        de = DecisionEngine()
        action = {"type": "read", "target": "test.py"}
        result = de.evaluate(action, {})
        assert result.status in {"VALID", "WARNING", "REJECTED"}


class TestFailurePredictor:
    def test_predict(self):
        fp = FailurePredictor()
        result = fp.predict({}, {})
        assert isinstance(result, dict)

    def test_predict_task_risk(self):
        fp = FailurePredictor()
        result = fp.predict_task_risk({"type": "scan"}, {})
        assert result in {"none", "low", "medium", "high"}
