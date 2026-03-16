"""
clockwork/cli/commands/registry.py
------------------------------------
CLI commands for the Registry & Ecosystem subsystem (spec §14).

Commands:
    clockwork registry search [query]
    clockwork registry info <name>
    clockwork registry refresh
    clockwork registry status

    clockwork plugin install <name>
    clockwork plugin list
    clockwork plugin update <name>
    clockwork plugin remove <name>
    clockwork plugin publish <path>
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── Typer sub-apps ─────────────────────────────────────────────────────────

registry_app = typer.Typer(
    name="registry",
    help="Search and manage the Clockwork plugin registry.",
    no_args_is_help=True,
)

plugin_app = typer.Typer(
    name="plugin",
    help="Install, update, and manage plugins.",
    no_args_is_help=True,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _engine(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw   = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.registry import RegistryEngine
    return RegistryEngine(root)


def _print_entry(e) -> None:
    trusted = " [trusted]" if e.trusted else ""
    info(f"  {e.name:<28} v{e.version:<8} {e.artifact_type}{trusted}")
    if e.description:
        info(f"    {e.description}")
    if e.tags:
        info(f"    tags: {', '.join(e.tags)}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork registry …
# ══════════════════════════════════════════════════════════════════════════

@registry_app.command("search")
def registry_search(
    query:         str            = typer.Argument("", help="Search term (empty = list all)."),
    artifact_type: str            = typer.Option("", "--type", "-t",
                                       help="Filter by type: plugin, brain, package."),
    repo_root:     Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:       bool           = typer.Option(False, "--json"),
) -> None:
    """Search the registry for plugins, brains, and packages."""
    reg     = _engine(repo_root)
    results = reg.search(query, artifact_type)

    if as_json:
        json_output([e.to_dict() for e in results])
        return

    header(f"Registry Search: '{query}'" if query else "Registry — All Entries")
    if not results:
        warn("No entries found. Try a different search term.")
        return

    info(f"  {len(results)} result(s):\n")
    for e in sorted(results, key=lambda x: (x.artifact_type, x.name)):
        _print_entry(e)
        rule()


@registry_app.command("info")
def registry_info(
    name:      str            = typer.Argument(..., help="Plugin or artifact name."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show detailed info about a registry entry."""
    reg   = _engine(repo_root)
    entry = reg.get(name)

    if entry is None:
        error(f"'{name}' not found in registry.")
        raise typer.Exit(code=1)

    if as_json:
        json_output(entry.to_dict())
        return

    header(f"Registry: {entry.name}")
    info(f"  Name        : {entry.name}")
    info(f"  Version     : {entry.version}")
    info(f"  Type        : {entry.artifact_type}")
    info(f"  Author      : {entry.author or '(unknown)'}")
    info(f"  Description : {entry.description or '(none)'}")
    info(f"  Requires    : clockwork {entry.requires_clockwork}")
    info(f"  Permissions : {', '.join(entry.permissions) or '(none)'}")
    info(f"  Tags        : {', '.join(entry.tags) or '(none)'}")
    info(f"  Trusted     : {'yes' if entry.trusted else 'no'}")
    if entry.checksum:
        info(f"  Checksum    : {entry.checksum[:16]}...")


@registry_app.command("refresh")
def registry_refresh(
    url:       str            = typer.Option("", "--url", "-u",
                                    help="Registry server URL."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Refresh the local registry cache from the remote server."""
    reg  = _engine(repo_root)
    step("Refreshing registry cache...")
    ok, msg = reg.refresh(url)
    if ok:
        success(msg)
    else:
        warn(msg)


@registry_app.command("status")
def registry_status(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show registry cache status."""
    reg  = _engine(repo_root)
    data = reg.cache_info()

    if as_json:
        json_output(data)
        return

    header("Registry Status")
    info(f"  Cached entries   : {data['entries']}")
    info(f"  Installed plugins: {data['installed']}")
    info(f"  Registry URL     : {data['registry_url'] or '(not set)'}")
    stale = "yes — run: clockwork registry refresh" if data["is_stale"] else "no"
    info(f"  Cache stale      : {stale}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork plugin …
# ══════════════════════════════════════════════════════════════════════════

@plugin_app.command("install")
def plugin_install(
    name:      str            = typer.Argument(..., help="Plugin name to install."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Install a plugin from the registry."""
    reg = _engine(repo_root)
    step(f"Installing '{name}'...")
    ok, msg = reg.install(name)
    if ok:
        success(msg)
        info("  Run:  clockwork plugin list  to see installed plugins.")
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("list")
def plugin_list(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """List installed plugins."""
    reg       = _engine(repo_root)
    installed = reg.list_installed()

    if as_json:
        json_output([p.to_dict() for p in installed])
        return

    header("Installed Plugins")
    if not installed:
        info("No plugins installed.")
        info("  Discover plugins:  clockwork registry search")
        info("  Install a plugin:  clockwork plugin install <name>")
        return

    for p in installed:
        status = "enabled" if p.enabled else "disabled"
        info(f"  {p.name:<28} v{p.version:<8} [{status}]")
        info(f"    {p.install_path}")


@plugin_app.command("update")
def plugin_update(
    name:      str            = typer.Argument(..., help="Plugin name to update."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Update an installed plugin to its latest version."""
    reg = _engine(repo_root)
    step(f"Updating '{name}'...")
    ok, msg = reg.update(name)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("remove")
def plugin_remove(
    name:      str            = typer.Argument(..., help="Plugin name to remove."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Remove an installed plugin."""
    reg = _engine(repo_root)
    ok, msg = reg.remove(name)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("publish")
def plugin_publish(
    plugin_path: Path          = typer.Argument(
                                     Path("."),
                                     help="Path to plugin directory (default: current dir)."),
    repo_root:   Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Publish a plugin to the registry."""
    reg = _engine(repo_root)
    step(f"Publishing '{plugin_path.name}'...")
    ok, msg = reg.publish(plugin_path)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)

