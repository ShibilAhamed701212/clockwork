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
from clockwork.cli.commands.graph import graph_app
from clockwork.cli.commands.agent import agent_app, task_app
from clockwork.cli.commands.security import security_app
from clockwork.cli.commands.registry import registry_app, plugin_app
from clockwork.packaging.cli_commands import cmd_pack, cmd_load

app = typer.Typer(
    name="clockwork",
    help="Clockwork - local-first repository intelligence and agent coordination.",
    add_completion=False,
    no_args_is_help=True,
)

app.command("init",    help="Initialise Clockwork in a repository.")(cmd_init)
app.command("scan",    help="Analyse repository structure.")(cmd_scan)
app.command("update",  help="Merge scan results into context.yaml.")(cmd_update)
app.command("verify",  help="Verify repository integrity.")(cmd_verify)
app.command("handoff", help="Generate agent handoff data.")(cmd_handoff)
app.command("pack",    help="Package project intelligence.")(cmd_pack)
app.command("load",    help="Load a .clockwork package.")(cmd_load)
app.command("index",   help="Build/refresh the Live Context Index.")(cmd_index)
app.command("repair",  help="Wipe and rebuild the index + graph.")(cmd_repair)
app.command("watch",   help="Start real-time repository monitoring.")(cmd_watch)
app.add_typer(graph_app,    name="graph")
app.add_typer(agent_app,    name="agent")
app.add_typer(task_app,     name="task")
app.add_typer(security_app, name="security")
app.add_typer(registry_app, name="registry")
app.add_typer(plugin_app,   name="plugin")

def main() -> None:
    app()

if __name__ == "__main__":
    main()

