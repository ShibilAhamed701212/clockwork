"""
clockwork mcp — start and configure the MCP server.
"""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional
import typer
from clockwork.cli.output import header, success, info, warn, error, rule

mcp_app = typer.Typer(name="mcp",
    help="MCP server for Claude Code / Cursor integration.",
    no_args_is_help=True)

CLAUDE_CONFIG_PATHS = [
    Path.home() / ".claude" / "claude_desktop_config.json",
    Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    Path.home() / ".config" / "claude" / "claude_desktop_config.json",
]

@mcp_app.command("start")
def mcp_start(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r"),
    port: Optional[int] = typer.Option(None, "--port", "-p",
                                        help="HTTP port (stdio if omitted)"),
) -> None:
    """Start the Clockwork MCP server."""
    root = str((repo or Path.cwd()).resolve())
    args = [sys.executable, "-m", "clockwork.mcp_server",
            "--repo", root]
    if port:
        args += ["--http", str(port)]
    info(f"Starting Clockwork MCP server (repo={root})")
    subprocess.run(args)

@mcp_app.command("install-claude")
def mcp_install_claude(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Install Clockwork into Claude Code / Claude Desktop config."""
    root = str((repo or Path.cwd()).resolve())
    config_path = None
    for p in CLAUDE_CONFIG_PATHS:
        if p.parent.exists():
            config_path = p
            break
    if not config_path:
        error("Claude config directory not found.")
        info("Manually add to your Claude Desktop config:")
        _print_manual_config(root)
        return

    header("Claude MCP Configuration")
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            config = {}

    config.setdefault("mcpServers", {})
    config["mcpServers"]["clockwork"] = {
        "command": "clockwork-mcp",
        "args": ["--repo", root],
    }
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    success(f"Clockwork MCP registered in {config_path}")
    info("Restart Claude Desktop to activate.")
    rule()
    info("Tools available to Claude:")
    tools = ["get_project_context", "query_graph", "check_file_safety",
             "get_handoff_brief", "run_verify", "search_codebase"]
    for t in tools:
        info(f"  - {t}")

@mcp_app.command("install-cursor")
def mcp_install_cursor(
    repo: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Install Clockwork into Cursor's MCP config."""
    root = str((repo or Path.cwd()).resolve())
    cursor_config = Path.cwd() / ".cursor" / "mcp.json"
    cursor_config.parent.mkdir(exist_ok=True)
    config = {}
    if cursor_config.exists():
        try:
            config = json.loads(cursor_config.read_text(encoding="utf-8"))
        except Exception:
            config = {}
    config.setdefault("mcpServers", {})
    config["mcpServers"]["clockwork"] = {
        "command": "clockwork-mcp",
        "args": ["--repo", root],
    }
    cursor_config.write_text(json.dumps(config, indent=2), encoding="utf-8")
    success(f"Clockwork MCP registered in {cursor_config}")

def _print_manual_config(root: str) -> None:
    config = {"mcpServers": {"clockwork": {
        "command": "clockwork-mcp",
        "args": ["--repo", root],
    }}}
    info(json.dumps(config, indent=2))
