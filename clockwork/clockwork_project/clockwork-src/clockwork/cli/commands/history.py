"""
clockwork/cli/commands/history.py
---------------------------------
`clockwork history` — view unified activity history.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import typer

from clockwork.cli.output import error, header, info, json_output, warn


def _read_activity_history(path: Path) -> tuple[list[dict[str, Any]], int]:
    """Read JSONL history entries. Returns (entries, malformed_line_count)."""
    if not path.exists():
        return [], 0

    entries: list[dict[str, Any]] = []
    malformed = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if isinstance(item, dict):
            entries.append(item)
        else:
            malformed += 1

    return entries, malformed


def cmd_history(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    limit: int = typer.Option(20, "--limit", "-n", min=1, help="Show last N entries."),
    actor: Optional[str] = typer.Option(None, "--actor", help="Filter by actor."),
    action: Optional[str] = typer.Option(None, "--action", help="Filter by action."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    """Show `.clockwork/logs/activity_history.jsonl` entries."""
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not cw_dir.is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    history_path = cw_dir / "logs" / "activity_history.jsonl"
    entries, malformed = _read_activity_history(history_path)

    if actor:
        entries = [e for e in entries if e.get("actor") == actor]
    if action:
        entries = [e for e in entries if e.get("action") == action]

    entries = entries[-limit:]

    if as_json:
        json_output({
            "count": len(entries),
            "malformed": malformed,
            "entries": entries,
        })
        return

    header("Clockwork History")
    if not entries:
        warn("No activity history found yet.")
        return

    if malformed:
        warn(f"Skipped {malformed} malformed history line(s).")

    for event in entries:
        ts = str(event.get("timestamp", "")).replace("T", " ").replace("+00:00", "Z")
        actor_name = event.get("actor", "unknown")
        action_name = event.get("action", "")
        status = event.get("status", "")
        info(f"{ts} | {actor_name:<12} | {action_name:<20} | {status}")

