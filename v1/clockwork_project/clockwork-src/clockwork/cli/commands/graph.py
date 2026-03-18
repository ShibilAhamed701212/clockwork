"""
clockwork/cli/commands/graph.py
---------------------------------
`clockwork graph` — generate the repository knowledge graph.

Writes a full SQLite knowledge graph to .clockwork/knowledge_graph.db.

Commands exposed:
    clockwork graph          — build the full graph
    clockwork graph query    — run a query against an existing graph
    clockwork graph stats    — show node / edge counts
    clockwork graph export   — dump graph to JSON
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── Typer sub-app ──────────────────────────────────────────────────────────

graph_app = typer.Typer(
    name="graph",
    help="Build and query the repository knowledge graph.",
    no_args_is_help=False,
    invoke_without_command=True,
)


# ── Default command: build ─────────────────────────────────────────────────

@graph_app.callback(invoke_without_command=True)
def cmd_graph(
    ctx: typer.Context,
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Generate a repository knowledge graph from the current repo_map.

    Output: .clockwork/knowledge_graph.db  (SQLite)
    """
    if ctx.invoked_subcommand is not None:
        return

    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Graph")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    repo_map_path = cw_dir / "repo_map.json"
    if not repo_map_path.exists():
        error("repo_map.json not found.\nRun:  clockwork scan")
        raise typer.Exit(code=1)

    try:
        repo_map: dict = json.loads(repo_map_path.read_text(encoding="utf-8"))
    except Exception as exc:
        error(f"Cannot read repo_map.json: {exc}")
        raise typer.Exit(code=1)

    db_path = cw_dir / "knowledge_graph.db"

    if not as_json:
        step("Building knowledge graph...")

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        stats  = engine.build(repo_map)
        engine.close()
    except Exception as exc:
        error(f"Graph build failed: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats.to_dict())
        return

    rule()
    success(f"Knowledge graph written to .clockwork/knowledge_graph.db")
    info(f"  Nodes (total)  : {stats.node_count}")
    info(f"  Edges (total)  : {stats.edge_count}")
    info(f"  Files          : {stats.file_count}")
    info(f"  Layers         : {stats.layer_count}")
    info(f"  Services       : {stats.service_count}")
    info(f"  Languages      : {stats.language_count}")
    info(f"  Elapsed        : {stats.elapsed_ms:.0f} ms")
    info("\nNext step: run  clockwork graph stats")


# ── Sub-command: stats ─────────────────────────────────────────────────────

@graph_app.command("stats")
def cmd_graph_stats(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show node and edge statistics for the knowledge graph."""
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        stats_dict = engine.query().stats()
        engine.close()
    except Exception as exc:
        error(f"Cannot read graph: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats_dict)
        return

    header("Clockwork Graph Stats")
    info(f"  Total nodes : {stats_dict['total_nodes']}")
    info(f"  Total edges : {stats_dict['total_edges']}")
    rule()
    info("Nodes by kind:")
    for kind, cnt in sorted(stats_dict["nodes_by_kind"].items()):
        info(f"  {kind:<14}: {cnt}")
    rule()
    info("Files by layer:")
    for layer, cnt in sorted(stats_dict["layers"].items()):
        info(f"  {layer:<14}: {cnt}")
    rule()
    info("Files by language:")
    for lang, cnt in sorted(stats_dict["languages"].items(), key=lambda x: -x[1]):
        info(f"  {lang:<14}: {cnt}")


# ── Sub-command: query ─────────────────────────────────────────────────────

@graph_app.command("query")
def cmd_graph_query(
    question: str = typer.Argument(..., help=(
        "Query to run. Examples:\n"
        "  depends-on <file_path>\n"
        "  dependencies-of <file_path>\n"
        "  layer <layer_name>\n"
        "  imports <module_name>\n"
        "  safe-to-delete <file_path>"
    )),
    target: str = typer.Argument("", help="Target file/module/layer for the query."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Query the knowledge graph."""
    root    = (repo_root or Path.cwd()).resolve()
    cw_dir  = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        q      = engine.query()
    except Exception as exc:
        error(f"Cannot open graph: {exc}")
        raise typer.Exit(code=1)

    try:
        result: object = None
        cmd = question.lower().replace("-", "_")

        if cmd == "depends_on" and target:
            nodes = q.who_depends_on(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files that depend on: {target}")
                _print_nodes(nodes)

        elif cmd == "dependencies_of" and target:
            nodes = q.dependencies_of(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Dependencies of: {target}")
                _print_nodes(nodes)

        elif cmd == "layer" and target:
            nodes = q.files_in_layer(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files in layer: {target}")
                _print_nodes(nodes)

        elif cmd == "imports" and target:
            nodes = q.files_importing(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files importing: {target}")
                _print_nodes(nodes)

        elif cmd == "safe_to_delete" and target:
            safe, reasons = q.is_safe_to_delete(target)
            result = {"safe": safe, "reasons": reasons}
            if not as_json:
                header(f"Safe to delete: {target}")
                if safe:
                    success("Yes — no other files depend on this file.")
                else:
                    warn(f"No — {len(reasons)} file(s) depend on it:")
                    for r in reasons:
                        info(f"  • {r}")

        else:
            error(f"Unknown query '{question}'. Run 'clockwork graph query --help'.")
            raise typer.Exit(code=1)

        if as_json and result is not None:
            json_output(result)

    finally:
        engine.close()


# ── Sub-command: export ────────────────────────────────────────────────────

@graph_app.command("export")
def cmd_graph_export(
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output JSON file path (default: .clockwork/graph_export.json).",
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Export the knowledge graph to JSON."""
    root    = (repo_root or Path.cwd()).resolve()
    cw_dir  = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    out_path = output or (cw_dir / "graph_export.json")

    try:
        from clockwork.graph import GraphEngine
        engine     = GraphEngine(root)
        graph_data = engine.query().export()
        engine.close()
    except Exception as exc:
        error(f"Export failed: {exc}")
        raise typer.Exit(code=1)

    out_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
    success(f"Graph exported to {out_path}")
    info(f"  Nodes : {len(graph_data['nodes'])}")
    info(f"  Edges : {len(graph_data['edges'])}")


# ── helpers ────────────────────────────────────────────────────────────────

def _print_nodes(nodes: list) -> None:
    if not nodes:
        warn("No results found.")
        return
    for n in nodes:
        layer = f" [{n.layer}]" if n.layer else ""
        lang  = f" ({n.language})" if n.language else ""
        info(f"  • {n.file_path or n.label}{lang}{layer}")


# ── legacy standalone function (keeps test_cli.py working) ────────────────

def _build_graph(repo_map: dict, db_path: Path) -> tuple[int, int]:
    """
    Thin wrapper kept for backward-compatibility with test_cli.py.
    Builds the graph and returns (node_count, edge_count).
    """
    from clockwork.graph.storage import GraphStorage
    from clockwork.graph.builder import GraphBuilder

    storage = GraphStorage(db_path)
    storage.open()
    storage.initialise(drop_existing=True)
    builder = GraphBuilder(storage)
    stats   = builder.build(repo_map)
    storage.close()
    return stats.node_count, stats.edge_count

