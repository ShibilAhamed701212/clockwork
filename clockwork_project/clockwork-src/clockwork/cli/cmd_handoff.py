"""
Clockwork CLI - handoff command
clockwork/cli/cmd_handoff.py

Register in main Typer app:
    from clockwork.cli.cmd_handoff import app as handoff_app
    main_app.add_typer(handoff_app, name="handoff")
"""

from __future__ import annotations

from pathlib import Path

import typer

from clockwork.handoff import HandoffEngine

app = typer.Typer(help="Generate an agent handoff package.")


@app.callback(invoke_without_command=True)
def handoff(
    agent: str = typer.Option(
        "unknown",
        "--agent", "-a",
        help="Name of the target agent receiving the handoff (e.g. Claude, GPT-4).",
    ),
    repo: Path = typer.Option(
        Path("."),
        "--repo", "-r",
        help="Path to the repository root (default: current directory).",
        exists=False,
    ),
) -> None:
    """
    Generate a structured handoff for the next AI agent.

    Produces:
      .clockwork/handoff/next_agent_brief.md
      .clockwork/handoff/handoff.json
    """
    typer.echo("Generating agent handoff...")

    engine = HandoffEngine(repo_root=repo)
    success, message = engine.run(target_agent=agent)

    if success:
        typer.secho(message, fg=typer.colors.GREEN)
    else:
        typer.secho(message, fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)
def run() -> None:
    """Wrapper so main.py can register this as a command."""
    handoff()
