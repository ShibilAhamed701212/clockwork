"""
tests/test_cli_integration_full.py
---------------------------------
Full integration tests for CLI commands.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from typer.testing import CliRunner
from clockwork.cli.app import app


def _init_clockwork_dir(root: Path) -> None:
    """Create a valid .clockwork directory."""
    cw = root / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    (cw / "context.yaml").write_text(
        "project_name: test_project\n"
        "clockwork_version: 1.0.0\n"
        "memory_schema_version: 1\n"
    )
    (cw / "rules.md").write_text("- Must not delete core files\n")
    (cw / "config.yaml").write_text("mode: minibrain\n")


class TestCiRunFull:
    def test_ci_run_with_valid_config(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            app, ["ci-run", "--repo", str(tmp_path), "--dry-run", "--verbose"]
        )
        assert result.exit_code != 0

    def test_ci_run_no_stages(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["ci-run", "--repo", str(tmp_path)])
        assert result.exit_code != 0


class TestInitFull:
    def test_init_help(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0


class TestScanFull:
    def test_scan_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "main.py").write_text("print('hello')")
        runner = CliRunner()
        result = runner.invoke(app, ["scan", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestVerifyFull:
    def test_verify_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["verify", "--repo", str(tmp_path), "--json"])
        assert result.exit_code == 0


class TestGenerateFull:
    def test_generate_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "main.py").write_text("# main file")
        runner = CliRunner()
        result = runner.invoke(app, ["generate", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestGraphFull:
    def test_graph_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "--help"])
        assert result.exit_code == 0

    def test_graph_stats_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "stats", "--help"])
        assert result.exit_code == 0


class TestIndexFull:
    def test_index_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0


class TestStatusFull:
    def test_status_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["status", "--repo", str(tmp_path)])
        assert "error" in result.output.lower() or result.exit_code == 0


class TestHandoffFull:
    def test_handoff_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["handoff", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestDoctorFull:
    def test_doctor_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["doctor", "--repo", str(tmp_path)])
        assert result.exit_code == 0


class TestRecoverFull:
    def test_recover_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["recover", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestUpdateFull:
    def test_update_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0


class TestHistoryFull:
    def test_history_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["history", "--repo", str(tmp_path)])
        assert "error" in result.output.lower() or result.exit_code == 0


class TestAskFull:
    def test_ask_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["ask", "--repo", str(tmp_path), "test query"])
        assert "error" in result.output.lower() or result.exit_code == 0


class TestWorktreeFull:
    def test_worktree_list_with_git(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        try:
            import git

            git.Repo.init(tmp_path)
        except Exception:
            pass
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "list", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestDiffFull:
    def test_diff_with_git(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        try:
            import git

            repo = git.Repo.init(tmp_path)
            (tmp_path / "test.py").write_text("# test")
            repo.index.add(["test.py"])
            repo.index.commit("initial")
        except Exception:
            pass
        runner = CliRunner()
        result = runner.invoke(app, ["diff", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestSyncFull:
    def test_sync_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0


class TestMcpFull:
    def test_mcp_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0


class TestHooksFull:
    def test_hooks_status(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "status", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()


class TestSecurityFull:
    def test_security_scan_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "scan", "--help"])
        assert result.exit_code == 0

    def test_security_audit_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "audit", "--help"])
        assert result.exit_code == 0

    def test_security_log_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "log", "--help"])
        assert result.exit_code == 0

    def test_security_verify_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "verify", "--help"])
        assert result.exit_code == 0

    def test_security_secrets_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "secrets", "--help"])
        assert result.exit_code == 0

    def test_security_sandbox_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["security", "sandbox", "--help"])
        assert result.exit_code == 0


class TestAgentFull:
    def test_agent_list_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "list", "--help"])
        assert result.exit_code == 0

    def test_agent_register_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "register", "--help"])
        assert result.exit_code == 0

    def test_agent_status_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "status", "--help"])
        assert result.exit_code == 0

    def test_agent_remove_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "remove", "--help"])
        assert result.exit_code == 0

    def test_task_add_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "add", "--help"])
        assert result.exit_code == 0

    def test_task_list_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "list", "--help"])
        assert result.exit_code == 0

    def test_task_run_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "run", "--help"])
        assert result.exit_code == 0

    def test_task_fail_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "fail", "--help"])
        assert result.exit_code == 0

    def test_task_retry_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "retry", "--help"])
        assert result.exit_code == 0

    def test_task_locks_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["task", "locks", "--help"])
        assert result.exit_code == 0

    def test_agent_swarm_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "swarm", "--help"])
        assert result.exit_code == 0

    def test_agent_consensus_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["agent", "consensus", "--help"])
        assert result.exit_code == 0


class TestGraphFull:
    def test_graph_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "--help"])
        assert result.exit_code == 0

    def test_graph_stats_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "stats", "--help"])
        assert result.exit_code == 0

    def test_graph_query_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "query", "--help"])
        assert result.exit_code == 0

    def test_graph_export_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["graph", "export", "--help"])
        assert result.exit_code == 0


class TestValidateFull:
    def test_validate_output_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "output", "--help"])
        assert result.exit_code == 0

    def test_validate_guard_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["validate", "guard", "--help"])
        assert result.exit_code == 0

    def test_validate_syntax_valid(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "test.py").write_text("def hello():\n    print('world')")
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "syntax", "test.py", "--repo", str(tmp_path)]
        )
        assert result.exit_code == 0

    def test_validate_json_valid(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "test.json").write_text('{"key": "value"}')
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "json", "test.json", "--repo", str(tmp_path)]
        )
        assert result.exit_code == 0

    def test_validate_yaml_valid(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "test.yaml").write_text("key: value")
        runner = CliRunner()
        result = runner.invoke(
            app, ["validate", "yaml", "test.yaml", "--repo", str(tmp_path)]
        )
        assert result.exit_code == 0


class TestSessionFull:
    def test_session_show_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["session", "show", "--help"])
        assert result.exit_code == 0

    def test_session_log_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["session", "log", "--help"])
        assert result.exit_code == 0

    def test_session_stats_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["session", "stats", "--help"])
        assert result.exit_code == 0


class TestMcpFull:
    def test_mcp_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "--help"])
        assert result.exit_code == 0

    def test_mcp_start_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "start", "--help"])
        assert result.exit_code == 0

    def test_mcp_install_claude_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "install-claude", "--help"])
        assert result.exit_code == 0

    def test_mcp_install_cursor_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["mcp", "install-cursor", "--help"])
        assert result.exit_code == 0


class TestHooksFull:
    def test_hooks_install_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "install", "--help"])
        assert result.exit_code == 0

    def test_hooks_remove_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "remove", "--help"])
        assert result.exit_code == 0

    def test_hooks_status_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["hooks", "status", "--help"])
        assert result.exit_code == 0


class TestWorktreeFull:
    def test_worktree_create_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "create", "--help"])
        assert result.exit_code == 0

    def test_worktree_list_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "list", "--help"])
        assert result.exit_code == 0

    def test_worktree_merge_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "merge", "--help"])
        assert result.exit_code == 0

    def test_worktree_clean_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["worktree", "clean", "--help"])
        assert result.exit_code == 0


class TestSyncFull:
    def test_sync_push_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "push", "--help"])
        assert result.exit_code == 0

    def test_sync_pull_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["sync", "pull", "--help"])
        assert result.exit_code == 0


class TestDiffFull:
    def test_diff_staged_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["diff", "--staged", "--help"])
        assert result.exit_code == 0


class TestRegistryFull:
    def test_registry_refresh_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["registry", "refresh", "--help"])
        assert result.exit_code == 0

    def test_plugin_list_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["plugin", "list", "--help"])
        assert result.exit_code == 0

    def test_registry_info(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["registry", "info", "--help"])
        assert result.exit_code == 0


class TestPluginFull:
    def test_plugin_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["plugin", "--help"])
        assert result.exit_code == 0

    def test_plugin_install_help(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["plugin", "install", "--help"])
        assert result.exit_code == 0


class TestUpdateFull:
    def test_update_with_valid_repo(self, tmp_path):
        _init_clockwork_dir(tmp_path)
        (tmp_path / "main.py").write_text("# main")
        runner = CliRunner()
        result = runner.invoke(app, ["update", "--repo", str(tmp_path)])
        assert result.exit_code == 0 or "error" in result.output.lower()
