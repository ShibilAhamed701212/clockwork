"""
clockwork/cli/commands/worktree.py
------------------------------------
`clockwork worktree` — manage git worktrees for parallel agent sessions.

Commands:
  clockwork worktree create <task-name>  — create worktree + branch
  clockwork worktree list                — show active worktrees
  clockwork worktree merge <task-name>   — check conflicts + merge
  clockwork worktree clean <task-name>   — remove worktree and branch
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule, json_output,
)

worktree_app = typer.Typer(
    name="worktree",
    help="Manage git worktrees for parallel agent sessions.",
    no_args_is_help=True,
)


@worktree_app.command("create")
def cmd_worktree_create(
    task_name: str = typer.Argument(..., help="Name for the task/branch."),
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Create a new worktree for parallel development."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Clockwork Worktree — Create")

    repo = _get_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    branch_name = f"feature/{task_name}"
    worktree_path = root.parent / f"{root.name}-{task_name}"

    if worktree_path.exists():
        error(f"Worktree path already exists: {worktree_path}")
        raise typer.Exit(code=1)

    try:
        # Create worktree with new branch
        repo.git.worktree("add", str(worktree_path), "-b", branch_name)

        # Copy .clockwork directory
        src_cw = root / ".clockwork"
        dst_cw = worktree_path / ".clockwork"
        if src_cw.is_dir():
            shutil.copytree(str(src_cw), str(dst_cw), dirs_exist_ok=True)

        if as_json:
            json_output({
                "created": True,
                "worktree_path": str(worktree_path),
                "branch": branch_name,
            })
        else:
            success(f"Worktree created: {worktree_path}")
            info(f"  Branch: {branch_name}")
            info(f"  .clockwork/ copied")
            rule()
            info(f"cd {worktree_path}")
            info("Start working on your task in the new worktree.")

    except Exception as exc:
        error(f"Failed to create worktree: {exc}")
        raise typer.Exit(code=1)


@worktree_app.command("list")
def cmd_worktree_list(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """List all active git worktrees."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Clockwork Worktree — List")

    repo = _get_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    try:
        worktrees = _list_worktrees(repo)

        if as_json:
            json_output({"worktrees": worktrees})
            return

        if not worktrees:
            info("No worktrees found.")
            return

        for wt in worktrees:
            path = wt.get("path", "")
            branch = wt.get("branch", "")
            has_clockwork = wt.get("has_clockwork", False)
            cw_mark = " [clockwork]" if has_clockwork else ""
            info(f"  {branch}  →  {path}{cw_mark}")

        rule()
        info(f"{len(worktrees)} worktree(s)")

    except Exception as exc:
        error(f"Failed to list worktrees: {exc}")
        raise typer.Exit(code=1)


@worktree_app.command("merge")
def cmd_worktree_merge(
    task_name: str = typer.Argument(..., help="Task name to merge."),
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Check for conflicts and merge a worktree branch."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Clockwork Worktree — Merge")

    repo = _get_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    branch_name = f"feature/{task_name}"

    # Check for conflicts
    try:
        conflicts = _predict_conflicts(repo, branch_name)

        if as_json:
            json_output({
                "branch": branch_name,
                "conflict_predicted": bool(conflicts),
                "conflicts": conflicts,
            })
            return

        if conflicts:
            warn(f"Potential conflicts detected in {len(conflicts)} file(s):")
            for f in conflicts:
                info(f"  ✗ {f}")
            rule()
            warn("Review conflicts before merging.")
        else:
            success("No conflicts predicted")
            info(f"Branch '{branch_name}' appears safe to merge.")
            info(f"Run: git merge {branch_name}")

    except Exception as exc:
        error(f"Failed to analyze merge: {exc}")
        raise typer.Exit(code=1)


@worktree_app.command("clean")
def cmd_worktree_clean(
    task_name: str = typer.Argument(..., help="Task name to clean up."),
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository.",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force removal."),
    as_json: bool = typer.Option(False, "--json", help="Emit JSON output."),
) -> None:
    """Remove a worktree and its branch after merge."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Clockwork Worktree — Clean")

    repo = _get_repo(root)
    if repo is None:
        error("Not a git repository.")
        raise typer.Exit(code=1)

    branch_name = f"feature/{task_name}"
    worktree_path = root.parent / f"{root.name}-{task_name}"

    try:
        # Remove worktree
        if worktree_path.exists():
            force_flag = "--force" if force else ""
            try:
                repo.git.worktree("remove", str(worktree_path), force_flag)
            except Exception:
                if force:
                    shutil.rmtree(str(worktree_path), ignore_errors=True)
                    repo.git.worktree("prune")
                else:
                    raise

        # Delete branch
        try:
            repo.git.branch("-d", branch_name)
        except Exception:
            if force:
                try:
                    repo.git.branch("-D", branch_name)
                except Exception:
                    pass

        if as_json:
            json_output({"cleaned": True, "branch": branch_name})
        else:
            success(f"Cleaned up worktree and branch: {branch_name}")

    except Exception as exc:
        error(f"Failed to clean worktree: {exc}")
        raise typer.Exit(code=1)


# ── Helpers ───────────────────────────────────────────────────────────────

def _get_repo(root: Path):
    """Get git repo object or None."""
    try:
        import git
        return git.Repo(root)
    except Exception:
        return None


def _list_worktrees(repo) -> list[dict]:
    """List all worktrees with metadata."""
    worktrees: list[dict] = []
    try:
        output = repo.git.worktree("list", "--porcelain")
        current: dict = {}
        for line in output.splitlines():
            if line.startswith("worktree "):
                if current:
                    worktrees.append(current)
                path = line.split(" ", 1)[1]
                current = {
                    "path": path,
                    "branch": "",
                    "has_clockwork": Path(path, ".clockwork").is_dir(),
                }
            elif line.startswith("branch "):
                current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
            elif line.startswith("HEAD "):
                current["head"] = line.split(" ", 1)[1]
        if current:
            worktrees.append(current)
    except Exception:
        pass
    return worktrees


def _predict_conflicts(repo, branch_name: str) -> list[str]:
    """Predict merge conflicts between current branch and target."""
    conflicts: list[str] = []
    try:
        # Get files modified in both branches
        current = set(repo.git.diff("--name-only", f"HEAD...{branch_name}").splitlines())

        # Check for files modified on both sides
        merge_base = repo.git.merge_base("HEAD", branch_name)
        current_changes = set(repo.git.diff("--name-only", merge_base, "HEAD").splitlines())
        branch_changes = set(repo.git.diff("--name-only", merge_base, branch_name).splitlines())

        conflicts = list(current_changes & branch_changes)
    except Exception:
        pass
    return conflicts
