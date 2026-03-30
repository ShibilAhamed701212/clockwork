"""
clockwork/cli/commands/handoff.py
-----------------------------------
`clockwork handoff` — generate agent handoff data.

Produces:
  .clockwork/handoff/handoff.json
  .clockwork/handoff/next_agent_brief.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import header, success, info, error, step, rule


def cmd_handoff(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    note: Optional[str] = typer.Option(
        None, "--note", "-n",
        help="Optional human note to include in the handoff brief.",
    ),
) -> None:
    """
    Generate agent handoff data from current project context.

    Writes handoff.json and next_agent_brief.md into .clockwork/handoff/.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Handoff")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        error("context.yaml not found.\nRun:  clockwork init && clockwork scan && clockwork update")
        raise typer.Exit(code=1)

    try:
        context: dict = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        error(f"Cannot read context.yaml: {exc}")
        raise typer.Exit(code=1)

    handoff_dir = cw_dir / "handoff"
    handoff_dir.mkdir(exist_ok=True)

    step("Building handoff payload...")
    handoff = _build_handoff(context, note=note)

    step("Writing handoff.json...")
    handoff_json_path = handoff_dir / "handoff.json"
    handoff_json_path.write_text(
        json.dumps(handoff, indent=2, default=str),
        encoding="utf-8",
    )

    step("Writing next_agent_brief.md...")
    brief_path = handoff_dir / "next_agent_brief.md"
    brief_path.write_text(_build_brief(handoff), encoding="utf-8")

    # Record in agent history
    _append_agent_history(cw_dir, handoff)

    rule()
    success("Handoff data generated")
    info(f"  JSON  : .clockwork/handoff/handoff.json")
    info(f"  Brief : .clockwork/handoff/next_agent_brief.md")


def _build_handoff(context: dict, note: Optional[str]) -> dict:
    """Construct the handoff payload from project context."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_name": context.get("project_name", "unknown"),
        "clockwork_version": context.get("clockwork_version", "0.1"),
        "architecture_summary": context.get("architecture_overview", ""),
        "primary_language": context.get("primary_language", ""),
        "frameworks": context.get("frameworks", []),
        "entry_points": context.get("entry_points", []),
        "current_tasks": context.get("current_tasks", []),
        "recent_changes": context.get("recent_changes", []),
        "total_files": context.get("total_files", 0),
        "languages": context.get("languages", {}),
        "handoff_note": note or "",
        "next_steps": context.get("current_tasks", []),
    }


def _build_brief(handoff: dict) -> str:
    """Render a Markdown handoff brief for the next agent."""
    tasks = handoff.get("current_tasks") or ["(none recorded)"]
    frameworks = handoff.get("frameworks") or ["(none detected)"]
    entry_points = handoff.get("entry_points") or ["(none detected)"]

    task_list = "\n".join(f"- {t}" for t in tasks)
    fw_list = "\n".join(f"- {f}" for f in frameworks)
    ep_list = "\n".join(f"- {e}" for e in entry_points)
    note_section = (
        f"\n## Handoff Note\n\n{handoff['handoff_note']}\n"
        if handoff.get("handoff_note")
        else ""
    )

    return f"""# Clockwork Agent Handoff Brief

**Project:** {handoff['project_name']}
**Generated:** {handoff['generated_at']}
**Clockwork Version:** {handoff['clockwork_version']}

---

## Architecture Summary

{handoff.get('architecture_summary') or '(not yet recorded — update context.yaml)'}

---

## Technical Stack

**Primary Language:** {handoff['primary_language'] or '(unknown)'}

**Frameworks:**
{fw_list}

**Entry Points:**
{ep_list}

---

## Current Tasks

{task_list}

---

## Recent Changes

{chr(10).join(f'- {c}' for c in handoff.get('recent_changes') or ['(none recorded)'])}

---
{note_section}
## Instructions for Next Agent

1. Read `.clockwork/context.yaml` for full project context.
2. Read `.clockwork/rules.md` before making any changes.
3. Run `clockwork verify` before committing.
4. Run `clockwork update` after significant changes.
5. Run `clockwork handoff` when passing work to another agent.
"""


def _append_agent_history(cw_dir: Path, handoff: dict) -> None:
    """Append a summary entry to agent_history.json."""
    history_path = cw_dir / "agent_history.json"
    try:
        history: list = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = []

    history.append({
        "event": "handoff_generated",
        "timestamp": handoff["generated_at"],
        "project": handoff["project_name"],
        "tasks": handoff["current_tasks"],
    })

    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
