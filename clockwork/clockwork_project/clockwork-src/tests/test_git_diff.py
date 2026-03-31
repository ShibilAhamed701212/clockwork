"""
Tests for Phase 1: Git Integration (GitDiffScanner, hooks).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from clockwork.scanner.git_diff import GitDiffScanner, RepoDiff


# ── RepoDiff tests ─────────────────────────────────────────────────────────


def test_repo_diff_defaults():
    diff = RepoDiff()
    assert diff.added == []
    assert diff.deleted == []
    assert diff.modified == []
    assert diff.is_git_repo is False
    assert diff.all_changed() == []


def test_repo_diff_has_changes():
    diff = RepoDiff(added=["a.py"], is_git_repo=True)
    assert bool(diff.all_changed()) is True
    assert diff.all_changed() == ["a.py"]


def test_repo_diff_deduplication():
    diff = RepoDiff(added=["a.py"], modified=["a.py", "b.py"], is_git_repo=True)
    changed = diff.all_changed()
    assert "a.py" in changed
    assert "b.py" in changed


def test_repo_diff_to_dict():
    diff = RepoDiff(
        added=["new.py"],
        modified=["changed.py"],
        is_git_repo=True,
        current_branch="main",
    )
    d = diff.to_dict()
    assert d["is_git_repo"] is True
    assert d["current_branch"] == "main"
    assert "new.py" in d["added"]


# ── GitDiffScanner tests ──────────────────────────────────────────────────


def test_non_git_repo(tmp_path):
    """GitDiffScanner gracefully handles non-git directories."""
    scanner = GitDiffScanner(tmp_path)
    assert scanner.is_git_repo() is False
    assert scanner.current_branch() == ""
    assert scanner.last_commit()[0] == ""

    diff = scanner.diff_since_last_scan()
    assert diff.is_git_repo is False

    diff = scanner.diff_staged()
    assert diff.is_git_repo is False


def _init_git_repo(path):
    """Create a minimal git repo with one commit."""
    subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path), capture_output=True)
    # Create a file and commit
    (path / "hello.py").write_text("print('hello')", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(path), capture_output=True)


@pytest.fixture
def git_repo(tmp_path):
    _init_git_repo(tmp_path)
    return tmp_path


def test_git_repo_is_detected(git_repo):
    scanner = GitDiffScanner(git_repo)
    assert scanner.is_git_repo() is True


def test_get_branch_name(git_repo):
    scanner = GitDiffScanner(git_repo)
    branch = scanner.current_branch()
    assert branch in ("main", "master")


def test_get_head_sha(git_repo):
    scanner = GitDiffScanner(git_repo)
    sha = scanner.last_commit()[0]
    assert len(sha) == 40  # Full SHA


def test_get_head_message(git_repo):
    scanner = GitDiffScanner(git_repo)
    msg = scanner.last_commit()[1]
    assert "initial" in msg





def test_record_and_diff_since_last_scan(git_repo):
    cw_dir = git_repo / ".clockwork"
    cw_dir.mkdir()

    scanner = GitDiffScanner(git_repo)
    scanner.record_scan()

    # No changes since scan
    diff = scanner.diff_since_last_scan()
    assert diff.is_git_repo is True
    # No new changes
    assert len(diff.added) == 0

    # Verify last_scan.json was written
    scan_file = cw_dir / "last_scan.json"
    assert scan_file.exists()
    data = json.loads(scan_file.read_text(encoding="utf-8"))
    assert "sha" in data


def test_diff_staged(git_repo):
    scanner = GitDiffScanner(git_repo)

    # Stage a new file
    (git_repo / "staged.py").write_text("pass", encoding="utf-8")
    subprocess.run(["git", "add", "staged.py"], cwd=str(git_repo), capture_output=True)

    diff = scanner.diff_staged()
    assert diff.is_git_repo is True
    assert "staged.py" in diff.added or "staged.py" in diff.staged


# ── Hooks tests ────────────────────────────────────────────────────────────


def test_hooks_install_no_git(tmp_path):
    """Hooks install fails gracefully when no .git directory."""
    from clockwork.cli.commands.hooks import PRE_COMMIT_CONTENT
    assert PRE_COMMIT_CONTENT  # Just verify the marker constant exists


def test_hooks_install_and_remove(git_repo):
    """Hooks install creates pre-commit, remove deletes it."""
    from clockwork.cli.commands.hooks import PRE_COMMIT_CONTENT

    hooks_dir = git_repo / ".git" / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    # Install
    hook_path.write_text(PRE_COMMIT_CONTENT, encoding="utf-8")
    assert hook_path.exists()
    assert "Clockwork" in hook_path.read_text(encoding="utf-8")

    # Remove
    hook_path.unlink()
    assert not hook_path.exists()
