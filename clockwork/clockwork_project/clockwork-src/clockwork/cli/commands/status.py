"""
clockwork/cli/commands/status.py
---------------------------------
`clockwork status` - show runtime state, recovery health, and validation mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import error, header, info, rule, success
from clockwork.config.settings import load_settings
from clockwork.recovery.recovery_engine import RecoveryEngine
from clockwork.state.state_manager import StateManager


def cmd_status(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository."
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    root = (repo_root or Path.cwd()).resolve()
    if not (root / ".clockwork").is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    settings = load_settings(root)
    state_manager = StateManager(settings, repo_root=root)
    recovery = RecoveryEngine(state=state_manager, repo_root=root)

    payload = {
        "mode": settings.mode,
        "autonomy": settings.autonomy,
        "validation": settings.validation,
        "state": state_manager.snapshot(),
        "recovery": recovery.stats(),
    }

    if as_json:
        import json

        typer.echo(json.dumps(payload, indent=2))
        return

    header("Clockwork Status")
    info(f"mode: {settings.mode}")
    info(f"autonomy: {settings.autonomy}")
    info(f"validation: {settings.validation}")
    info(f"session_id: {payload['state']['session_id']}")
    info(f"failsafe_active: {payload['recovery']['failsafe_active']}")
    rule()
    success("Status collected")

