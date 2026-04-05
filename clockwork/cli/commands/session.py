"""
clockwork/cli/commands/session.py
---------------------------------
CLI commands for session tracking.

Commands:
    clockwork session show   — show current session info
    clockwork session log    — log an event
    clockwork session stats  — show session statistics
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header,
    success,
    info,
    warn,
    error,
    step,
    rule,
    json_output,
)
from clockwork.state.session_tracker import SessionTracker

session_app = typer.Typer(
    name="session",
    help="Session tracking and management.",
    no_args_is_help=True,
)


def _get_tracker(repo_root: Path) -> SessionTracker:
    session_id = f"cli-{int(time.time())}"
    return SessionTracker(session_id, repo_root)


@session_app.command("show")
def session_show(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show current session information."""
    root = (repo_root or Path.cwd()).resolve()

    if not as_json:
        header("Session Info")

    tracker = _get_tracker(root)
    summary = tracker.summary()

    if as_json:
        json_output(summary)
    else:
        info(f"Session ID: {summary['session_id']}")
        info(f"Duration: {summary['duration_s']}s")
        info(f"Events: {summary['events']}")


@session_app.command("log")
def session_log(
    event: str = typer.Argument(..., help="Event type to log"),
    data: Optional[str] = typer.Option(None, "--data", "-d", help="JSON data to log"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Log an event to the session."""
    import json

    root = (repo_root or Path.cwd()).resolve()
    tracker = _get_tracker(root)

    payload = {}
    if data:
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            warn("Invalid JSON in --data, ignoring")

    tracker.log(event, payload)
    success(f"Logged event: {event}")


@session_app.command("stats")
def session_stats(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show session statistics from sessions.json."""
    import json

    root = (repo_root or Path.cwd()).resolve()
    sessions_file = root / ".clockwork" / "sessions.json"

    if not sessions_file.exists():
        info("No sessions recorded yet.")
        return

    if not as_json:
        header("Session Statistics")

    try:
        sessions = json.loads(sessions_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        error("Could not parse sessions.json")
        return

    if as_json:
        json_output({"total_sessions": len(sessions)})
    else:
        info(f"Total session entries: {len(sessions)}")
        if sessions:
            last = sessions[-1]
            info(f"Last session: {last.get('session_id', 'unknown')}")
