"""Clockwork CLI � main entry point."""
import typer
from clockwork.cli import cmd_init, cmd_scan, cmd_verify, cmd_update
from clockwork.cli import cmd_handoff, cmd_pack, cmd_load, cmd_graph
from clockwork.cli.cmd_plugin import plugin_app

app = typer.Typer(name="clockwork", help="Local-first repository intelligence system.", no_args_is_help=True)
app.command("init")(cmd_init.run)
app.command("scan")(cmd_scan.run)
app.command("verify")(cmd_verify.run)
app.command("update")(cmd_update.run)
app.add_typer(cmd_handoff.app, name="handoff")
app.command("pack")(cmd_pack.run)
app.command("load")(cmd_load.run)
app.command("graph")(cmd_graph.run)
app.add_typer(plugin_app, name="plugin")

if __name__ == "__main__":
    app()
