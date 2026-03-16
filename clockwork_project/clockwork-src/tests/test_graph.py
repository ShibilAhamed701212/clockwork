"""
tests/test_graph.py
---------------------
Unit tests for the Knowledge Graph subsystem (spec §08).

Run with:
    pytest tests/test_graph.py -v
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.graph.builder  import GraphBuilder, _detect_layer, _detect_service
from clockwork.graph.graph_engine import GraphEngine
from clockwork.graph.models   import EdgeType, NodeType
from clockwork.graph.queries  import GraphQueryEngine
from clockwork.graph.storage  import GraphStorage


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_repo_map(tmp_path: Path) -> dict:
    """Minimal repo_map that exercises all node/edge types."""
    return {
        "project_name": "test_project",
        "total_files": 5,
        "languages": {"Python": 4, "YAML": 1},
        "files": [
            {
                "path": "clockwork/scanner/scanner.py",
                "language": "Python",
                "size_bytes": 2000,
                "symbols": [
                    {"name": "RepositoryScanner", "kind": "class"},
                    {"name": "scan",               "kind": "function"},
                ],
                "imports": [
                    "clockwork.scanner.models",
                    "clockwork.scanner.filters",
                    "pathlib.Path",
                    "typer",
                ],
            },
            {
                "path": "clockwork/scanner/models.py",
                "language": "Python",
                "size_bytes": 1500,
                "symbols": [{"name": "ScanResult", "kind": "class"}],
                "imports": ["dataclasses", "pathlib.Path"],
            },
            {
                "path": "clockwork/scanner/filters.py",
                "language": "Python",
                "size_bytes": 800,
                "symbols": [{"name": "ScanFilter", "kind": "class"}],
                "imports": ["pathlib.Path"],
            },
            {
                "path": "clockwork/cli/app.py",
                "language": "Python",
                "size_bytes": 1000,
                "symbols": [{"name": "app", "kind": "function"}],
                "imports": ["typer", "clockwork.scanner.scanner"],
            },
            {
                "path": "clockwork/rules/default_rules.yaml",
                "language": "YAML",
                "size_bytes": 400,
                "symbols": [],
                "imports": [],
            },
        ],
    }


def _make_storage(tmp_path: Path) -> GraphStorage:
    db = tmp_path / ".clockwork" / "knowledge_graph.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    s = GraphStorage(db)
    s.open()
    s.initialise(drop_existing=True)
    return s


def _make_engine(tmp_path: Path) -> GraphEngine:
    cw = tmp_path / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    repo_map = _make_repo_map(tmp_path)
    (cw / "repo_map.json").write_text(json.dumps(repo_map), encoding="utf-8")
    return GraphEngine(tmp_path)


# ── GraphStorage ───────────────────────────────────────────────────────────

class TestGraphStorage:
    def test_creates_db_file(self, tmp_path):
        db = tmp_path / "test.db"
        s = GraphStorage(db)
        s.open()
        s.initialise()
        s.close()
        assert db.exists()

    def test_schema_has_required_tables(self, tmp_path):
        s = _make_storage(tmp_path)
        conn = sqlite3.connect(str(s.db_path))
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        conn.close()
        s.close()
        assert "nodes" in tables
        assert "edges" in tables
        assert "graph_meta" in tables

    def test_insert_and_retrieve_node(self, tmp_path):
        s = _make_storage(tmp_path)
        nid = s.insert_node(NodeType.FILE, "app.py", file_path="clockwork/cli/app.py")
        s.commit()
        nodes = s.fetch_nodes(kind=NodeType.FILE)
        s.close()
        assert any(n.node_id == nid for n in nodes)

    def test_get_or_create_is_idempotent(self, tmp_path):
        s = _make_storage(tmp_path)
        id1 = s.get_or_create_node(NodeType.LANGUAGE, "Python")
        id2 = s.get_or_create_node(NodeType.LANGUAGE, "Python")
        s.close()
        assert id1 == id2

    def test_insert_edge_deduplicates(self, tmp_path):
        s = _make_storage(tmp_path)
        a = s.insert_node(NodeType.FILE, "a.py")
        b = s.insert_node(NodeType.FILE, "b.py")
        e1 = s.insert_edge(a, b, EdgeType.IMPORTS)
        e2 = s.insert_edge(a, b, EdgeType.IMPORTS)
        s.close()
        assert e1 == e2

    def test_meta_roundtrip(self, tmp_path):
        s = _make_storage(tmp_path)
        s.set_meta("built_at", "2026-03-15")
        s.commit()
        val = s.get_meta("built_at")
        s.close()
        assert val == "2026-03-15"

    def test_count_nodes(self, tmp_path):
        s = _make_storage(tmp_path)
        s.insert_node(NodeType.FILE, "a.py")
        s.insert_node(NodeType.FILE, "b.py")
        s.commit()
        assert s.count_nodes() == 2
        s.close()

    def test_export_json_keys(self, tmp_path):
        s = _make_storage(tmp_path)
        s.insert_node(NodeType.FILE, "x.py")
        s.commit()
        data = s.export_json()
        s.close()
        assert "nodes" in data
        assert "edges" in data


# ── GraphBuilder ───────────────────────────────────────────────────────────

class TestGraphBuilder:
    def test_build_returns_stats(self, tmp_path):
        s = _make_storage(tmp_path)
        b = GraphBuilder(s)
        stats = b.build(_make_repo_map(tmp_path))
        s.close()
        assert stats.node_count > 0

    def test_file_nodes_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        nodes = s.fetch_nodes(kind=NodeType.FILE)
        s.close()
        paths = {n.file_path.replace("\\", "/") for n in nodes}
        assert "clockwork/scanner/scanner.py" in paths
        assert "clockwork/cli/app.py" in paths

    def test_language_nodes_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        nodes = s.fetch_nodes(kind=NodeType.LANGUAGE)
        s.close()
        labels = {n.label for n in nodes}
        assert "Python" in labels
        assert "YAML" in labels

    def test_layer_nodes_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        nodes = s.fetch_nodes(kind=NodeType.LAYER)
        s.close()
        assert len(nodes) > 0

    def test_symbol_nodes_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        classes   = s.fetch_nodes(kind=NodeType.CLASS)
        functions = s.fetch_nodes(kind=NodeType.FUNCTION)
        s.close()
        class_names = {n.label for n in classes}
        assert any("RepositoryScanner" in name for name in class_names)
        assert len(functions) > 0

    def test_import_edges_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        edges = s.fetch_edges(relationship=EdgeType.IMPORTS)
        s.close()
        assert len(edges) > 0

    def test_external_dep_nodes_created(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        deps = s.fetch_nodes(kind=NodeType.DEPENDENCY)
        s.close()
        dep_labels = {n.label for n in deps}
        assert "typer" in dep_labels  # typer is an external dep

    def test_layer_assignment(self, tmp_path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        files = s.fetch_nodes(kind=NodeType.FILE)
        s.close()
        layers = {n.file_path.replace("\\", "/"): n.layer for n in files}
        assert layers.get("clockwork/scanner/scanner.py") is not None


# ── Helper functions ───────────────────────────────────────────────────────

class TestHelpers:
    def test_detect_layer_frontend(self):
        assert _detect_layer("frontend/app.js") == "frontend"

    def test_detect_layer_backend(self):
        assert _detect_layer("backend/api.py") == "backend"

    def test_detect_layer_database(self):
        assert _detect_layer("db/models.py") == "database"

    def test_detect_layer_tests(self):
        assert _detect_layer("tests/test_scanner.py") == "tests"

    def test_detect_layer_infra(self):
        assert _detect_layer("infra/docker-compose.yml") == "infrastructure"

    def test_detect_service_returns_path(self):
        assert _detect_service("services/auth/handler.py") == "services/auth"

    def test_detect_service_no_match(self):
        assert _detect_service("clockwork/scanner/scanner.py") == ""


# ── GraphQueryEngine ───────────────────────────────────────────────────────

class TestGraphQueryEngine:
    def _build(self, tmp_path: Path):
        s = _make_storage(tmp_path)
        GraphBuilder(s).build(_make_repo_map(tmp_path))
        return GraphQueryEngine(s), s

    def test_who_depends_on_scanner(self, tmp_path):
        q, s = self._build(tmp_path)
        deps = q.who_depends_on("clockwork/scanner/scanner.py")
        s.close()
        paths = {n.file_path.replace("\\", "/") for n in deps}
        assert "clockwork/cli/app.py" in paths

    def test_dependencies_of_app(self, tmp_path):
        q, s = self._build(tmp_path)
        deps = q.dependencies_of("clockwork/cli/app.py")
        s.close()
        labels = {n.label for n in deps}
        # should include internal scanner module and external typer
        assert len(labels) > 0

    def test_is_safe_to_delete_used_file(self, tmp_path):
        q, s = self._build(tmp_path)
        safe, reasons = q.is_safe_to_delete("clockwork/scanner/scanner.py")
        s.close()
        assert safe is False
        assert len(reasons) > 0

    def test_is_safe_to_delete_isolated_file(self, tmp_path):
        q, s = self._build(tmp_path)
        safe, reasons = q.is_safe_to_delete("clockwork/rules/default_rules.yaml")
        s.close()
        assert safe is True
        assert reasons == []

    def test_layer_summary_returns_dict(self, tmp_path):
        q, s = self._build(tmp_path)
        summary = q.layer_summary()
        s.close()
        assert isinstance(summary, dict)
        assert len(summary) > 0

    def test_language_counts(self, tmp_path):
        q, s = self._build(tmp_path)
        counts = q.language_counts()
        s.close()
        assert "Python" in counts
        assert counts["Python"] >= 4

    def test_files_importing_typer(self, tmp_path):
        q, s = self._build(tmp_path)
        nodes = q.files_importing("typer")
        s.close()
        paths = {n.file_path.replace("\\", "/") for n in nodes}
        # both scanner.py and app.py import typer
        assert len(paths) >= 1

    def test_stats_returns_expected_keys(self, tmp_path):
        q, s = self._build(tmp_path)
        stats = q.stats()
        s.close()
        assert "nodes_by_kind" in stats
        assert "total_nodes"   in stats
        assert "total_edges"   in stats
        assert "layers"        in stats
        assert "languages"     in stats

    def test_export_has_nodes_and_edges(self, tmp_path):
        q, s = self._build(tmp_path)
        data = q.export()
        s.close()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0


# ── GraphEngine (integration) ──────────────────────────────────────────────

class TestGraphEngine:
    def test_build_creates_db(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats  = engine.build()
        engine.close()
        assert (tmp_path / ".clockwork" / "knowledge_graph.db").exists()
        assert stats.node_count > 0

    def test_build_then_query(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        q    = engine.query()
        deps = q.who_depends_on("clockwork/scanner/scanner.py")
        engine.close()
        assert len(deps) > 0

    def test_db_exists_after_build(self, tmp_path):
        engine = _make_engine(tmp_path)
        assert not engine.db_exists()
        engine.build()
        engine.close()
        assert engine.db_exists()

    def test_missing_repo_map_raises(self, tmp_path):
        (tmp_path / ".clockwork").mkdir()
        engine = GraphEngine(tmp_path)
        with pytest.raises(FileNotFoundError):
            engine.build()

    def test_context_manager(self, tmp_path):
        engine = _make_engine(tmp_path)
        with engine:
            stats = engine.build()
        assert stats.node_count > 0

    def test_rebuild_is_idempotent(self, tmp_path):
        engine = _make_engine(tmp_path)
        s1 = engine.build()
        s2 = engine.build()
        engine.close()
        assert s1.node_count == s2.node_count
        assert s1.edge_count == s2.edge_count

