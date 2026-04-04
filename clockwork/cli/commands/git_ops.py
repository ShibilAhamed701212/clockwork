"""
clockwork/cli/commands/git_ops.py
---------------------------------
`clockwork sync` — guarded git pull/push automation for agent workflows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import error, header, info, json_output, success, warn
from clockwork.state import append_activity

sync_app = typer.Typer(
    name="sync",
    help="Guarded git pull/push automation for AI agent workflows.",
    no_args_is_help=True,
)


def _open_repo(root: Path):
    try:
        import git

        return git.Repo(root)
    except Exception:
        return None


def _require_clean(repo, *, allow_dirty: bool) -> None:
    if allow_dirty:
        return
    if repo.is_dirty(untracked_files=True):
        raise RuntimeError(
            "Repository has uncommitted changes. Commit/stash first, or use --allow-dirty."
        )


def _current_branch(repo) -> str:
    try:
        return repo.active_branch.name
    except Exception:
        return "HEAD"


def _log(root: Path, action: str, status: str, details: dict) -> None:
    append_activity(
        root / ".clockwork",
        actor="sync_cli",
        action=action,
        status=status,
        details=details,
    )


@sync_app.command("pull")
def cmd_sync_pull(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    remote: str = typer.Option("origin", "--remote"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    rebase: bool = typer.Option(True, "--rebase/--merge"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Pull from remote with safety checks."""
    root = (repo_root or Path.cwd()).resolve()
    repo = _open_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    target_branch = branch or _current_branch(repo)
    details = {"remote": remote, "branch": target_branch, "rebase": rebase}

    try:
        _require_clean(repo, allow_dirty=allow_dirty)
        flags = ["--rebase"] if rebase else []
        output = repo.git.pull(remote, target_branch, *flags)
        details["output"] = output.strip()
        _log(root, "git_pull", "success", details)

        if as_json:
            json_output({"ok": True, **details})
            return

        header("Clockwork Sync Pull")
        success(f"Pulled {remote}/{target_branch}")
        if output.strip():
            info(output.strip())
    except Exception as exc:
        details["error"] = str(exc)
        _log(root, "git_pull", "failed", details)
        if as_json:
            json_output({"ok": False, **details})
            raise typer.Exit(code=1)
        error(f"Pull failed: {exc}")
        raise typer.Exit(code=1)


@sync_app.command("push")
def cmd_sync_push(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    remote: str = typer.Option("origin", "--remote"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    set_upstream: bool = typer.Option(False, "--set-upstream", "-u"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Push current branch to remote with safety checks."""
    root = (repo_root or Path.cwd()).resolve()
    repo = _open_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    target_branch = branch or _current_branch(repo)
    details = {"remote": remote, "branch": target_branch, "set_upstream": set_upstream}

    try:
        _require_clean(repo, allow_dirty=allow_dirty)
        if set_upstream:
            output = repo.git.push("-u", remote, target_branch)
        else:
            output = repo.git.push(remote, target_branch)
        details["output"] = output.strip()
        _log(root, "git_push", "success", details)

        if as_json:
            json_output({"ok": True, **details})
            return

        header("Clockwork Sync Push")
        success(f"Pushed {target_branch} to {remote}")
        if output.strip():
            info(output.strip())
    except Exception as exc:
        details["error"] = str(exc)
        _log(root, "git_push", "failed", details)
        if as_json:
            json_output({"ok": False, **details})
            raise typer.Exit(code=1)
        error(f"Push failed: {exc}")
        raise typer.Exit(code=1)


@sync_app.command("run")
def cmd_sync_run(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    remote: str = typer.Option("origin", "--remote"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    rebase: bool = typer.Option(True, "--rebase/--merge"),
    set_upstream: bool = typer.Option(False, "--set-upstream", "-u"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Pull then push as one guarded sync action."""
    root = (repo_root or Path.cwd()).resolve()
    repo = _open_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    target_branch = branch or _current_branch(repo)
    details = {
        "remote": remote,
        "branch": target_branch,
        "rebase": rebase,
        "set_upstream": set_upstream,
    }

    try:
        _require_clean(repo, allow_dirty=allow_dirty)
        pull_flags = ["--rebase"] if rebase else []
        pull_out = repo.git.pull(remote, target_branch, *pull_flags)
        if set_upstream:
            push_out = repo.git.push("-u", remote, target_branch)
        else:
            push_out = repo.git.push(remote, target_branch)

        details["pull"] = pull_out.strip()
        details["push"] = push_out.strip()
        _log(root, "git_sync", "success", details)

        if as_json:
            json_output({"ok": True, **details})
            return

        header("Clockwork Sync Run")
        success(f"Synced {remote}/{target_branch}")
        if pull_out.strip():
            info(f"pull: {pull_out.strip()}")
        if push_out.strip():
            info(f"push: {push_out.strip()}")
    except Exception as exc:
        details["error"] = str(exc)
        _log(root, "git_sync", "failed", details)
        if as_json:
            json_output({"ok": False, **details})
            raise typer.Exit(code=1)
        warn(f"Sync failed: {exc}")
        raise typer.Exit(code=1)

