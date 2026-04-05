"""
clockwork/cli/app.py
"""

from __future__ import annotations
import typer
from .commands.init import cmd_init
from .commands.ci_run import cmd_ci_run
from .commands.scan import cmd_scan
from .commands.update import cmd_update
from .commands.verify import cmd_verify
from .commands.handoff import cmd_handoff
from .commands.index import cmd_index, cmd_repair, cmd_watch
from .commands.status import cmd_status
from .commands.recover import cmd_recover
from .commands.graph import graph_app
from .commands.agent import agent_app, task_app
from .commands.security import security_app
from .commands.registry import registry_app, plugin_app
from ..packaging.cli_commands import cmd_pack, cmd_load
from .commands.hooks import hooks_app
from .commands.generate import cmd_generate
from .commands.diff import cmd_diff
from .commands.ask import cmd_ask
from .commands.doctor import cmd_doctor
from .commands.mcp import mcp_app
from .commands.worktree import worktree_app
from .commands.git_ops import sync_app
from .commands.history import cmd_history
from .commands.validate import validate_app
from .commands.session import session_app

app = typer.Typer(
    name="clockwork",
    help="Clockwork - local-first repository intelligence and agent coordination.",
    add_completion=False,
    no_args_is_help=True,
)

app.command("init", help="Initialise Clockwork in a repository.")(cmd_init)
app.command("ci-run", help="Run CI/CD pipeline with auto-retry.")(cmd_ci_run)
app.command("scan", help="Analyse repository structure.")(cmd_scan)
app.command("update", help="Merge scan results into context.yaml.")(cmd_update)
app.command("verify", help="Verify repository integrity.")(cmd_verify)
app.command("handoff", help="Generate agent handoff data.")(cmd_handoff)
app.command("pack", help="Package project intelligence.")(cmd_pack)
app.command("load", help="Load a .clockwork package.")(cmd_load)
app.command("index", help="Build/refresh the Live Context Index.")(cmd_index)
app.command("repair", help="Wipe and rebuild the index + graph.")(cmd_repair)
app.command("watch", help="Start real-time repository monitoring.")(cmd_watch)
app.command("status", help="Show runtime state, validation, and recovery health.")(
    cmd_status
)
app.command("recover", help="Trigger the recovery engine for a failure scenario.")(
    cmd_recover
)
app.command(
    "generate",
    help="Generate AI context files (agent-context.md, agent-rules.md, etc.).",
)(cmd_generate)
app.command("diff", help="Show changed files since last scan with impact analysis.")(
    cmd_diff
)
app.command("ask", help="Ask natural language questions about the codebase.")(cmd_ask)
app.command("doctor", help="Diagnose Clockwork installation and project health.")(
    cmd_doctor
)
app.command("history", help="Show agent/tool activity history from .clockwork logs.")(
    cmd_history
)
app.add_typer(graph_app, name="graph")
app.add_typer(agent_app, name="agent")
app.add_typer(task_app, name="task")
app.add_typer(security_app, name="security")
app.add_typer(registry_app, name="registry")
app.add_typer(plugin_app, name="plugin")
app.add_typer(hooks_app, name="hooks")
app.add_typer(mcp_app, name="mcp")
app.add_typer(worktree_app, name="worktree")
app.add_typer(sync_app, name="sync")
app.add_typer(validate_app, name="validate")
app.add_typer(session_app, name="session")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
