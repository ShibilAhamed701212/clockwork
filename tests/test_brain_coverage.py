"""
tests/test_brain_coverage.py
---------------------------
Additional tests to improve brain module coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.brain.prioritization import PrioritizationEngine
from clockwork.brain.optimization_engine import OptimizationEngine
from clockwork.brain.planning_engine import PlanningEngine, Task
from clockwork.brain.meta_reasoning import MetaReasoning


class TestPrioritizationEngine:
    def test_score_task(self):
        pe = PrioritizationEngine()
        task = {"urgency": 0.8, "impact": 0.7, "risk": 0.3, "alignment": 0.6}
        result = pe.score_task(task)
        assert result > 0

    def test_rank(self):
        pe = PrioritizationEngine()
        tasks = [
            {"urgency": 0.3, "impact": 0.3, "risk": 0.3, "alignment": 0.3},
            {"urgency": 0.9, "impact": 0.9, "risk": 0.1, "alignment": 0.9},
        ]
        result = pe.rank(tasks)
        assert result[0]["priority_score"] > result[1]["priority_score"]

    def test_top(self):
        pe = PrioritizationEngine()
        tasks = [{"urgency": 0.3}, {"urgency": 0.9}, {"urgency": 0.6}]
        result = pe.top(tasks, n=2)
        assert len(result) == 2

    def test_classify(self):
        pe = PrioritizationEngine()
        assert pe.classify(0.8) == "critical"
        assert pe.classify(0.6) == "high"
        assert pe.classify(0.4) == "medium"
        assert pe.classify(0.1) == "low"


class TestOptimizationEngine:
    def test_optimize_plan_safe(self):
        oe = OptimizationEngine()
        tasks = [{"priority_score": 0.5}, {"priority_score": 0.9}]
        result = oe.optimize_plan(tasks, mode="safe")
        assert result[0]["priority_score"] >= result[1]["priority_score"]

    def test_optimize_plan_aggressive(self):
        oe = OptimizationEngine()
        tasks = [{"priority_score": 0.5}, {"priority_score": 0.9}]
        result = oe.optimize_plan(tasks, mode="aggressive")
        assert isinstance(result, list)

    def test_deduplicate(self):
        oe = OptimizationEngine()
        tasks = [
            {"name": "task1", "action": {}},
            {"name": "task1", "action": {}},
            {"name": "task2", "action": {}},
        ]
        result = oe.deduplicate(tasks)
        assert len(result) == 2

    def test_estimate_duration(self):
        oe = OptimizationEngine()
        tasks = [{"action": {"type": "scan"}}, {"action": {"type": "verify"}}]
        result = oe.estimate_duration(tasks)
        assert result > 0

    def test_generate_alternatives(self):
        oe = OptimizationEngine()
        action = {"type": "test"}
        result = oe.generate_alternatives(action)
        assert len(result) == 3


class TestPlanningEngine:
    def test_decompose(self):
        pe = PlanningEngine()
        result = pe.decompose("execute test", {})
        assert len(result) > 0
        assert all(isinstance(t, Task) for t in result)

    def test_order(self):
        pe = PlanningEngine()
        tasks = [
            Task("a", {"type": "test"}),
            Task("b", {"type": "test"}, ["a"]),
        ]
        result = pe.order(tasks)
        assert result[0].name == "a"

    def test_to_graph(self):
        pe = PlanningEngine()
        tasks = [Task("a", {"type": "test"})]
        result = pe.to_graph(tasks)
        assert "nodes" in result
        assert "edges" in result

    def test_next_ready(self):
        pe = PlanningEngine()
        tasks = [
            Task("a", {"type": "test"}),
            Task("b", {"type": "test"}, ["a"]),
        ]
        tasks[0].status = "completed"
        result = pe.next_ready(tasks, ["a"])
        assert len(result) == 1


class TestMetaReasoning:
    def test_evaluate_decision(self):
        from clockwork.brain.base import BrainResult, BrainStatus, RiskLevel

        mr = MetaReasoning()
        decision = BrainResult(
            status=BrainStatus.VALID,
            confidence=0.8,
            risk_level=RiskLevel.LOW,
            explanation="test",
        )
        result = mr.evaluate_decision(decision, {"action": "test"})
        assert "quality" in result

    def test_detect_pattern_no_history(self):
        mr = MetaReasoning()
        result = mr.detect_pattern()
        assert result is None

    def test_summary_empty(self):
        mr = MetaReasoning()
        result = mr.summary()
        assert result["total"] == 0
