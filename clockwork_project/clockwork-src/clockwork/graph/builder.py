"""
clockwork/graph/builder.py
---------------------------
Builds the knowledge graph from a ScanResult / repo_map dict.

Pipeline (spec §8):
    repo_map.json
        ↓
    File nodes
        ↓
    Language / Layer / Service nodes
        ↓
    Dependency edges  (from symbol imports)
        ↓
    Structural edges  (belongs_to, part_of_layer)
        ↓
    Commit to SQLite
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .models import (
    EdgeType,
    GraphStats,
    LAYER_PATTERNS,
    NodeType,
)
from .storage import GraphStorage


class GraphBuilder:
    """
    Constructs nodes and edges from a repo_map dict and writes them
    to the provided GraphStorage instance.

    Usage::

        storage = GraphStorage(db_path)
        storage.open()
        storage.initialise(drop_existing=True)
        builder = GraphBuilder(storage)
        stats = builder.build(repo_map)
        storage.close()
    """

    def __init__(self, storage: GraphStorage) -> None:
        self._s = storage

    # ── public entry point ─────────────────────────────────────────────────

    def build(self, repo_map: dict[str, Any]) -> GraphStats:
        """
        Full build from a repo_map dict.

        Returns GraphStats with counts and elapsed time.
        """
        t0 = time.perf_counter()

        files: list[dict[str, Any]] = repo_map.get("files", [])

        # 1. Language nodes
        self._build_language_nodes(repo_map)

        # 2. Layer nodes
        layer_ids = self._build_layer_nodes()

        # 3. Service nodes (detected from directory structure)
        service_ids = self._build_service_nodes(files)

        # 4. File nodes + structural edges
        file_node_ids = self._build_file_nodes(files, layer_ids, service_ids)

        # 5. Symbol nodes (classes, functions) from file entries
        self._build_symbol_nodes(files, file_node_ids)

        # 6. Dependency edges (imports between files)
        self._build_import_edges(files, file_node_ids)

        # 7. External dependency nodes (third-party packages)
        self._build_external_dep_nodes(files, file_node_ids)

        self._s.commit()

        elapsed = (time.perf_counter() - t0) * 1000
        counts = self._s.count_nodes_by_kind()

        return GraphStats(
            node_count=self._s.count_nodes(),
            edge_count=self._s.count_edges(),
            file_count=counts.get(NodeType.FILE, 0),
            layer_count=counts.get(NodeType.LAYER, 0),
            service_count=counts.get(NodeType.SERVICE, 0),
            language_count=counts.get(NodeType.LANGUAGE, 0),
            elapsed_ms=elapsed,
        )

    # ── language nodes ─────────────────────────────────────────────────────

    def _build_language_nodes(self, repo_map: dict[str, Any]) -> None:
        """Insert one node per detected language."""
        languages: dict[str, Any] = repo_map.get("languages", {})
        if isinstance(languages, dict):
            for lang_name in languages:
                self._s.get_or_create_node(NodeType.LANGUAGE, lang_name)
        elif isinstance(languages, list):
            for lang_name in languages:
                self._s.get_or_create_node(NodeType.LANGUAGE, str(lang_name))

    # ── layer nodes ────────────────────────────────────────────────────────

    def _build_layer_nodes(self) -> dict[str, int]:
        """Insert architectural layer nodes, return {layer_name: node_id}."""
        layer_ids: dict[str, int] = {}
        for layer_name in LAYER_PATTERNS:
            nid = self._s.get_or_create_node(NodeType.LAYER, layer_name)
            layer_ids[layer_name] = nid
        return layer_ids

    # ── service nodes ──────────────────────────────────────────────────────

    def _build_service_nodes(self, files: list[dict[str, Any]]) -> dict[str, int]:
        """
        Detect service boundaries from directory structure.

        A 'service' is a top-level directory that contains source files
        and looks like a bounded context (services/, apps/, packages/, etc.).
        """
        service_roots: set[str] = set()
        service_parent_dirs = {"services", "apps", "packages", "modules", "components"}

        for f in files:
            parts = Path(f.get("path", "")).parts
            if len(parts) >= 2 and parts[0].lower() in service_parent_dirs:
                service_roots.add(f"{parts[0]}/{parts[1]}")

        service_ids: dict[str, int] = {}
        for svc in sorted(service_roots):
            nid = self._s.get_or_create_node(
                NodeType.SERVICE, svc, file_path=svc
            )
            service_ids[svc] = nid
        return service_ids

    # ── file nodes ─────────────────────────────────────────────────────────

    def _build_file_nodes(
        self,
        files: list[dict[str, Any]],
        layer_ids: dict[str, int],
        service_ids: dict[str, int],
    ) -> dict[str, int]:
        """
        Insert one node per file, plus structural edges:
        - file belongs_to language
        - file part_of_layer <layer>
        - file part_of_service <service>  (when applicable)
        """
        file_node_ids: dict[str, int] = {}

        for f in files:
            path     = f.get("path", "")
            language = f.get("language", "")
            layer    = _detect_layer(path)

            if not path:
                continue

            nid = self._s.insert_node(
                kind=NodeType.FILE,
                label=Path(path).name,
                file_path=path,
                language=language,
                layer=layer,
            )
            file_node_ids[path] = nid

            # edge → language node
            if language:
                lang_nid = self._s.get_or_create_node(NodeType.LANGUAGE, language)
                self._s.insert_edge(nid, lang_nid, EdgeType.BELONGS_TO)

            # edge → layer node
            if layer and layer in layer_ids:
                self._s.insert_edge(nid, layer_ids[layer], EdgeType.PART_OF_LAYER)

            # edge → service node
            svc_key = _detect_service(path)
            if svc_key and svc_key in service_ids:
                self._s.insert_edge(nid, service_ids[svc_key], EdgeType.PART_OF_SERVICE)

        return file_node_ids

    # ── symbol nodes ───────────────────────────────────────────────────────

    def _build_symbol_nodes(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        Insert class/function nodes for symbols detected by the scanner.
        Each symbol gets a 'contains' edge from its parent file.
        """
        for f in files:
            path    = f.get("path", "")
            symbols = f.get("symbols", [])
            file_nid = file_node_ids.get(path)
            if not file_nid or not symbols:
                continue

            for sym in symbols:
                sym_kind  = sym.get("kind", "function")
                sym_name  = sym.get("name", "")
                if not sym_name:
                    continue

                node_type = NodeType.CLASS if sym_kind == "class" else NodeType.FUNCTION
                label     = f"{sym_name} ({Path(path).name})"
                sym_nid   = self._s.insert_node(
                    kind=node_type,
                    label=label,
                    file_path=path,
                )
                self._s.insert_edge(file_nid, sym_nid, EdgeType.CONTAINS)

    # ── import edges ───────────────────────────────────────────────────────

    def _build_import_edges(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        For each file, resolve its imports list to other known files
        and create 'imports' edges.

        Strategy: try to match import strings to known file paths by
        converting dot-notation to path fragments.
        """
        # Build a lookup: module-path fragment → node id
        # e.g.  "clockwork/scanner/scanner.py" → 42
        path_index: dict[str, int] = {}
        for fpath, nid in file_node_ids.items():
            normalised = fpath.replace("\\", "/")
            path_index[normalised] = nid
            # also index stem (without extension)
            stem_key = normalised.rsplit(".", 1)[0]
            path_index.setdefault(stem_key, nid)
            # and dotted module form
            dot_key = stem_key.replace("/", ".")
            path_index.setdefault(dot_key, nid)

        for f in files:
            src_path = f.get("path", "").replace("\\", "/")
            src_nid  = file_node_ids.get(f.get("path", ""))
            if not src_nid:
                continue

            for imp in f.get("imports", []):
                target_nid = _resolve_import(imp, src_path, path_index)
                if target_nid and target_nid != src_nid:
                    self._s.insert_edge(src_nid, target_nid, EdgeType.IMPORTS)

    # ── external dependency nodes ──────────────────────────────────────────

    def _build_external_dep_nodes(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        Imports that could NOT be resolved to internal files are treated
        as external dependencies.  One DEPENDENCY node per unique package
        root name, with a 'depends_on' edge from each importing file.
        """
        # Build set of known internal module stems for quick lookup
        internal_stems: set[str] = set()
        for fpath in file_node_ids:
            norm = fpath.replace("\\", "/").rsplit(".", 1)[0]
            for part in norm.replace("/", ".").split("."):
                internal_stems.add(part)

        for f in files:
            src_nid  = file_node_ids.get(f.get("path", ""))
            if not src_nid:
                continue
            for imp in f.get("imports", []):
                root = imp.split(".")[0]
                # skip stdlib-ish and known internal names
                if root in _STDLIB_ROOTS or root in internal_stems:
                    continue
                dep_nid = self._s.get_or_create_node(
                    NodeType.DEPENDENCY, root
                )
                self._s.insert_edge(src_nid, dep_nid, EdgeType.DEPENDS_ON)


# ── helpers ────────────────────────────────────────────────────────────────

def _detect_layer(file_path: str) -> str:
    """Map a file path to an architectural layer name."""
    norm = file_path.replace("\\", "/").lower()
    for layer, keywords in LAYER_PATTERNS.items():
        for kw in keywords:
            if f"/{kw}/" in norm or norm.startswith(kw + "/"):
                return layer
    # fallback: tests
    if file_path.lower().endswith("_test.py") or "test" in file_path.lower():
        return "tests"
    return "backend"  # sensible default for unlabelled files


def _detect_service(file_path: str) -> str:
    """Return '<parent>/<service>' string if file is inside a service dir."""
    parts = Path(file_path).parts
    service_parents = {"services", "apps", "packages", "modules", "components"}
    if len(parts) >= 2 and parts[0].lower() in service_parents:
        return f"{parts[0]}/{parts[1]}"
    return ""


def _resolve_import(
    imp: str,
    src_path: str,
    path_index: dict[str, int],
) -> int | None:
    """
    Try to resolve an import string to a known file node id.
    Returns the node id or None.
    """
    # Direct match (e.g. "clockwork.scanner.scanner")
    candidate = path_index.get(imp)
    if candidate:
        return candidate

    # Relative: strip leading dots and try
    stripped = imp.lstrip(".")
    candidate = path_index.get(stripped)
    if candidate:
        return candidate

    # Convert dots to slash path
    slash_form = stripped.replace(".", "/")
    candidate = path_index.get(slash_form)
    if candidate:
        return candidate

    # Try adding .py
    candidate = path_index.get(slash_form + ".py")
    if candidate:
        return candidate

    return None


# Common stdlib root names to skip as external deps
_STDLIB_ROOTS: frozenset[str] = frozenset({
    "os", "sys", "re", "io", "abc", "ast", "csv", "json", "math",
    "time", "copy", "enum", "uuid", "glob", "shutil", "string",
    "struct", "textwrap", "hashlib", "logging", "pathlib", "typing",
    "datetime", "dataclasses", "functools", "itertools", "collections",
    "contextlib", "subprocess", "threading", "multiprocessing",
    "unittest", "tempfile", "zipfile", "tarfile", "sqlite3",
    "urllib", "http", "email", "html", "xml", "base64", "platform",
    "__future__", "builtins", "warnings", "inspect", "importlib",
    "traceback", "argparse", "configparser", "getpass", "socket",
    "ssl", "select", "signal", "ctypes", "weakref", "gc",
})

