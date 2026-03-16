"""
clockwork/cli/commands/index.py
---------------------------------
CLI commands for the Live Context Index subsystem.

Commands:
    clockwork watch   — start real-time filesystem monitoring
    clockwork index   — build / refresh the index
    clockwork repair  — wipe and rebuild the index from scratch
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── clockwork index ────────────────────────────────────────────────────────

def cmd_index(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """
    Build or refresh the Live Context Index.

    Scans the repository and writes metadata to .clockwork/index.db.
    Skips files whose content has not changed.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Index")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    if not as_json:
        step("Building Live Context Index...")

    try:
        from clockwork.index import LiveContextIndex
        engine = LiveContextIndex(root)
        stats  = engine.build()
    except Exception as exc:
        error(f"Index build failed: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats.to_dict())
        return

    rule()
    success("Live Context Index written to .clockwork/index.db")
    info(f"  Total files   : {stats.total_files}")
    info(f"  Indexed       : {stats.indexed_files}")
    info(f"  Skipped (unchanged) : {stats.skipped_files}")
    info(f"  Elapsed       : {stats.elapsed_ms:.0f} ms")
    info("\nNext step: run  clockwork watch")


# ── clockwork repair ───────────────────────────────────────────────────────

def cmd_repair(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """
    Wipe and rebuild the Live Context Index from scratch.

    Use this if the index becomes corrupted or out of sync.
    Also rebuilds the Knowledge Graph.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Repair")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    if not as_json:
        step("Wiping index.db and rebuilding...")

    try:
        from clockwork.index import LiveContextIndex
        engine = LiveContextIndex(root)
        stats  = engine.repair()
    except Exception as exc:
        error(f"Repair failed: {exc}")
        raise typer.Exit(code=1)

    # also rebuild the knowledge graph if repo_map exists
    graph_rebuilt = False
    if (cw_dir / "repo_map.json").exists():
        if not as_json:
            step("Rebuilding Knowledge Graph...")
        try:
            from clockwork.graph import GraphEngine
            ge = GraphEngine(root)
            ge.build()
            ge.close()
            graph_rebuilt = True
        except Exception as exc:
            warn(f"Graph rebuild skipped: {exc}")

    if as_json:
        result = stats.to_dict()
        result["graph_rebuilt"] = graph_rebuilt
        json_output(result)
        return

    rule()
    success("Repair complete.")
    info(f"  Files indexed  : {stats.indexed_files}")
    info(f"  Elapsed        : {stats.elapsed_ms:.0f} ms")
    if graph_rebuilt:
        info("  Knowledge Graph: rebuilt")
    else:
        info("  Knowledge Graph: skipped (run clockwork graph)")


# ── clockwork watch ────────────────────────────────────────────────────────

def cmd_watch(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    debounce: float = typer.Option(
        0.2, "--debounce", "-d",
        help="Debounce window in seconds (default: 0.2).",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Print each file change event.",
    ),
) -> None:
    """
    Start real-time repository monitoring.

    Watches for file changes and updates the Live Context Index,
    Knowledge Graph, and Context Engine automatically.

    Press Ctrl+C to stop.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Watch")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    # ensure index.db exists before watching
    if not (cw_dir / "index.db").exists():
        step("Building initial index...")
        try:
            from clockwork.index import LiveContextIndex
            engine = LiveContextIndex(root)
            stats  = engine.build()
            info(f"  Initial index: {stats.indexed_files} files in {stats.elapsed_ms:.0f} ms")
        except Exception as exc:
            warn(f"Initial index build failed: {exc}")

    try:
        from clockwork.index import LiveContextIndex
        from clockwork.index.models import ChangeEvent

        change_count = [0]

        def on_change(event: ChangeEvent) -> None:
            change_count[0] += 1
            if verbose:
                info(f"  [{event.event_type}] {event.file_path}")

        engine = LiveContextIndex(root)
        has_watchdog = engine.watch(debounce_s=debounce)

        if has_watchdog:
            success(f"Watching {root}")
            info(f"  Debounce     : {debounce * 1000:.0f} ms")
            info("  Press Ctrl+C to stop.\n")
        else:
            warn("watchdog not installed — real-time watching unavailable.")
            info("Install it with:  pip install watchdog")
            info("Then re-run:      clockwork watch")
            engine.stop()
            raise typer.Exit(code=1)

        # handle Ctrl+C gracefully
        def _shutdown(*_: object) -> None:
            info(f"\nStopping... ({change_count[0]} changes processed)")
            engine.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _shutdown)

        # keep alive
        while True:
            time.sleep(1)

    except ImportError as exc:
        error(f"Import error: {exc}")
        raise typer.Exit(code=1)

