"""
clockwork/cli/commands/registry.py
------------------------------------
CLI commands for the Registry & Ecosystem subsystem (spec 14).

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

import sys
from pathlib import Path

# ── helpers ────────────────────────────────────────────────────────────────

def _engine(repo_root=None):
    root = (repo_root or Path.cwd()).resolve()
    cw   = root / ".clockwork"
    if not cw.is_dir():
        print("[ERROR] Clockwork not initialised. Run: clockwork init")
        sys.exit(1)
    from registry.registry_engine import RegistryEngine
    return RegistryEngine(root)


def _print_entry(e) -> None:
    trusted = " [trusted]" if e.trusted else ""
    print("  " + e.name.ljust(28) + " v" + e.version.ljust(8) + " " + e.artifact_type + trusted)
    if e.description:
        print("    " + e.description)
    if e.tags:
        print("    tags: " + ", ".join(e.tags))


# ══════════════════════════════════════════════════════════════════════════
# clockwork registry …
# ══════════════════════════════════════════════════════════════════════════

def registry_search(query: str = "", artifact_type: str = "", repo_root=None) -> None:
    """Search the registry for plugins, brains, and packages."""
    reg     = _engine(repo_root)
    results = reg.search(query, artifact_type)

    print("=" * 60)
    print(" Registry Search: '" + query + "'" if query else " Registry — All Entries")
    print("=" * 60)
    if not results:
        print("[WARN] No entries found. Try a different search term.")
        return

    print("  " + str(len(results)) + " result(s):\n")
    for e in sorted(results, key=lambda x: (x.artifact_type, x.name)):
        _print_entry(e)
        print("-" * 60)


def registry_info(name: str, repo_root=None) -> None:
    """Show detailed info about a registry entry."""
    reg   = _engine(repo_root)
    entry = reg.get(name)

    if entry is None:
        print("[ERROR] '" + name + "' not found in registry.")
        sys.exit(1)

    print("=" * 60)
    print(" Registry: " + entry.name)
    print("=" * 60)
    print("  Name        : " + entry.name)
    print("  Version     : " + entry.version)
    print("  Type        : " + entry.artifact_type)
    print("  Author      : " + (entry.author or "(unknown)"))
    print("  Description : " + (entry.description or "(none)"))
    print("  Requires    : clockwork " + entry.requires_clockwork)
    print("  Permissions : " + (", ".join(entry.permissions) or "(none)"))
    print("  Tags        : " + (", ".join(entry.tags) or "(none)"))
    print("  Trusted     : " + ("yes" if entry.trusted else "no"))
    if entry.checksum:
        print("  Checksum    : " + entry.checksum[:16] + "...")


def registry_refresh(url: str = "", repo_root=None) -> None:
    """Refresh the local registry cache from the remote server."""
    reg = _engine(repo_root)
    print("[...] Refreshing registry cache...")
    ok, msg = reg.refresh(url)
    if ok:
        print("[OK] " + msg)
    else:
        print("[WARN] " + msg)


def registry_status(repo_root=None) -> None:
    """Show registry cache status."""
    reg  = _engine(repo_root)
    data = reg.cache_info()

    print("=" * 60)
    print(" Registry Status")
    print("=" * 60)
    print("  Cached entries   : " + str(data["entries"]))
    print("  Installed plugins: " + str(data["installed"]))
    print("  Registry URL     : " + (data["registry_url"] or "(not set)"))
    stale = "yes — run: clockwork registry refresh" if data["is_stale"] else "no"
    print("  Cache stale      : " + stale)


# ══════════════════════════════════════════════════════════════════════════
# clockwork plugin …
# ══════════════════════════════════════════════════════════════════════════

def plugin_install(name: str, repo_root=None) -> None:
    """Install a plugin from the registry."""
    reg = _engine(repo_root)
    print("[...] Installing '" + name + "'...")
    ok, msg = reg.install(name)
    if ok:
        print("[OK] " + msg)
        print("  Run:  clockwork plugin list  to see installed plugins.")
    else:
        print("[ERROR] " + msg)
        sys.exit(1)


def plugin_list(repo_root=None) -> None:
    """List installed plugins."""
    reg       = _engine(repo_root)
    installed = reg.list_installed()

    print("=" * 60)
    print(" Installed Plugins")
    print("=" * 60)
    if not installed:
        print("  No plugins installed.")
        print("  Discover plugins:  clockwork registry search")
        print("  Install a plugin:  clockwork plugin install <name>")
        return

    for p in installed:
        status = "enabled" if p.enabled else "disabled"
        print("  " + p.name.ljust(28) + " v" + p.version.ljust(8) + " [" + status + "]")
        print("    " + p.install_path)


def plugin_update(name: str, repo_root=None) -> None:
    """Update an installed plugin to its latest version."""
    reg = _engine(repo_root)
    print("[...] Updating '" + name + "'...")
    ok, msg = reg.update(name)
    if ok:
        print("[OK] " + msg)
    else:
        print("[ERROR] " + msg)
        sys.exit(1)


def plugin_remove(name: str, repo_root=None) -> None:
    """Remove an installed plugin."""
    reg = _engine(repo_root)
    print("[...] Removing '" + name + "'...")
    ok, msg = reg.remove(name)
    if ok:
        print("[OK] " + msg)
    else:
        print("[ERROR] " + msg)
        sys.exit(1)


def plugin_publish(plugin_path: str = ".", repo_root=None) -> None:
    """Publish a plugin to the registry."""
    reg        = _engine(repo_root)
    plugin_dir = Path(plugin_path).resolve()
    print("[...] Publishing plugin at " + str(plugin_dir) + "...")
    ok, msg = reg.publish(plugin_dir)
    if ok:
        print("[OK] " + msg)
    else:
        print("[ERROR] " + msg)
        sys.exit(1)