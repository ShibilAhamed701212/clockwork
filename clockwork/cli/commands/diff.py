"""
clockwork diff — show what changed since last scan and impact analysis.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer
from clockwork.cli.output import header, info, warn, success, error, rule, json_output

def cmd_diff(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
    staged_only: bool = typer.Option(False, "--staged",
                                      help="Show only staged files."),
) -> None:
    """Show files changed since last scan with impact analysis."""
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not cw_dir.is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    from clockwork.scanner.git_diff import GitDiffScanner
    git = GitDiffScanner(root)

    if not git.is_git_repo():
        warn("Not a git repository. Showing index changes only.")

    diff = git.diff_staged() if staged_only else git.diff_since_last_scan()

    if as_json:
        json_output(diff.to_dict())
        return

    header("Clockwork Diff")
    if not diff.is_git_repo:
        warn("Not a git repository — diff unavailable.")
        return

    branch = diff.current_branch
    sha = diff.last_commit_sha[:8] if diff.last_commit_sha else "?"
    info(f"  Branch: {branch}  |  HEAD: {sha}  {diff.last_commit_message[:50]}")
    rule()

    all_changes = diff.all_changed()
    if not all_changes and not diff.untracked:
        success("No changes since last scan.")
        return

    db_path = cw_dir / "knowledge_graph.db"
    graph_available = db_path.exists()

    for fpath in (diff.added + diff.modified)[:20]:
        marker = "+" if fpath in diff.added else "~"
        info(f"  {marker} {fpath}")
        if graph_available:
            try:
                from clockwork.graph import GraphEngine
                ge = GraphEngine(root)
                deps = ge.query().who_depends_on(fpath)
                ge.close()
                if deps:
                    dep_paths = [d.file_path for d in deps[:3]]
                    warn(f"    dependents: {', '.join(dep_paths)}"
                         + (" ..." if len(deps) > 3 else ""))
            except Exception:
                pass

    for fpath in diff.deleted[:10]:
        info(f"  - {fpath}")
        if graph_available:
            try:
                from clockwork.graph import GraphEngine
                ge = GraphEngine(root)
                safe, reasons = ge.query().is_safe_to_delete(fpath)
                ge.close()
                if not safe:
                    warn(f"    UNSAFE to delete: {reasons[0][:60]}")
            except Exception:
                pass

    if diff.untracked:
        rule()
        info(f"  Untracked: {len(diff.untracked)} files (run clockwork scan to index)")
