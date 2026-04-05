"""
tests/test_graph_coverage.py
--------------------------
Additional tests to improve graph module coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.graph.node_manager import NodeManager


class TestNodeManager:
    def test_upsert_and_get(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        node_id = nm.upsert("function", "test_func", "test.py", "python")
        assert node_id > 0

        node = nm.get(node_id)
        assert node is not None
        assert node["name"] == "test_func"

    def test_find(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        nm.upsert("function", "func1", "a.py", "python")
        nm.upsert("function", "func2", "b.py", "python")

        results = nm.find(node_type="function")
        assert len(results) >= 2

    def test_delete(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        node_id = nm.upsert("class", "TestClass", "test.py", "python")

        nm.delete(node_id)
        node = nm.get(node_id)
        assert node is None

    def test_clear_by_file(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        nm.upsert("function", "func1", "test.py", "python")

        nm.clear_by_file("test.py")
        results = nm.find(name="func1")
        assert len(results) == 0

    def test_count(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        nm.upsert("function", "func1", "test.py", "python")
        nm.upsert("function", "func2", "test.py", "python")

        counts = nm.count()
        assert "function" in counts

    def test_all(self, tmp_path):
        db = tmp_path / "test.db"
        nm = NodeManager(db)
        nm.upsert("function", "func1", "test.py", "python")

        all_nodes = nm.all()
        assert len(all_nodes) > 0
