"""
clockwork/graph/storage.py
---------------------------
SQLite persistence layer for the Knowledge Graph.

Owns schema creation, node/edge insertion, and raw SQL queries.
All higher-level logic lives in graph_engine.py.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from .models import GraphEdge, GraphNode, GraphStats


# ── DDL ────────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS graph_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kind      TEXT    NOT NULL,
    label     TEXT    NOT NULL,
    file_path TEXT    NOT NULL DEFAULT '',
    language  TEXT    NOT NULL DEFAULT '',
    layer     TEXT    NOT NULL DEFAULT '',
    metadata  TEXT    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS edges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id    INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relationship TEXT    NOT NULL,
    weight       REAL    NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_nodes_kind      ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_label     ON nodes(label);
CREATE INDEX IF NOT EXISTS idx_nodes_layer     ON nodes(layer);
CREATE INDEX IF NOT EXISTS idx_nodes_file_path ON nodes(file_path);
CREATE INDEX IF NOT EXISTS idx_edges_source    ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target    ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_rel       ON edges(relationship);
"""

_DROP_SQL = """
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS graph_meta;
"""


class GraphStorage:
    """
    Manages the SQLite database that backs the knowledge graph.

    Usage::

        storage = GraphStorage(db_path)
        storage.initialise(drop_existing=True)
        nid = storage.insert_node("file", "app.py", file_path="app.py")
        storage.commit()
        storage.close()
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open (or create) the database file."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Commit and close the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def __enter__(self) -> "GraphStorage":
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── schema ─────────────────────────────────────────────────────────────

    def initialise(self, drop_existing: bool = False) -> None:
        """Create tables (optionally dropping existing ones first)."""
        assert self._conn, "Call open() first"
        if drop_existing:
            self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ── node operations ────────────────────────────────────────────────────

    def insert_node(
        self,
        kind:      str,
        label:     str,
        file_path: str = "",
        language:  str = "",
        layer:     str = "",
        metadata:  Optional[dict[str, Any]] = None,
    ) -> int:
        """Insert a node and return its row-id."""
        assert self._conn
        cur = self._conn.execute(
            "INSERT INTO nodes (kind, label, file_path, language, layer, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, label, file_path, language, layer,
             json.dumps(metadata or {})),
        )
        return cur.lastrowid  # type: ignore[return-value]

    def get_or_create_node(
        self,
        kind:  str,
        label: str,
        **kwargs: Any,
    ) -> int:
        """Return existing node id if (kind, label) exists, else insert."""
        assert self._conn
        row = self._conn.execute(
            "SELECT id FROM nodes WHERE kind = ? AND label = ?",
            (kind, label),
        ).fetchone()
        if row:
            return int(row["id"])
        return self.insert_node(kind, label, **kwargs)

    def node_exists(self, kind: str, label: str) -> bool:
        assert self._conn
        row = self._conn.execute(
            "SELECT 1 FROM nodes WHERE kind=? AND label=?", (kind, label)
        ).fetchone()
        return row is not None

    # ── edge operations ────────────────────────────────────────────────────

    def insert_edge(
        self,
        source_id:    int,
        target_id:    int,
        relationship: str,
        weight:       float = 1.0,
    ) -> int:
        """Insert an edge (deduplicates by source/target/relationship)."""
        assert self._conn
        existing = self._conn.execute(
            "SELECT id FROM edges WHERE source_id=? AND target_id=? AND relationship=?",
            (source_id, target_id, relationship),
        ).fetchone()
        if existing:
            return int(existing["id"])
        cur = self._conn.execute(
            "INSERT INTO edges (source_id, target_id, relationship, weight) "
            "VALUES (?, ?, ?, ?)",
            (source_id, target_id, relationship, weight),
        )
        return cur.lastrowid  # type: ignore[return-value]

    # ── metadata ───────────────────────────────────────────────────────────

    def set_meta(self, key: str, value: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_meta(self, key: str) -> Optional[str]:
        assert self._conn
        row = self._conn.execute(
            "SELECT value FROM graph_meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    # ── read queries ───────────────────────────────────────────────────────

    def fetch_nodes(
        self,
        kind:  Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 500,
    ) -> list[GraphNode]:
        assert self._conn
        sql   = "SELECT * FROM nodes WHERE 1=1"
        params: list[Any] = []
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        sql += f" LIMIT {limit}"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_node(r) for r in rows]

    def fetch_edges(
        self,
        relationship: Optional[str] = None,
        limit: int = 2000,
    ) -> list[GraphEdge]:
        assert self._conn
        if relationship:
            rows = self._conn.execute(
                "SELECT * FROM edges WHERE relationship=? LIMIT ?",
                (relationship, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM edges LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_edge(r) for r in rows]

    def fetch_dependents(self, file_path: str) -> list[GraphNode]:
        """Return all nodes that import/depend on the given file path."""
        assert self._conn
        rows = self._conn.execute(
            """
            SELECT DISTINCT n.*
            FROM nodes n
            JOIN edges e ON e.source_id = n.id
            JOIN nodes t ON t.id = e.target_id
            WHERE t.file_path = ?
              AND e.relationship IN ('imports', 'depends_on')
            LIMIT 200
            """,
            (file_path,),
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def fetch_dependencies(self, file_path: str) -> list[GraphNode]:
        """Return all nodes that the given file imports/depends on."""
        assert self._conn
        rows = self._conn.execute(
            """
            SELECT DISTINCT t.*
            FROM nodes n
            JOIN edges e ON e.source_id = n.id
            JOIN nodes t ON t.id = e.target_id
            WHERE n.file_path = ?
              AND e.relationship IN ('imports', 'depends_on')
            LIMIT 200
            """,
            (file_path,),
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def count_nodes(self) -> int:
        assert self._conn
        return int(self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])

    def count_edges(self) -> int:
        assert self._conn
        return int(self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0])

    def count_nodes_by_kind(self) -> dict[str, int]:
        assert self._conn
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS c FROM nodes GROUP BY kind"
        ).fetchall()
        return {r["kind"]: r["c"] for r in rows}

    def export_json(self) -> dict[str, Any]:
        """Export the entire graph as a JSON-serialisable dict."""
        assert self._conn
        nodes = [_row_to_node(r).to_dict() for r in
                 self._conn.execute("SELECT * FROM nodes").fetchall()]
        edges = [_row_to_edge(r).to_dict() for r in
                 self._conn.execute("SELECT * FROM edges").fetchall()]
        return {"nodes": nodes, "edges": edges}


# ── helpers ────────────────────────────────────────────────────────────────

def _row_to_node(row: sqlite3.Row) -> GraphNode:
    return GraphNode(
        node_id=row["id"],
        kind=row["kind"],
        label=row["label"],
        file_path=row["file_path"],
        language=row["language"],
        layer=row["layer"],
        metadata=row["metadata"],
    )


def _row_to_edge(row: sqlite3.Row) -> GraphEdge:
    return GraphEdge(
        edge_id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        relationship=row["relationship"],
        weight=row["weight"],
    )

