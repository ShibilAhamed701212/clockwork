"""
clockwork/cli/commands/graph.py
---------------------------------
`clockwork graph` — generate repository knowledge graph.

Writes a SQLite knowledge graph to .clockwork/knowledge_graph.db.
This module provides the CLI entry point and a foundational graph builder.
The full Knowledge Graph subsystem (clockwork/graph/) extends this.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, error, step, rule


def cmd_graph(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
) -> None:
    """
    Generate a repository knowledge graph from the current repo_map.

    Output: .clockwork/knowledge_graph.db  (SQLite)
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Graph")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    repo_map_path = cw_dir / "repo_map.json"
    if not repo_map_path.exists():
        error("repo_map.json not found.\nRun:  clockwork scan")
        raise typer.Exit(code=1)

    start = time.perf_counter()

    try:
        repo_map: dict = json.loads(repo_map_path.read_text(encoding="utf-8"))
    except Exception as exc:
        error(f"Cannot read repo_map.json: {exc}")
        raise typer.Exit(code=1)

    db_path = cw_dir / "knowledge_graph.db"

    step("Building knowledge graph...")
    node_count, edge_count = _build_graph(repo_map, db_path)

    elapsed_ms = (time.perf_counter() - start) * 1000

    rule()
    success(f"Knowledge graph written to .clockwork/knowledge_graph.db")
    info(f"  Nodes : {node_count}")
    info(f"  Edges : {edge_count}")
    info(f"  Time  : {elapsed_ms:.0f} ms")


def _build_graph(repo_map: dict, db_path: Path) -> tuple[int, int]:
    """
    Build a simple SQLite knowledge graph from repo_map data.

    Schema:
      nodes(id, label, kind, metadata)
      edges(src_id, dst_id, relation)
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.executescript("""
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS edges;

        CREATE TABLE nodes (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            label    TEXT NOT NULL,
            kind     TEXT NOT NULL,
            metadata TEXT
        );

        CREATE TABLE edges (
            src_id   INTEGER NOT NULL,
            dst_id   INTEGER NOT NULL,
            relation TEXT NOT NULL,
            FOREIGN KEY(src_id) REFERENCES nodes(id),
            FOREIGN KEY(dst_id) REFERENCES nodes(id)
        );
    """)

    node_ids: dict[str, int] = {}
    edge_count = 0

    def insert_node(label: str, kind: str, metadata: Optional[dict] = None) -> int:
        cur.execute(
            "INSERT INTO nodes (label, kind, metadata) VALUES (?, ?, ?)",
            (label, kind, json.dumps(metadata or {})),
        )
        nid = cur.lastrowid
        node_ids[label] = nid
        return nid

    def insert_edge(src: str, dst: str, relation: str) -> None:
        nonlocal edge_count
        if src in node_ids and dst in node_ids:
            cur.execute(
                "INSERT INTO edges (src_id, dst_id, relation) VALUES (?, ?, ?)",
                (node_ids[src], node_ids[dst], relation),
            )
            edge_count += 1

    # Project root node
    project_name = repo_map.get("root", "project")
    insert_node(project_name, "project")

    # Language nodes
    for lang, count in repo_map.get("languages", {}).items():
        lang_id = insert_node(lang, "language", {"file_count": count})
        insert_edge(project_name, lang, "uses_language")

    # Directory nodes
    for dir_path, members in repo_map.get("directory_tree", {}).items():
        dir_label = dir_path or "."
        insert_node(dir_label, "directory", {"file_count": len(members)})
        insert_edge(project_name, dir_label, "contains_directory")

    # File nodes
    for file_entry in repo_map.get("files", []):
        path_str = file_entry["path"]
        insert_node(path_str, "file", {
            "extension": file_entry.get("extension", ""),
            "language": file_entry.get("language", ""),
            "size_bytes": file_entry.get("size_bytes", 0),
        })

        # File → directory edge
        parent = str(Path(path_str).parent)
        if parent == ".":
            parent_label = "."
        else:
            parent_label = parent
        insert_edge(parent_label, path_str, "contains_file")

        # File → language edge
        lang = file_entry.get("language", "Other")
        if lang != "Other":
            insert_edge(path_str, lang, "written_in")

    conn.commit()

    total_nodes = cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    conn.close()

    return total_nodes, edge_count
