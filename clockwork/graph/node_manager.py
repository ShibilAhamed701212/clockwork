from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(".clockwork/knowledge_graph.db")


class NodeManager:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    type      TEXT NOT NULL,
                    name      TEXT NOT NULL,
                    file_path TEXT,
                    language  TEXT,
                    layer     TEXT,
                    metadata  TEXT,
                    created   REAL,
                    UNIQUE(type, name, file_path)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node_type ON nodes(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_node_name ON nodes(name)")
            conn.commit()

    def upsert(self, node_type: str, name: str, file_path: str = "", language: str = "", layer: str = "", metadata: dict | None = None) -> int:
        metadata = metadata or {}
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO nodes (type, name, file_path, language, layer, metadata, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(type, name, file_path) DO UPDATE SET
                    language=excluded.language,
                    layer=excluded.layer,
                    metadata=excluded.metadata
                """,
                (node_type, name, file_path, language, layer, json.dumps(metadata), time.time()),
            )
            conn.commit()
            row = conn.execute(
                "SELECT id FROM nodes WHERE type=? AND name=? AND file_path=?",
                (node_type, name, file_path),
            ).fetchone()
            return row[0] if row else -1

    def get(self, node_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def find(self, node_type: str = "", name: str = "", layer: str = "") -> list[dict]:
        query = "SELECT * FROM nodes WHERE 1=1"
        params: list[object] = []
        if node_type:
            query += " AND type=?"
            params.append(node_type)
        if name:
            query += " AND name LIKE ?"
            params.append("%" + name + "%")
        if layer:
            query += " AND layer=?"
            params.append(layer)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def delete(self, node_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM nodes WHERE id=?", (node_id,))
            conn.commit()

    def clear_by_file(self, file_path: str) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM nodes WHERE file_path=?", (file_path,))
            conn.commit()

    def count(self) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type").fetchall()
        return {row[0]: row[1] for row in rows}

    def all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM nodes").fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> dict:
        return {
            "id": row[0],
            "type": row[1],
            "name": row[2],
            "file_path": row[3],
            "language": row[4],
            "layer": row[5],
            "metadata": json.loads(row[6] or "{}"),
            "created": row[7],
        }

