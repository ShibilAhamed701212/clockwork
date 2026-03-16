"""
clockwork/cli/app.py
----------------------
Main Typer application for the Clockwork CLI.

Registers all commands:
    clockwork init
    clockwork scan
    clockwork verify
    clockwork update
    clockwork handoff
    clockwork pack
    clockwork load
    clockwork graph
"""

from __future__ import annotations

import typer

from clockwork.cli.commands.init import cmd_init
from clockwork.cli.commands.scan import cmd_scan
from clockwork.cli.commands.update import cmd_update
from clockwork.cli.commands.verify import cmd_verify
from clockwork.cli.commands.handoff import cmd_handoff
from clockwork.cli.commands.graph import cmd_graph
from clockwork.packaging.cli_commands import cmd_pack, cmd_load

# ── App definition ─────────────────────────────────────────────────────────

app = typer.Typer(
    name="clockwork",
    help=(
        "Clockwork — local-first repository intelligence and agent coordination.\n\n"
        "Maintains persistent project context so multiple AI agents can understand\n"
        "and continue development without losing state."
    ),
    add_completion=False,
    no_args_is_help=True,
)

# ── Command registration ───────────────────────────────────────────────────

app.command("init",    help="Initialise Clockwork in a repository.")(cmd_init)
app.command("scan",    help="Analyse repository structure → repo_map.json.")(cmd_scan)
app.command("update",  help="Merge scan results into context.yaml.")(cmd_update)
app.command("verify",  help="Verify repository integrity via Rule Engine.")(cmd_verify)
app.command("handoff", help="Generate agent handoff data.")(cmd_handoff)
app.command("pack",    help="Package project intelligence into .clockwork archive.")(cmd_pack)
app.command("load",    help="Load a .clockwork package into the repository.")(cmd_load)
app.command("graph",   help="Generate repository knowledge graph (SQLite).")(cmd_graph)


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point used by pyproject.toml [project.scripts]."""
    app()


if __name__ == "__main__":
    main()
