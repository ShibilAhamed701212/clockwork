"""
clockwork/cli/app.py
"""
from __future__ import annotations
import typer
from clockwork.cli.commands.init import cmd_init
from clockwork.cli.commands.scan import cmd_scan
from clockwork.cli.commands.update import cmd_update
from clockwork.cli.commands.verify import cmd_verify
from clockwork.cli.commands.handoff import cmd_handoff
from clockwork.cli.commands.index import cmd_index, cmd_repair, cmd_watch
from clockwork.cli.commands.status import cmd_status
from clockwork.cli.commands.recover import cmd_recover
from clockwork.cli.commands.graph import graph_app
from clockwork.cli.commands.agent import agent_app, task_app
from clockwork.cli.commands.security import security_app
from clockwork.cli.commands.registry import registry_app, plugin_app
from clockwork.packaging.cli_commands import cmd_pack, cmd_load
from clockwork.cli.commands.hooks import hooks_app
from clockwork.cli.commands.generate import cmd_generate
from clockwork.cli.commands.diff import cmd_diff
from clockwork.cli.commands.ask import cmd_ask
from clockwork.cli.commands.doctor import cmd_doctor
from clockwork.cli.commands.mcp import mcp_app
from clockwork.cli.commands.worktree import worktree_app

app = typer.Typer(
    name="clockwork",
    help="Clockwork - local-first repository intelligence and agent coordination.",
    add_completion=False,
    no_args_is_help=True,
)

app.command("init",     help="Initialise Clockwork in a repository.")(cmd_init)
app.command("scan",     help="Analyse repository structure.")(cmd_scan)
app.command("update",   help="Merge scan results into context.yaml.")(cmd_update)
app.command("verify",   help="Verify repository integrity.")(cmd_verify)
app.command("handoff",  help="Generate agent handoff data.")(cmd_handoff)
app.command("pack",     help="Package project intelligence.")(cmd_pack)
app.command("load",     help="Load a .clockwork package.")(cmd_load)
app.command("index",    help="Build/refresh the Live Context Index.")(cmd_index)
app.command("repair",   help="Wipe and rebuild the index + graph.")(cmd_repair)
app.command("watch",    help="Start real-time repository monitoring.")(cmd_watch)
app.command("status",   help="Show runtime state, validation, and recovery health.")(cmd_status)
app.command("recover",  help="Trigger the recovery engine for a failure scenario.")(cmd_recover)
app.command("generate", help="Generate IDE context files (CLAUDE.md, .cursorrules, etc.).")(cmd_generate)
app.command("diff",     help="Show changed files since last scan with impact analysis.")(cmd_diff)
app.command("ask",      help="Ask natural language questions about the codebase.")(cmd_ask)
app.command("doctor",   help="Diagnose Clockwork installation and project health.")(cmd_doctor)
app.add_typer(graph_app,    name="graph")
app.add_typer(agent_app,    name="agent")
app.add_typer(task_app,     name="task")
app.add_typer(security_app, name="security")
app.add_typer(registry_app, name="registry")
app.add_typer(plugin_app,   name="plugin")
app.add_typer(hooks_app,    name="hooks")
app.add_typer(mcp_app,      name="mcp")
app.add_typer(worktree_app, name="worktree")

def main() -> None:
    app()

if __name__ == "__main__":
    main()
