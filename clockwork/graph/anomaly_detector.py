from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(".clockwork/knowledge_graph.db")


class AnomalyDetector:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _ensure_schema(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    file_path TEXT,
                    language TEXT,
                    layer TEXT,
                    metadata TEXT,
                    created REAL,
                    UNIQUE(type, name, file_path)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    source_name TEXT,
                    target_name TEXT,
                    rel_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    created REAL,
                    UNIQUE(source_id, target_id, rel_type)
                )
                """
            )
            conn.commit()

    def detect_all(self) -> dict[str, list]:
        return {
            "circular_dependencies": self.detect_circular(),
            "cross_layer_violations": self.detect_cross_layer(),
            "orphan_modules": self.detect_orphans(),
            "high_coupling": self.detect_high_coupling(),
        }

    def detect_circular(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT source_name, target_name FROM edges WHERE rel_type IN ('imports','depends_on')"
            ).fetchall()
        graph: dict[str, list[str]] = {}
        for source, target in rows:
            if source and target:
                graph.setdefault(source, []).append(target)

        circular: list[str] = []
        visited: set[str] = set()
        recursion: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            recursion.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in recursion:
                    cycle = " -> ".join(path + [neighbor])
                    if cycle not in circular:
                        circular.append(cycle)
            recursion.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])
        return circular[:20]

    def detect_cross_layer(self) -> list[str]:
        return []

    def detect_orphans(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT name FROM nodes
                WHERE type='file'
                AND id NOT IN (SELECT source_id FROM edges)
                AND id NOT IN (SELECT target_id FROM edges)
                """
            ).fetchall()
        return [row[0] for row in rows]

    def detect_high_coupling(self, threshold: int = 10) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT source_name, COUNT(*) as cnt
                FROM edges
                WHERE rel_type IN ('imports','depends_on')
                GROUP BY source_name
                HAVING cnt >= ?
                ORDER BY cnt DESC
                """,
                (threshold,),
            ).fetchall()
        return [{"module": row[0], "dependency_count": row[1]} for row in rows]

    def score_health(self) -> dict:
        issues = self.detect_all()
        score = 100
        score -= len(issues["circular_dependencies"]) * 15
        score -= len(issues["cross_layer_violations"]) * 10
        score -= len(issues["orphan_modules"]) * 2
        score -= len(issues["high_coupling"]) * 5
        score = max(0, score)
        return {
            "health_score": score,
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F",
            "issues": {key: len(value) for key, value in issues.items()},
        }

