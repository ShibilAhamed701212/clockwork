"""
clockwork/graph/queries.py
---------------------------
High-level query API for the Knowledge Graph.

Answers the questions defined in spec §13:
  - Which files depend on X?
  - Which modules import Y?
  - Which components belong to layer Z?
  - Which files would be affected if X is deleted?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EdgeType, GraphNode, NodeType, QueryResult
from .storage import GraphStorage


class GraphQueryEngine:
    """
    Provides a clean query API on top of GraphStorage.

    Usage::

        q = GraphQueryEngine(storage)
        dependents = q.who_depends_on("clockwork/scanner/scanner.py")
        layer_files = q.files_in_layer("backend")
    """

    def __init__(self, storage: GraphStorage) -> None:
        self._s = storage

    # ── dependency queries (spec §13, §14) ─────────────────────────────────

    def who_depends_on(self, file_path: str) -> list[GraphNode]:
        """
        Return all files that directly import / depend on *file_path*.

        Used by the Brain before allowing file deletion (spec §14).
        """
        return self._s.fetch_dependents(file_path)

    def dependencies_of(self, file_path: str) -> list[GraphNode]:
        """Return all files / packages that *file_path* imports."""
        return self._s.fetch_dependencies(file_path)

    def is_safe_to_delete(self, file_path: str) -> tuple[bool, list[str]]:
        """
        Returns (safe, [reasons]).

        safe=False means other files import this file — deletion would break them.
        """
        dependents = self.who_depends_on(file_path)
        if dependents:
            reasons = [f"{d.file_path} imports {file_path}" for d in dependents]
            return False, reasons
        return True, []

    # ── layer queries ──────────────────────────────────────────────────────

    def files_in_layer(self, layer: str) -> list[GraphNode]:
        """Return all file nodes tagged to the given architectural layer."""
        return self._s.fetch_nodes(kind=NodeType.FILE, layer=layer)

    def layer_summary(self) -> dict[str, int]:
        """Return {layer_name: file_count} for all layers."""
        nodes = self._s.fetch_nodes(kind=NodeType.FILE, limit=10_000)
        summary: dict[str, int] = {}
        for node in nodes:
            lyr = node.layer or "unknown"
            summary[lyr] = summary.get(lyr, 0) + 1
        return summary

    # ── language queries ───────────────────────────────────────────────────

    def files_by_language(self, language: str) -> list[GraphNode]:
        """Return all file nodes for the given language."""
        if self._s._conn is None:
            raise RuntimeError("GraphStorage is not open. Call storage.open() before querying.")
        rows = self._s._conn.execute(
            "SELECT * FROM nodes WHERE kind=? AND language=? LIMIT 500",
            (NodeType.FILE, language),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    def language_counts(self) -> dict[str, int]:
        """Return {language: file_count}."""
        assert self._s._conn
        rows = self._s._conn.execute(
            "SELECT language, COUNT(*) AS c FROM nodes "
            "WHERE kind=? AND language != '' GROUP BY language",
            (NodeType.FILE,),
        ).fetchall()
        return {r["language"]: r["c"] for r in rows}

    # ── import queries ─────────────────────────────────────────────────────

    def files_importing(self, module_name: str) -> list[GraphNode]:
        """
        Return files that import *module_name* (exact label match on
        DEPENDENCY or FILE nodes, following depends_on / imports edges).
        """
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT src.*
            FROM nodes src
            JOIN edges e  ON e.source_id = src.id
            JOIN nodes tgt ON tgt.id = e.target_id
            WHERE tgt.label = ?
              AND e.relationship IN ('imports','depends_on')
            LIMIT 200
            """,
            (module_name,),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    # ── service queries ────────────────────────────────────────────────────

    def files_in_service(self, service_path: str) -> list[GraphNode]:
        """Return all files belonging to a service node."""
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT f.*
            FROM nodes f
            JOIN edges e ON e.source_id = f.id
            JOIN nodes s ON s.id = e.target_id
            WHERE s.kind=? AND s.label=?
              AND e.relationship=?
            LIMIT 200
            """,
            (NodeType.SERVICE, service_path, EdgeType.PART_OF_SERVICE),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    def services(self) -> list[GraphNode]:
        """Return all service nodes."""
        return self._s.fetch_nodes(kind=NodeType.SERVICE)

    # ── class / function queries ───────────────────────────────────────────

    def symbols_in_file(self, file_path: str) -> list[GraphNode]:
        """Return all class/function nodes contained in a file."""
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT sym.*
            FROM nodes sym
            JOIN edges e ON e.source_id = sym.id
            JOIN nodes f ON f.id = e.target_id
            WHERE f.file_path=?
              AND e.relationship=?
              AND sym.kind IN (?,?)
            LIMIT 200
            """,
            (file_path, EdgeType.CONTAINS, NodeType.CLASS, NodeType.FUNCTION),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    # ── full graph export ──────────────────────────────────────────────────

    def export(self) -> dict[str, Any]:
        """Export the entire graph as a dict (for JSON serialisation)."""
        return self._s.export_json()

    def stats(self) -> dict[str, Any]:
        """Return per-kind node counts and edge count."""
        return {
            "nodes_by_kind": self._s.count_nodes_by_kind(),
            "total_nodes":   self._s.count_nodes(),
            "total_edges":   self._s.count_edges(),
            "layers":        self.layer_summary(),
            "languages":     self.language_counts(),
        }

