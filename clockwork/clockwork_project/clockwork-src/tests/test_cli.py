"""
tests/test_cli.py
------------------
Unit tests for the Clockwork CLI subsystem.

Covers: init, scan, update, verify, handoff, graph
pack/load covered in tests/test_packaging.py

Run with:  pytest tests/test_cli.py -v
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
import yaml


# ── Helpers ────────────────────────────────────────────────────────────────

def _init_repo(root: Path) -> Path:
    """Run cmd_init against a temp directory and return .clockwork path."""
    from clockwork.cli.commands.init import _create_clockwork_dir
    _create_clockwork_dir(root / ".clockwork", project_name=root.name)
    return root / ".clockwork"


def _init_and_scan(root: Path) -> Path:
    """Init + scan a temp repo."""
    cw = _init_repo(root)
    # Create some source files
    (root / "main.py").write_text('print("hello")')
    (root / "app.py").write_text("# app")
    (root / "README.md").write_text("# Test")
    sub = root / "src"
    sub.mkdir()
    (sub / "utils.py").write_text("# utils")
    (root / ".env").write_text("SECRET=x")  # should be ignored

    from clockwork.cli.commands.scan import _scan_repository, _load_ignore_dirs
    ignore = _load_ignore_dirs(cw)
    repo_map = _scan_repository(root, ignore)
    (cw / "repo_map.json").write_text(json.dumps(repo_map, indent=2))
    return cw


# ── Init tests ─────────────────────────────────────────────────────────────

class TestInit:
    def test_creates_clockwork_dir(self, tmp_path):
        cw = _init_repo(tmp_path)
        assert cw.is_dir()

    def test_creates_required_files(self, tmp_path):
        cw = _init_repo(tmp_path)
        for name in ["context.yaml", "rules.md", "config.yaml",
                     "tasks.json", "skills.json", "agent_history.json"]:
            assert (cw / name).exists(), f"Missing {name}"

    def test_creates_subdirectories(self, tmp_path):
        cw = _init_repo(tmp_path)
        for sub in ["handoff", "packages", "plugins", "logs", "integrations"]:
            assert (cw / sub).is_dir(), f"Missing subdirectory {sub}"

    def test_context_yaml_is_valid(self, tmp_path):
        cw = _init_repo(tmp_path)
        ctx = yaml.safe_load((cw / "context.yaml").read_text())
        assert ctx["clockwork_version"] == "0.2.0"
        assert ctx["project_name"] == tmp_path.name

    def test_tasks_is_empty_list(self, tmp_path):
        cw = _init_repo(tmp_path)
        data = json.loads((cw / "tasks.json").read_text())
        assert data == []

    def test_agent_history_is_empty_list(self, tmp_path):
        cw = _init_repo(tmp_path)
        data = json.loads((cw / "agent_history.json").read_text())
        assert data == []


# ── Scan tests ─────────────────────────────────────────────────────────────

class TestScan:
    def test_scan_creates_repo_map(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        assert (cw / "repo_map.json").exists()

    def test_repo_map_valid_json(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        assert "total_files" in data
        assert "languages" in data
        assert "files" in data

    def test_detects_python_language(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        assert "Python" in data["languages"]

    def test_detects_entry_points(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        paths = [e for e in data["entry_points"]]
        assert any("main.py" in p or "app.py" in p for p in paths)

    def test_excludes_sensitive_files(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        file_names = [f["path"] for f in data["files"]]
        assert all(".env" not in p for p in file_names)

    def test_excludes_clockwork_dir(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        file_names = [f["path"] for f in data["files"]]
        assert all(".clockwork" not in p for p in file_names)

    def test_file_entries_have_required_fields(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        data = json.loads((cw / "repo_map.json").read_text())
        for entry in data["files"]:
            assert "path" in entry
            assert "language" in entry
            assert "size_bytes" in entry


# ── Update tests ───────────────────────────────────────────────────────────

class TestUpdate:
    def test_update_sets_primary_language(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        from clockwork.cli.commands.update import _derive_primary_language
        repo_map = json.loads((cw / "repo_map.json").read_text())
        lang = _derive_primary_language(repo_map)
        assert lang == "Python"

    def test_update_writes_context(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        repo_map = json.loads((cw / "repo_map.json").read_text())
        ctx = yaml.safe_load((cw / "context.yaml").read_text()) or {}

        from clockwork.cli.commands.update import _derive_primary_language, _detect_frameworks
        ctx["primary_language"] = _derive_primary_language(repo_map)
        ctx["frameworks"] = _detect_frameworks(tmp_path, repo_map)
        ctx["entry_points"] = repo_map.get("entry_points", [])

        (cw / "context.yaml").write_text(
            yaml.dump(ctx, default_flow_style=False), encoding="utf-8"
        )
        updated = yaml.safe_load((cw / "context.yaml").read_text())
        assert updated["primary_language"] == "Python"

    def test_framework_detection_typer(self, tmp_path):
        # requirements.txt must exist BEFORE scanning so it appears in repo_map
        (tmp_path / "requirements.txt").write_text("typer==0.12\nfastapi\n")
        cw = _init_and_scan(tmp_path)
        repo_map = json.loads((cw / "repo_map.json").read_text())
        from clockwork.cli.commands.update import _detect_frameworks
        frameworks = _detect_frameworks(tmp_path, repo_map)
        assert "Typer" in frameworks
        assert "FastAPI" in frameworks


# ── Verify tests ───────────────────────────────────────────────────────────

class TestVerify:
    def test_passes_on_valid_repo(self, tmp_path):
        _init_and_scan(tmp_path)
        from clockwork.cli.commands.verify import (
            VerificationResult, _check_required_files,
            _check_context_schema, _check_repo_map,
        )
        cw = tmp_path / ".clockwork"
        result = VerificationResult()
        _check_required_files(cw, result)
        _check_context_schema(cw, result)
        _check_repo_map(cw, result)
        assert result.passed
        assert not result.failures

    def test_fails_on_missing_context(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        from clockwork.cli.commands.verify import (
            VerificationResult, _check_required_files,
        )
        result = VerificationResult()
        _check_required_files(cw, result)
        assert not result.passed
        assert any("context.yaml" in f for f in result.failures)

    def test_warns_on_missing_repo_map(self, tmp_path):
        cw = _init_repo(tmp_path)
        from clockwork.cli.commands.verify import (
            VerificationResult, _check_repo_map,
        )
        result = VerificationResult()
        _check_repo_map(cw, result)
        assert any("repo_map" in w for w in result.warnings)
        # Should still pass (it's a warning not a failure)
        assert result.passed


# ── Handoff tests ──────────────────────────────────────────────────────────

class TestHandoff:
    def test_handoff_creates_files(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        from clockwork.cli.commands.handoff import _build_handoff, _build_brief
        ctx = yaml.safe_load((cw / "context.yaml").read_text()) or {}
        handoff = _build_handoff(ctx, note="test note")
        brief = _build_brief(handoff)

        (cw / "handoff").mkdir(exist_ok=True)
        (cw / "handoff" / "handoff.json").write_text(json.dumps(handoff))
        (cw / "handoff" / "next_agent_brief.md").write_text(brief)

        assert (cw / "handoff" / "handoff.json").exists()
        assert (cw / "handoff" / "next_agent_brief.md").exists()

    def test_handoff_json_structure(self, tmp_path):
        cw = _init_repo(tmp_path)
        ctx = yaml.safe_load((cw / "context.yaml").read_text()) or {}
        from clockwork.cli.commands.handoff import _build_handoff
        handoff = _build_handoff(ctx, note=None)
        assert "project_name" in handoff
        assert "generated_at" in handoff
        assert "current_tasks" in handoff

    def test_brief_contains_project_name(self, tmp_path):
        cw = _init_repo(tmp_path)
        ctx = yaml.safe_load((cw / "context.yaml").read_text()) or {}
        from clockwork.cli.commands.handoff import _build_handoff, _build_brief
        handoff = _build_handoff(ctx, note=None)
        brief = _build_brief(handoff)
        assert tmp_path.name in brief

    def test_handoff_note_appears_in_brief(self, tmp_path):
        cw = _init_repo(tmp_path)
        ctx = yaml.safe_load((cw / "context.yaml").read_text()) or {}
        from clockwork.cli.commands.handoff import _build_handoff, _build_brief
        handoff = _build_handoff(ctx, note="Continue work on the scanner.")
        brief = _build_brief(handoff)
        assert "Continue work on the scanner." in brief


# ── Graph tests ────────────────────────────────────────────────────────────

class TestGraph:
    def test_graph_creates_db(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        from clockwork.cli.commands.graph import _build_graph
        repo_map = json.loads((cw / "repo_map.json").read_text())
        db_path = cw / "knowledge_graph.db"
        node_count, edge_count = _build_graph(repo_map, db_path)
        assert db_path.exists()
        assert node_count > 0

    def test_graph_db_has_tables(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        from clockwork.cli.commands.graph import _build_graph
        repo_map = json.loads((cw / "repo_map.json").read_text())
        db_path = cw / "knowledge_graph.db"
        _build_graph(repo_map, db_path)

        conn = sqlite3.connect(db_path)
        tables = {
            row[0] for row in
            conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        conn.close()
        assert "nodes" in tables
        assert "edges" in tables

    def test_graph_contains_language_nodes(self, tmp_path):
        cw = _init_and_scan(tmp_path)
        from clockwork.cli.commands.graph import _build_graph
        repo_map = json.loads((cw / "repo_map.json").read_text())
        db_path = cw / "knowledge_graph.db"
        _build_graph(repo_map, db_path)

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT label FROM nodes WHERE kind='language'"
        ).fetchall()
        conn.close()
        labels = {r[0] for r in rows}
        assert "Python" in labels
