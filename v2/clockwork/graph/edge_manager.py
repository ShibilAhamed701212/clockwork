import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(".clockwork/knowledge_graph.db")

EDGE_TYPES = {"imports", "calls", "depends_on", "belongs_to_layer", "contains", "extends", "uses"}

class EdgeManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id    INTEGER NOT NULL,
                    target_id    INTEGER NOT NULL,
                    source_name  TEXT,
                    target_name  TEXT,
                    rel_type     TEXT NOT NULL,
                    weight       REAL DEFAULT 1.0,
                    created      REAL,
                    UNIQUE(source_id, target_id, rel_type)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_src  ON edges(source_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_tgt  ON edges(target_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_type ON edges(rel_type)")
            conn.commit()

    def add(self, source_id: int, target_id: int, rel_type: str,
            source_name: str = "", target_name: str = "", weight: float = 1.0):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO edges
                (source_id, target_id, source_name, target_name, rel_type, weight, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (source_id, target_id, source_name, target_name, rel_type, weight, time.time()))
            conn.commit()

    def get_outgoing(self, node_id: int, rel_type: str = "") -> List[Dict]:
        query  = "SELECT * FROM edges WHERE source_id=?"
        params = [node_id]
        if rel_type:
            query += " AND rel_type=?"
            params.append(rel_type)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row(r) for r in rows]

    def get_incoming(self, node_id: int, rel_type: str = "") -> List[Dict]:
        query  = "SELECT * FROM edges WHERE target_id=?"
        params = [node_id]
        if rel_type:
            query += " AND rel_type=?"
            params.append(rel_type)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row(r) for r in rows]

    def delete_by_source(self, source_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM edges WHERE source_id=?", (source_id,))
            conn.commit()

    def count(self) -> Dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT rel_type, COUNT(*) FROM edges GROUP BY rel_type"
            ).fetchall()
        return {r[0]: r[1] for r in rows}

    def all(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM edges").fetchall()
        return [self._row(r) for r in rows]

    def _row(self, row) -> Dict:
        return {
            "id":          row[0],
            "source_id":   row[1],
            "target_id":   row[2],
            "source_name": row[3],
            "target_name": row[4],
            "rel_type":    row[5],
            "weight":      row[6],
            "created":     row[7],
        }