"""
clockwork/graph/graph_engine.py
--------------------------------
Main entry-point for the Knowledge Graph subsystem.

Replaces the previous stub with a full implementation.

Spec §8 pipeline:
    Repository Scan  →  AST Parsing  →  Dependency Detection
    →  Relationship Extraction  →  Graph Construction

Usage::

    engine = GraphEngine(repo_root=Path("."))
    stats  = engine.build()
    q      = engine.query()
    deps   = q.who_depends_on("clockwork/scanner/scanner.py")
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from .builder import GraphBuilder
from .models import GraphStats
from .queries import GraphQueryEngine
from .storage import GraphStorage


class GraphEngine:
    """
    Facade that wires together GraphStorage, GraphBuilder, and
    GraphQueryEngine.

    Parameters
    ----------
    repo_path:
        Root of the repository.  The engine reads
        ``.clockwork/repo_map.json`` and writes to
        ``.clockwork/knowledge_graph.db``.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path    = repo_path.resolve()
        self.clockwork_dir = self.repo_path / ".clockwork"
        self.db_path      = self.clockwork_dir / "knowledge_graph.db"
        self._storage: Optional[GraphStorage] = None

    # ── public API ─────────────────────────────────────────────────────────

    def build(self, repo_map: Optional[dict[str, Any]] = None) -> GraphStats:
        """
        Build (or rebuild) the knowledge graph.

        Parameters
        ----------
        repo_map:
            Pre-loaded repo_map dict.  If omitted, the engine loads
            ``.clockwork/repo_map.json`` automatically.

        Returns
        -------
        GraphStats
            Node/edge counts and elapsed time.
        """
        if repo_map is None:
            repo_map = self._load_repo_map()

        storage = GraphStorage(self.db_path)
        storage.open()
        try:
            storage.initialise(drop_existing=True)
            builder = GraphBuilder(storage)
            stats   = builder.build(repo_map)
            storage.set_meta("built_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            storage.set_meta("stats", json.dumps(stats.to_dict()))
            storage.commit()
        except Exception:
            storage.close()
            raise
        self._storage = storage
        return stats

    def query(self) -> GraphQueryEngine:
        """
        Return a GraphQueryEngine backed by the current database.

        Automatically opens the database if not already open.
        """
        if self._storage is None or self._storage._conn is None:
            storage = GraphStorage(self.db_path)
            storage.open()
            self._storage = storage
        return GraphQueryEngine(self._storage)

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._storage:
            self._storage.close()
            self._storage = None

    def db_exists(self) -> bool:
        """Return True if the knowledge_graph.db file exists."""
        return self.db_path.exists()

    # ── private helpers ────────────────────────────────────────────────────

    def _load_repo_map(self) -> dict[str, Any]:
        repo_map_path = self.clockwork_dir / "repo_map.json"
        if not repo_map_path.exists():
            raise FileNotFoundError(
                f"repo_map.json not found at {repo_map_path}. "
                "Run:  clockwork scan"
            )
        try:
            return json.loads(repo_map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse repo_map.json: {exc}") from exc

    def __enter__(self) -> "GraphEngine":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

