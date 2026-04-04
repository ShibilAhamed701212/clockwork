"""
clockwork/cli/commands/recover.py
----------------------------------
`clockwork recover` - trigger and inspect recovery operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import error, header, info, rule, success, warn
from clockwork.config.settings import load_settings
from clockwork.recovery.recovery_engine import RecoveryEngine
from clockwork.state.state_manager import StateManager


def cmd_recover(
    failure_type: str = typer.Option(
        "invalid_context", "--type", "-t", help="Failure type to handle."
    ),
    details: str = typer.Option("manual-trigger", "--details", help="Failure details."),
    severity: str = typer.Option("medium", "--severity", help="Severity: low|medium|high"),
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r", help="Root directory of the repository."
    ),
) -> None:
    root = (repo_root or Path.cwd()).resolve()
    if not (root / ".clockwork").is_dir():
        error("Clockwork not initialised. Run: clockwork init")
        raise typer.Exit(code=1)

    settings = load_settings(root)
    state_manager = StateManager(settings, repo_root=root)
    engine = RecoveryEngine(state=state_manager, repo_root=root)

    header("Clockwork Recover")
    resolved = engine.on_failure(failure_type=failure_type, details=details, severity=severity)
    if resolved:
        success(f"Recovery handled failure type: {failure_type}")
    else:
        warn(f"Recovery could not fully resolve: {failure_type}")

    stats = engine.stats()
    rule()
    info(f"total_failures: {stats['total_failures']}")
    info(f"resolved: {stats['resolved']}")
    info(f"failsafe_active: {stats['failsafe_active']}")

