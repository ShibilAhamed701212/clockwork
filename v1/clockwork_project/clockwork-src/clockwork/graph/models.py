"""
clockwork/graph/models.py
--------------------------
Data models for the Knowledge Graph subsystem.

Defines node types, edge types, and query result containers
used throughout the graph engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Node / Edge type constants ─────────────────────────────────────────────

class NodeType:
    FILE       = "file"
    MODULE     = "module"
    CLASS      = "class"
    FUNCTION   = "function"
    DEPENDENCY = "dependency"
    SERVICE    = "service"
    LANGUAGE   = "language"
    LAYER      = "layer"


class EdgeType:
    IMPORTS       = "imports"
    CALLS         = "calls"
    DEPENDS_ON    = "depends_on"
    BELONGS_TO    = "belongs_to"
    CONTAINS      = "contains"
    PART_OF_LAYER = "part_of_layer"
    PART_OF_SERVICE = "part_of_service"


# ── Architecture layer detection ───────────────────────────────────────────

LAYER_PATTERNS: dict[str, list[str]] = {
    "frontend":       ["frontend", "ui", "client", "web", "static", "public", "views", "templates"],
    "backend":        ["backend", "server", "api", "app", "core", "services", "handlers", "routes"],
    "database":       ["database", "db", "models", "migrations", "schema", "repositories", "dao"],
    "infrastructure": ["infra", "infrastructure", "devops", "deploy", "docker", "k8s", "terraform", "scripts"],
    "tests":          ["tests", "test", "spec", "specs", "__tests__"],
}


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A single node in the knowledge graph."""

    node_id:   int
    kind:      str                        # NodeType constant
    label:     str                        # display name
    file_path: str       = ""
    language:  str       = ""
    layer:     str       = ""
    metadata:  str       = "{}"          # JSON string of extra attributes

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":        self.node_id,
            "kind":      self.kind,
            "label":     self.label,
            "file_path": self.file_path,
            "language":  self.language,
            "layer":     self.layer,
        }


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""

    edge_id:          int
    source_id:        int
    target_id:        int
    relationship:     str          # EdgeType constant
    weight:           float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":           self.edge_id,
            "source":       self.source_id,
            "target":       self.target_id,
            "relationship": self.relationship,
            "weight":       self.weight,
        }


@dataclass
class GraphStats:
    """Summary statistics returned after a build."""

    node_count:    int = 0
    edge_count:    int = 0
    file_count:    int = 0
    layer_count:   int = 0
    service_count: int = 0
    language_count: int = 0
    elapsed_ms:    float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count":     self.node_count,
            "edge_count":     self.edge_count,
            "file_count":     self.file_count,
            "layer_count":    self.layer_count,
            "service_count":  self.service_count,
            "language_count": self.language_count,
            "elapsed_ms":     round(self.elapsed_ms, 1),
        }


@dataclass
class QueryResult:
    """Container for graph query results."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }

