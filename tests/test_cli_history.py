"""Tests for `clockwork history` command behavior."""
from __future__ import annotations

import json

import pytest
import typer

from clockwork.cli.commands.history import cmd_history
from clockwork.state.history import append_activity


def test_history_json_output_with_limit(tmp_path, capsys):
    cw_dir = tmp_path / ".clockwork"
    append_activity(cw_dir, actor="agent-a", action="task", status="success", details={"id": 1})
    append_activity(cw_dir, actor="agent-b", action="verify", status="failed", details={"id": 2})

    cmd_history(
        repo_root=tmp_path,
        limit=1,
        actor=None,
        action=None,
        as_json=True,
    )
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload["count"] == 1
    assert payload["entries"][0]["actor"] == "agent-b"


def test_history_no_file_warns(tmp_path, capsys):
    (tmp_path / ".clockwork" / "logs").mkdir(parents=True)

    cmd_history(
        repo_root=tmp_path,
        limit=20,
        actor=None,
        action=None,
        as_json=False,
    )
    out = capsys.readouterr().out
    assert "No activity history found yet." in out


def test_history_skips_malformed_lines(tmp_path, capsys):
    logs_dir = tmp_path / ".clockwork" / "logs"
    logs_dir.mkdir(parents=True)
    history_file = logs_dir / "activity_history.jsonl"
    history_file.write_text(
        "not-json\n"
        '{"timestamp":"2026-01-01T00:00:00+00:00","actor":"mcp","action":"tool:git_pull","status":"success","details":{}}\n',
        encoding="utf-8",
    )

    cmd_history(
        repo_root=tmp_path,
        limit=20,
        actor=None,
        action=None,
        as_json=True,
    )
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload["malformed"] == 1
    assert payload["count"] == 1


def test_history_requires_init(tmp_path):
    with pytest.raises(typer.Exit):
        cmd_history(
            repo_root=tmp_path,
            limit=20,
            actor=None,
            action=None,
            as_json=False,
        )
