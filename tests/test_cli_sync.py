"""Focused tests for `clockwork sync` command behavior."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
import typer

from clockwork.cli.commands import git_ops


class _FakeGit:
    def __init__(self) -> None:
        self.pull_calls: list[tuple] = []
        self.push_calls: list[tuple] = []

    def pull(self, *args):
        self.pull_calls.append(args)
        return "pull-ok"

    def push(self, *args):
        self.push_calls.append(args)
        return "push-ok"


class _FakeRepo:
    def __init__(self, *, dirty: bool = False, branch: str = "main") -> None:
        self._dirty = dirty
        self.active_branch = SimpleNamespace(name=branch)
        self.git = _FakeGit()

    def is_dirty(self, untracked_files: bool = True) -> bool:
        return self._dirty


def test_sync_pull_calls_git_pull(monkeypatch, tmp_path):
    repo = _FakeRepo(dirty=False)
    logs: list[tuple[str, str]] = []
    monkeypatch.setattr(git_ops, "_open_repo", lambda root: repo)
    monkeypatch.setattr(git_ops, "_log", lambda root, action, status, details: logs.append((action, status)))

    git_ops.cmd_sync_pull(
        repo_root=tmp_path,
        remote="origin",
        branch="main",
        rebase=True,
        allow_dirty=False,
        as_json=True,
    )

    assert repo.git.pull_calls == [("origin", "main", "--rebase")]
    assert logs[-1] == ("git_pull", "success")


def test_sync_push_calls_git_push(monkeypatch, tmp_path):
    repo = _FakeRepo(dirty=False)
    logs: list[tuple[str, str]] = []
    monkeypatch.setattr(git_ops, "_open_repo", lambda root: repo)
    monkeypatch.setattr(git_ops, "_log", lambda root, action, status, details: logs.append((action, status)))

    git_ops.cmd_sync_push(
        repo_root=tmp_path,
        remote="origin",
        branch="main",
        set_upstream=False,
        allow_dirty=False,
        as_json=True,
    )

    assert repo.git.push_calls == [("origin", "main")]
    assert logs[-1] == ("git_push", "success")


def test_sync_run_calls_pull_then_push(monkeypatch, tmp_path):
    repo = _FakeRepo(dirty=False)
    logs: list[tuple[str, str]] = []
    monkeypatch.setattr(git_ops, "_open_repo", lambda root: repo)
    monkeypatch.setattr(git_ops, "_log", lambda root, action, status, details: logs.append((action, status)))

    git_ops.cmd_sync_run(
        repo_root=tmp_path,
        remote="origin",
        branch="main",
        rebase=True,
        set_upstream=False,
        allow_dirty=False,
        as_json=True,
    )

    assert repo.git.pull_calls == [("origin", "main", "--rebase")]
    assert repo.git.push_calls == [("origin", "main")]
    assert logs[-1] == ("git_sync", "success")


def test_sync_pull_blocks_dirty_repo_by_default(monkeypatch, tmp_path):
    repo = _FakeRepo(dirty=True)
    monkeypatch.setattr(git_ops, "_open_repo", lambda root: repo)
    monkeypatch.setattr(git_ops, "_log", lambda *args, **kwargs: None)

    with pytest.raises(typer.Exit):
        git_ops.cmd_sync_pull(
            repo_root=tmp_path,
            remote="origin",
            branch="main",
            rebase=True,
            allow_dirty=False,
            as_json=True,
        )

    assert repo.git.pull_calls == []


def test_sync_pull_allows_dirty_when_flag_set(monkeypatch, tmp_path):
    repo = _FakeRepo(dirty=True)
    monkeypatch.setattr(git_ops, "_open_repo", lambda root: repo)
    monkeypatch.setattr(git_ops, "_log", lambda *args, **kwargs: None)

    git_ops.cmd_sync_pull(
        repo_root=tmp_path,
        remote="origin",
        branch="main",
        rebase=True,
        allow_dirty=True,
        as_json=True,
    )

    assert repo.git.pull_calls == [("origin", "main", "--rebase")]
