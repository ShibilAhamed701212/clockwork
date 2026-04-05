"""
tests/test_cli_integration.py
-------------------------
CLI integration tests using Typer's test method.
"""

from __future__ import annotations

import sys
from pathlib import Path
import json

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from typer.testing import CliRunner
from clockwork.cli.app import app


class TestCiRunCLI:
    def test_ci_run_no_init(self):
        runner = CliRunner()
        result = runner.invoke(app, ["ci-run", "--repo", "/tmp/nonexistent"])
        assert result.exit_code != 0

    def test_ci_run_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["ci-run", "--help"])
        assert result.exit_code == 0

    def test_ci_run_dry_run(self, tmp_path):
        runner = CliRunner()
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        ctx = cw / "context.yaml"
        ctx.write_text("project_name: test\npipeline:\n  stages: []")
        result = runner.invoke(app, ["ci-run", "--repo", str(tmp_path), "--dry-run"])
        assert result.exit_code != 0


class TestWorktreeCLI:
    def test_worktree_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "--help"])
        assert result.exit_code == 0

    def test_worktree_create_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "create", "--help"])
        assert result.exit_code == 0

    def test_worktree_list_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "list", "--help"])
        assert result.exit_code == 0


class TestIndexCLI:
    def test_index_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0

    def test_index_build_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["index", "build", "--help"])
        assert result.exit_code == 0

    def test_index_search_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["index", "search", "--help"])
        assert result.exit_code == 0


class TestDiffCLI:
    def test_diff_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["diff", "--help"])
        assert result.exit_code == 0


class TestGenerateCLI:
    def test_generate_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["generate", "--help"])
        assert result.exit_code == 0


class TestUpdateCLI:
    def test_update_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0


class TestVerifyCLI:
    def test_verify_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["verify", "--help"])
        assert result.exit_code == 0

    def test_verify_no_init(self):
        runner = CliRunner()
        result = runner.invoke(app, ["verify", "--repo", "/tmp/nonexistent"])
        assert result.exit_code != 0


class TestHandoffCLI:
    def test_handoff_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["handoff", "--help"])
        assert result.exit_code == 0


class TestHistoryCLI:
    def test_history_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0


class TestRecoverCLI:
    def test_recover_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["recover", "--help"])
        assert result.exit_code == 0


class TestMcpCLI:
    def test_mcp_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0

    def test_mcp_start_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "start", "--help"])
        assert result.exit_code == 0


class TestHooksCLI:
    def test_hooks_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "--help"])
        assert result.exit_code == 0

    def test_hooks_install_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "install", "--help"])
        assert result.exit_code == 0


class TestAskCLI:
    def test_ask_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["ask", "--help"])
        assert result.exit_code == 0


class TestGitOpsCLI:
    def test_sync_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0

    def test_sync_pull_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "pull", "--help"])
        assert result.exit_code == 0


class TestDoctorCLI:
    def test_doctor_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["doctor", "--help"])
        assert result.exit_code == 0


class TestRegistryCLI:
    def test_registry_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["registry", "--help"])
        assert result.exit_code == 0

    def test_registry_info_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["registry", "info", "--help"])
        assert result.exit_code == 0

    def test_registry_search_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["registry", "search", "--help"])
        assert result.exit_code == 0


class TestStatusCLI:
    def test_status_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0


class TestValidateCLI:
    def test_validate_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0

    def test_validate_json_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "json", "--help"])
        assert result.exit_code == 0

    def test_validate_yaml_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "yaml", "--help"])
        assert result.exit_code == 0

    def test_validate_syntax_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "syntax", "--help"])
        assert result.exit_code == 0


class TestSessionCLI:
    def test_session_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["session", "--help"])
        assert result.exit_code == 0


class TestSecurityCLI:
    def test_security_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["security", "--help"])
        assert result.exit_code == 0

    def test_security_scan_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["security", "scan", "--help"])
        assert result.exit_code == 0


class TestAgentCLI:
    def test_agent_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0

    def test_task_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0


class TestGraphCLI:
    def test_graph_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "--help"])
        assert result.exit_code == 0


class TestPluginCLI:
    def test_plugin_help(self):
        runner = CliRunner()
        result = runner.invoke(app, ["plugin", "--help"])
        assert result.exit_code == 0
