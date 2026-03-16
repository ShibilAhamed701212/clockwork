"""
clockwork/index/storage.py
---------------------------
SQLite persistence layer for the Live Context Index.

Stores per-file metadata in .clockwork/index.db so Clockwork
can detect meaningful changes without re-reading every file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

from .models import IndexEntry

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS index_entries (
    file_path     TEXT PRIMARY KEY,
    last_modified REAL NOT NULL,
    file_hash     TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    language      TEXT NOT NULL DEFAULT '',
    module_type   TEXT NOT NULL DEFAULT '',
    dependencies  TEXT NOT NULL DEFAULT '[]',
    layer         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_language ON index_entries(language);
CREATE INDEX IF NOT EXISTS idx_layer    ON index_entries(layer);
"""

_DROP_SQL = """
DROP TABLE IF EXISTS index_entries;
DROP TABLE IF EXISTS index_meta;
"""


class IndexStorage:
    """
    Manages .clockwork/index.db.

    Usage::

        store = IndexStorage(db_path)
        store.open()
        store.initialise()
        store.upsert(entry)
        store.commit()
        store.close()
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def __enter__(self) -> "IndexStorage":
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def initialise(self, drop_existing: bool = False) -> None:
        assert self._conn
        if drop_existing:
            self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ── CRUD ───────────────────────────────────────────────────────────────

    def upsert(self, entry: IndexEntry) -> None:
        """Insert or replace an index entry."""
        assert self._conn
        self._conn.execute(
            """
            INSERT OR REPLACE INTO index_entries
              (file_path, last_modified, file_hash, size_bytes,
               language, module_type, dependencies, layer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.file_path,
                entry.last_modified,
                entry.file_hash,
                entry.size_bytes,
                entry.language,
                entry.module_type,
                entry.dependencies,
                entry.layer,
            ),
        )

    def delete(self, file_path: str) -> None:
        assert self._conn
        self._conn.execute(
            "DELETE FROM index_entries WHERE file_path=?", (file_path,)
        )

    def get(self, file_path: str) -> Optional[IndexEntry]:
        assert self._conn
        row = self._conn.execute(
            "SELECT * FROM index_entries WHERE file_path=?", (file_path,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def all_entries(self) -> list[IndexEntry]:
        assert self._conn
        rows = self._conn.execute("SELECT * FROM index_entries").fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        assert self._conn
        return int(
            self._conn.execute("SELECT COUNT(*) FROM index_entries").fetchone()[0]
        )

    def has_changed(self, file_path: str, mtime: float, file_hash: str) -> bool:
        """
        Return True if the file is not in the index or its hash differs.
        This is the core change-detection check (spec §12).
        """
        assert self._conn
        row = self._conn.execute(
            "SELECT file_hash, last_modified FROM index_entries WHERE file_path=?",
            (file_path,),
        ).fetchone()
        if row is None:
            return True                        # new file
        if row["file_hash"] != file_hash:
            return True                        # content changed
        return False                           # unchanged — skip

    # ── metadata ───────────────────────────────────────────────────────────

    def set_meta(self, key: str, value: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_meta(self, key: str) -> Optional[str]:
        assert self._conn
        row = self._conn.execute(
            "SELECT value FROM index_meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def drop_all(self) -> None:
        """Wipe the index completely (used by repair)."""
        assert self._conn
        self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()


def _row_to_entry(row: sqlite3.Row) -> IndexEntry:
    return IndexEntry(
        file_path=row["file_path"],
        last_modified=row["last_modified"],
        file_hash=row["file_hash"],
        size_bytes=row["size_bytes"],
        language=row["language"],
        module_type=row["module_type"],
        dependencies=row["dependencies"],
        layer=row["layer"],
    )

