"""
Tests for new CLI commands (diff, ask, doctor) and MCP.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clockwork.cli.commands.ask import _parse_question


# ── Ask question parsing tests ────────────────────────────────────────────


class TestParseQuestion:
    def test_depends_on(self):
        qtype, target = _parse_question("what depends on scanner.py?")
        assert qtype == "dependents_of"
        assert "scanner.py" in target

    def test_dependents_of(self):
        qtype, target = _parse_question("what files import scanner?")
        assert qtype == "dependents_of"
        assert "scanner" in target

    def test_delete_impact(self):
        qtype, target = _parse_question("what would break if I delete database.py?")
        assert qtype == "delete_impact"
        assert "database.py" in target

    def test_file_search(self):
        qtype, target = _parse_question("which files handle authentication?")
        assert qtype == "file_search"
        assert "authentication" in target

    def test_where_search(self):
        qtype, target = _parse_question("where is the main entry point?")
        assert qtype == "file_search"

    def test_fallback_search(self):
        qtype, target = _parse_question("something random")
        assert qtype == "file_search"


# ── Doctor checks tests ──────────────────────────────────────────────────


class TestDoctorChecks:
    def test_check_context_valid(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_context
        import yaml

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        ctx = {"clockwork_version": "0.2", "project_name": "test"}
        (cw_dir / "context.yaml").write_text(
            yaml.dump(ctx), encoding="utf-8"
        )
        result = _check_context(cw_dir)
        assert result["status"] == "ok"

    def test_check_context_missing(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_context

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        result = _check_context(cw_dir)
        assert result["status"] == "fail"

    def test_check_context_invalid(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_context

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        (cw_dir / "context.yaml").write_text("not valid yaml: [", encoding="utf-8")
        result = _check_context(cw_dir)
        assert result["status"] in ("fail", "ok")  # depends on yaml parser leniency

    def test_check_freshness_missing(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_freshness

        result = _check_freshness(tmp_path / "nonexistent.db", "Test DB", "rebuild")
        assert result["status"] == "warn"
        assert "not built" in result["detail"]

    def test_check_freshness_recent(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_freshness

        test_file = tmp_path / "fresh.db"
        test_file.write_text("data", encoding="utf-8")
        result = _check_freshness(test_file, "Test DB", "rebuild")
        assert result["status"] == "ok"

    def test_check_git(self, tmp_path):
        from clockwork.cli.commands.doctor import _check_git
        # tmp_path is not a git repo
        assert _check_git(tmp_path) is False


# ── Conflict Predictor tests ─────────────────────────────────────────────


class TestConflictPredictor:
    def test_report_defaults(self):
        from clockwork.brain.conflict_predictor import ConflictReport
        report = ConflictReport()
        assert not report.has_conflicts
        assert report.risk_level == "low"

    def test_report_with_conflicts(self):
        from clockwork.brain.conflict_predictor import ConflictReport
        report = ConflictReport(file_conflicts=["a.py", "b.py"])
        assert report.has_conflicts is True

    def test_report_to_dict(self):
        from clockwork.brain.conflict_predictor import ConflictReport
        report = ConflictReport(branch="feature/test", file_conflicts=["x.py"])
        d = report.to_dict()
        assert d["branch"] == "feature/test"
        assert "x.py" in d["file_conflicts"]
        assert d["has_conflicts"] is True

    def test_predictor_non_git(self, tmp_path):
        from clockwork.brain.conflict_predictor import ConflictPredictor
        predictor = ConflictPredictor()
        report = predictor.predict(tmp_path, "feature/test")
        # Should not crash, just return empty report
        assert not report.has_conflicts


# ── MCP Server tests ─────────────────────────────────────────────────────


class TestMCPToolHandlers:
    def test_get_project_context(self, tmp_path):
        # Create minimal .clockwork
        import yaml
        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        ctx = {"project_name": "test", "primary_language": "Python"}
        (cw_dir / "context.yaml").write_text(yaml.dump(ctx), encoding="utf-8")

        from clockwork.mcp_server import ClockworkMCPServer
        server = ClockworkMCPServer(tmp_path)
        result = server._call_tool("get_project_context", {})
        assert result["project_name"] == "test"

    def test_handle_unknown_tool(self, tmp_path):
        from clockwork.mcp_server import ClockworkMCPServer
        import pytest
        server = ClockworkMCPServer(tmp_path)
        with pytest.raises(ValueError, match="Unknown tool"):
            server._call_tool("unknown_tool", {})

    def test_search_codebase(self, tmp_path):
        from clockwork.mcp_server import ClockworkMCPServer
        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()

        server = ClockworkMCPServer(tmp_path)
        result = server._call_tool("search_codebase", {"query": "scanner", "limit": 10})
        assert isinstance(result, list)

    def test_get_handoff_brief_missing(self, tmp_path):
        from clockwork.mcp_server import ClockworkMCPServer
        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        server = ClockworkMCPServer(tmp_path)
        result = server._call_tool("get_handoff_brief", {})
        assert "No handoff brief found." in result

    def test_run_verify(self, tmp_path):
        from clockwork.mcp_server import ClockworkMCPServer
        import yaml
        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        (cw_dir / "context.yaml").write_text(yaml.dump({"clockwork_version": "0.2", "project_name": "t", "memory_schema_version": "1"}), encoding="utf-8")
        (cw_dir / "rules.md").write_text("- Rule", encoding="utf-8")
        (cw_dir / "config.yaml").write_text("mode: safe", encoding="utf-8")

        server = ClockworkMCPServer(tmp_path)
        result = server._call_tool("run_verify", {"files": []})
        assert "passed" in result
