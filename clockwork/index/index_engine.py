"""
clockwork/index/index_engine.py
--------------------------------
Main engine for the Live Context Index subsystem.

Orchestrates:
  - IndexStorage   (.clockwork/index.db)
  - IncrementalScanner  (single-file analysis)
  - RepositoryWatcher   (watchdog filesystem events)
  - Graph + Context sync after each change

Spec §3 pipeline:
    Repository Filesystem
        ↓
    Filesystem Watcher
        ↓
    Change Event Queue
        ↓
    Incremental Analysis
        ↓
    Knowledge Graph Update
        ↓
    Context Engine Sync
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from .incremental_scanner import IncrementalScanner
from .models import ChangeEvent, EventType, IndexEntry, IndexStats, compute_file_hash
from .storage import IndexStorage
from .watcher import RepositoryWatcher

logger = logging.getLogger("clockwork.index")


class LiveContextIndex:
    """
    The primary entry point for module 10.

    Responsibilities:
      1. Build / repair the full index from the current repository state.
      2. Watch for file changes and update the index incrementally.
      3. Sync the Knowledge Graph and Context Engine after each change.

    Usage::

        engine = LiveContextIndex(repo_root=Path("."))
        stats  = engine.build()          # full initial index
        engine.watch()                   # start real-time watching
        # ... later ...
        engine.stop()
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.db_path       = self.clockwork_dir / "index.db"
        self._storage      = IndexStorage(self.db_path)
        self._scanner      = IncrementalScanner()
        self._watcher: Optional[RepositoryWatcher] = None
        self._watching     = False

    # ── full index build ───────────────────────────────────────────────────

    def build(self, drop_existing: bool = False) -> IndexStats:
        """
        Walk the entire repository and populate index.db.

        Skips files whose hash hasn't changed (spec §12).
        Used by `clockwork index` and `clockwork repair`.
        """
        t0 = time.perf_counter()

        self._storage.open()
        self._storage.initialise(drop_existing=drop_existing)

        total = indexed = skipped = 0

        for root_dir, dirs, files in os.walk(str(self.repo_root)):
            # prune ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in _IGNORE_DIRS and not d.startswith(".")
            ]

            for fname in files:
                abs_path = os.path.join(root_dir, fname)
                total += 1

                # fast hash check before full scan
                try:
                    mtime    = os.path.getmtime(abs_path)
                    fhash    = compute_file_hash(abs_path)
                except OSError:
                    skipped += 1
                    continue

                if not self._storage.has_changed(
                    _rel(abs_path, self.repo_root), mtime, fhash
                ):
                    skipped += 1
                    continue

                entry = self._scanner.scan_file(abs_path, str(self.repo_root))
                if entry is None:
                    skipped += 1
                    continue

                self._storage.upsert(entry)
                indexed += 1

        self._storage.set_meta("built_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self._storage.commit()
        self._storage.close()

        elapsed = (time.perf_counter() - t0) * 1000
        return IndexStats(
            total_files=total,
            indexed_files=indexed,
            skipped_files=skipped,
            elapsed_ms=elapsed,
        )

    # ── real-time watching ─────────────────────────────────────────────────

    def watch(self, debounce_s: float = 0.2) -> bool:
        """
        Start real-time filesystem watching.

        Returns True if watchdog is available, False if not installed
        (index will still work via manual `clockwork index` calls).
        """
        if self._watching:
            return True

        self._storage.open()
        self._storage.initialise()

        self._watcher = RepositoryWatcher(
            repo_root=self.repo_root,
            on_change=self._handle_event,
            debounce_s=debounce_s,
        )
        try:
            result = self._watcher.start()
        except Exception:
            self._storage.close()
            self._watcher = None
            raise
        self._watching = True
        return result

    def stop(self) -> None:
        """Stop watching and close the database."""
        self._watching = False
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._storage.close()

    def is_watching(self) -> bool:
        return self._watching and (
            self._watcher is not None and self._watcher.is_watching()
        )

    # ── single-file update ─────────────────────────────────────────────────

    def update_file(self, file_path: str) -> Optional[IndexEntry]:
        """
        Manually trigger an incremental update for one file.
        Useful when watchdog is not available.
        """
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
            self._storage.initialise()

        entry = self._scanner.scan_file(file_path, str(self.repo_root))
        if entry:
            self._storage.upsert(entry)
            self._storage.commit()
            self._sync_graph(entry)
            self._sync_context(entry)
            logger.debug("Updated index entry for %s", file_path)
        else:
            # file deleted or unreadable
            rel = _rel(file_path, self.repo_root)
            self._storage.delete(rel)
            self._storage.commit()

        if not was_open:
            self._storage.close()

        return entry

    # ── repair ────────────────────────────────────────────────────────────

    def repair(self) -> IndexStats:
        """
        Wipe the index and rebuild it from scratch.
        Implements `clockwork repair` (spec §14).
        """
        logger.info("Repairing index — wiping and rebuilding...")
        return self.build(drop_existing=True)

    # ── query helpers ──────────────────────────────────────────────────────

    def get_entry(self, file_path: str) -> Optional[IndexEntry]:
        """Return the cached IndexEntry for a file, or None."""
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        entry = self._storage.get(file_path)
        if not was_open:
            self._storage.close()
        return entry

    def all_entries(self) -> list[IndexEntry]:
        """Return all IndexEntry records."""
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        entries = self._storage.all_entries()
        if not was_open:
            self._storage.close()
        return entries

    def count(self) -> int:
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        n = self._storage.count()
        if not was_open:
            self._storage.close()
        return n

    # ── internal event handler ─────────────────────────────────────────────

    def _handle_event(self, event: ChangeEvent) -> None:
        """
        Called by DebouncedProcessor for each debounced filesystem event.
        Implements spec §6 (incremental scanner) and §7 (graph update).
        """
        logger.info("Event: %s %s", event.event_type, event.file_path)

        if event.event_type == EventType.DELETED:
            rel = _rel(event.file_path, self.repo_root)
            self._storage.delete(rel)
            self._storage.commit()
            return

        if event.event_type == EventType.RENAMED and event.src_path:
            old_rel = _rel(event.src_path, self.repo_root)
            self._storage.delete(old_rel)

        entry = self._scanner.scan_file(event.file_path, str(self.repo_root))
        if entry is None:
            return

        # check if content actually changed (spec §12)
        if not self._storage.has_changed(entry.file_path, entry.last_modified, entry.file_hash):
            logger.debug("No meaningful change in %s — skipping", entry.file_path)
            return

        self._storage.upsert(entry)
        self._storage.commit()

        # downstream sync
        self._sync_graph(entry)
        self._sync_context(entry)

    # ── downstream sync ────────────────────────────────────────────────────

    def _sync_graph(self, entry: IndexEntry) -> None:
        """
        Update the Knowledge Graph for the changed file (spec §7).

        Steps: remove old node relationships → parse new file → insert nodes.
        Gracefully skips if knowledge_graph.db doesn't exist yet.
        """
        db_path = self.clockwork_dir / "knowledge_graph.db"
        if not db_path.exists():
            return

        try:
            from clockwork.graph.storage import GraphStorage
            from clockwork.graph.models import NodeType, EdgeType
            from clockwork.graph.builder import _detect_layer

            storage = GraphStorage(db_path)
            storage.open()

            # remove old file node + its edges (cascade delete handles edges)
            if storage._conn is None:
                raise RuntimeError("GraphStorage connection is None inside _sync_graph")
            storage._conn.execute(
                "DELETE FROM nodes WHERE kind=? AND file_path=?",
                (NodeType.FILE, entry.file_path),
            )

            # insert fresh file node
            layer = entry.layer or _detect_layer(entry.file_path)
            nid = storage.insert_node(
                kind=NodeType.FILE,
                label=Path(entry.file_path).name,
                file_path=entry.file_path,
                language=entry.language,
                layer=layer,
            )

            # re-add dependency edges for known internal files
            deps = json.loads(entry.dependencies)
            for imp in deps:
                slash = imp.replace(".", "/")
                for ext in (".py", ""):
                    row = storage._conn.execute(
                        "SELECT id FROM nodes WHERE kind=? AND (file_path=? OR file_path=?)",
                        (NodeType.FILE, slash + ext, slash),
                    ).fetchone()
                    if row:
                        storage.insert_edge(nid, row["id"], EdgeType.IMPORTS)
                        break

            storage.commit()
            storage.close()
            logger.debug("Graph synced for %s", entry.file_path)

        except Exception as exc:
            logger.warning("Graph sync failed for %s: %s", entry.file_path, exc)

    def _sync_context(self, entry: IndexEntry) -> None:
        """
        Notify the Context Engine of the change (spec §8).

        Records the changed file in context.yaml recent_changes.
        Gracefully skips if context.yaml doesn't exist yet.
        """
        context_path = self.clockwork_dir / "context.yaml"
        if not context_path.exists():
            return

        try:
            from clockwork.context import ContextEngine
            engine = ContextEngine(self.clockwork_dir)
            engine.record_change(
                description=f"File changed: {entry.file_path}",
                changed_files=[entry.file_path],
                agent="clockwork.index",
                change_type="file_change",
            )
            logger.debug("Context synced for %s", entry.file_path)
        except Exception as exc:
            logger.warning("Context sync failed for %s: %s", entry.file_path, exc)


# ── helpers ────────────────────────────────────────────────────────────────

_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
    "eggs",
}


def _rel(abs_path: str, repo_root: Path) -> str:
    """Return a repo-relative forward-slash path."""
    try:
        return str(Path(abs_path).relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return abs_path.replace("\\", "/")

