"""
clockwork/cli/commands/status.py
---------------------------------
`clockwork status` — rich dashboard showing runtime state, git info,
context freshness, graph stats, and recent changes.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import error, header, info, rule, success, warn
from clockwork.config.settings import load_settings


def cmd_status(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    """Show comprehensive project status dashboard."""
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not cw_dir.is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    settings = load_settings(root)

    payload: dict = {
        "project_name": root.name,
        "mode": settings.mode,
        "validation": settings.validation,
    }

    # ── Git info ──────────────────────────────────────────────────────────
    git_info = _get_git_info(root)
    payload["git"] = git_info

    # ── Context info ──────────────────────────────────────────────────────
    ctx_info = _get_context_info(cw_dir)
    payload["context"] = ctx_info

    # ── Graph info ────────────────────────────────────────────────────────
    graph_info = _get_graph_info(cw_dir)
    payload["graph"] = graph_info

    # ── Index info ────────────────────────────────────────────────────────
    index_info = _get_index_info(cw_dir)
    payload["index"] = index_info

    # ── State/Recovery ────────────────────────────────────────────────────
    try:
        from clockwork.state.state_manager import StateManager
        from clockwork.recovery.recovery_engine import RecoveryEngine
        state_manager = StateManager(settings, repo_root=root)
        recovery = RecoveryEngine(state=state_manager, repo_root=root)
        payload["state"] = state_manager.snapshot()
        payload["recovery"] = recovery.stats()
    except Exception:
        payload["state"] = {}
        payload["recovery"] = {}

    if as_json:
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    # ── Rich dashboard output ─────────────────────────────────────────────
    project_name = ctx_info.get("project_name", root.name)
    header(f"Clockwork Status — {project_name}")

    # Git
    if git_info.get("is_git_repo"):
        branch = git_info.get("branch", "?")
        uncommitted = git_info.get("uncommitted", 0)
        untracked = git_info.get("untracked", 0)
        git_str = f"Git:     {branch} branch"
        if uncommitted:
            git_str += f", {uncommitted} uncommitted files"
        if untracked:
            git_str += f", {untracked} untracked"
        info(git_str)
    else:
        info("Git:     not a git repository")

    # Context
    last_updated = ctx_info.get("last_updated", "")
    task_count = ctx_info.get("task_count", 0)
    ctx_age = _format_age(last_updated) if last_updated else "never"
    info(f"Context: last updated {ctx_age}, {task_count} tasks")

    # Graph
    if graph_info.get("exists"):
        info(f"Graph:   {graph_info['nodes']} nodes, {graph_info['edges']} edges (built {_format_age(graph_info.get('built_at', ''))})")
    else:
        info("Graph:   not built (run: clockwork graph build)")

    # Index
    if index_info.get("exists"):
        info(f"Index:   {index_info['file_count']} files indexed")
    else:
        info("Index:   not built (run: clockwork index)")

    # Mode
    info(f"Mode:    {settings.mode} / validation: {settings.validation}")

    # Recent changes
    recent = ctx_info.get("recent_changes", [])
    if recent:
        info("")
        info("Recent changes:")
        for change in recent[:3]:
            desc = change.get("description", "")[:60]
            ts = _format_age(change.get("timestamp", ""))
            info(f"  • {desc} ({ts})")

    # Active issues
    issues = _check_issues(cw_dir, ctx_info, graph_info, index_info)
    if issues:
        info("")
        for issue in issues:
            warn(issue)
    else:
        info("")
        info("Active issues: none")

    rule()
    info("Next: clockwork verify  |  clockwork handoff")


# ── Data collectors ───────────────────────────────────────────────────────

def _get_git_info(root: Path) -> dict:
    try:
        from clockwork.scanner.git_diff import GitDiffScanner
        scanner = GitDiffScanner(root)
        if not scanner.is_git_repo():
            return {"is_git_repo": False}
        sha, _ = scanner.last_commit()
        return {
            "is_git_repo": True,
            "branch": scanner.current_branch(),
            "commit": sha[:8] if sha else "",
            "is_dirty": False,
            "uncommitted": 0,
            "untracked": 0,
        }
    except Exception:
        return {"is_git_repo": False}


def _get_context_info(cw_dir: Path) -> dict:
    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        return {"exists": False}
    try:
        data = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
        return {
            "exists": True,
            "project_name": data.get("project_name", ""),
            "last_updated": data.get("last_updated", ""),
            "task_count": len(data.get("current_tasks", [])),
            "total_files": data.get("total_files", 0),
            "primary_language": data.get("primary_language", ""),
            "frameworks": data.get("frameworks", []),
            "recent_changes": data.get("recent_changes", [])[-5:],
        }
    except Exception:
        return {"exists": True, "error": "parse_failed"}


def _get_graph_info(cw_dir: Path) -> dict:
    db_path = cw_dir / "knowledge_graph.db"
    if not db_path.exists():
        return {"exists": False}
    try:
        from clockwork.graph.storage import GraphStorage
        from clockwork.graph.queries import GraphQueryEngine
        storage = GraphStorage(db_path)
        storage.open()
        engine = GraphQueryEngine(storage)
        stats = engine.stats()
        storage.close()
        built_at = ""
        try:
            built_at = datetime.fromtimestamp(
                db_path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        except Exception:
            pass
        return {
            "exists": True,
            "nodes": stats.get("total_nodes", 0),
            "edges": stats.get("total_edges", 0),
            "built_at": built_at,
        }
    except Exception:
        return {"exists": True, "nodes": 0, "edges": 0, "built_at": ""}


def _get_index_info(cw_dir: Path) -> dict:
    index_path = cw_dir / "live_index.db"
    if not index_path.exists():
        return {"exists": False}
    try:
        file_count = 0
        try:
            import sqlite3
            conn = sqlite3.connect(str(index_path))
            row = conn.execute("SELECT COUNT(*) FROM entries").fetchone()
            file_count = row[0] if row else 0
            conn.close()
        except Exception:
            pass
        return {"exists": True, "file_count": file_count}
    except Exception:
        return {"exists": True, "file_count": 0}


def _check_issues(cw_dir: Path, ctx: dict, graph: dict, index: dict) -> list[str]:
    """Check for potential issues to display."""
    issues: list[str] = []

    if not (cw_dir / "repo_map.json").exists():
        issues.append("repo_map.json missing — run: clockwork scan")

    if not graph.get("exists"):
        issues.append("Knowledge graph not built — run: clockwork graph build")

    last_updated = ctx.get("last_updated", "")
    if last_updated:
        try:
            updated_dt = datetime.fromisoformat(last_updated)
            age_hours = (datetime.now(timezone.utc) - updated_dt).total_seconds() / 3600
            if age_hours > 24:
                issues.append(f"Context is {age_hours:.0f}h old — run: clockwork update")
        except Exception:
            pass

    return issues


def _format_age(iso_timestamp: str) -> str:
    """Format an ISO timestamp as a human-readable age string."""
    if not iso_timestamp:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        seconds = delta.total_seconds()
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}h ago"
        else:
            return f"{int(seconds / 86400)}d ago"
    except Exception:
        return "unknown"
