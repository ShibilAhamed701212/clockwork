"""
clockwork/graph/__init__.py
----------------------------
Knowledge Graph subsystem.

The Knowledge Graph builds a SQLite-backed graph model of the
repository so Clockwork (and the Brain) can answer questions like:

  - Which files depend on X?
  - Which modules belong to the backend layer?
  - Is it safe to delete this file?

Public API::

    from clockwork.graph import GraphEngine

    engine = GraphEngine(repo_root=Path("."))
    stats  = engine.build()          # builds .clockwork/knowledge_graph.db
    q      = engine.query()
    deps   = q.who_depends_on("clockwork/scanner/scanner.py")
    layers = q.layer_summary()
    engine.close()
"""

from clockwork.graph.graph_engine import GraphEngine
from clockwork.graph.models import GraphStats, GraphNode, GraphEdge, NodeType, EdgeType
from clockwork.graph.queries import GraphQueryEngine

__all__ = [
    "GraphEngine",
    "GraphQueryEngine",
    "GraphStats",
    "GraphNode",
    "GraphEdge",
    "NodeType",
    "EdgeType",
]

