"""
tests/test_agents_coverage.py
---------------------------
Additional tests for agents module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.agents.task_queue import TaskQueue, TaskItem
from clockwork.agents.task_graph import TaskGraph


class TestTaskItem:
    def test_task_item_creation(self):
        task = TaskItem(name="test", action={"type": "scan"})
        assert task.name == "test"
        assert task.status == "pending"

    def test_to_dict(self):
        task = TaskItem(name="test", action={"type": "scan"})
        d = task.to_dict()
        assert d["name"] == "test"
        assert "id" in d


class TestTaskQueue:
    def test_queue_push_pop(self):
        q = TaskQueue()
        task = TaskItem(name="test", action={"type": "scan"})
        q.push(task)
        assert q.size() == 1

    def test_queue_empty(self):
        q = TaskQueue()
        assert q.pop() is None

    def test_queue_complete(self):
        q = TaskQueue()
        task = TaskItem(name="test", action={"type": "scan"})
        q.push(task)
        q.complete(task.id, "success")
        completed = q.completed()
        assert len(completed) > 0

    def test_queue_fail(self):
        q = TaskQueue()
        task = TaskItem(name="test", action={"type": "scan"})
        q.push(task)
        q.fail(task.id, "error")
        failed = q.failed()
        assert len(failed) > 0

    def test_queue_pending(self):
        q = TaskQueue()
        task = TaskItem(name="test", action={"type": "scan"})
        q.push(task)
        pending = q.pending()
        assert len(pending) > 0

    def test_queue_stats(self):
        q = TaskQueue()
        task = TaskItem(name="test", action={"type": "scan"})
        q.push(task)
        stats = q.stats()
        assert "pending" in stats


class TestTaskGraph:
    def test_add(self):
        tg = TaskGraph()
        task = TaskItem(name="test", action={"type": "scan"})
        tg.add(task)
        assert tg.get("test") is not None

    def test_get(self):
        tg = TaskGraph()
        task = TaskItem(name="test", action={"type": "scan"})
        tg.add(task)
        found = tg.get("test")
        assert found is not None

    def test_roots(self):
        tg = TaskGraph()
        task = TaskItem(name="test", action={"type": "scan"}, deps=[])
        tg.add(task)
        roots = tg.roots()
        assert len(roots) > 0

    def test_ready(self):
        tg = TaskGraph()
        task = TaskItem(name="test", action={"type": "scan"}, deps=[])
        tg.add(task)
        ready = tg.ready([])
        assert len(ready) > 0

    def test_topological_order(self):
        tg = TaskGraph()
        task = TaskItem(name="test", action={"type": "scan"}, deps=[])
        tg.add(task)
        order = tg.topological_order()
        assert len(order) > 0
