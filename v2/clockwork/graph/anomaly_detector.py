import sqlite3
from pathlib import Path
from typing import Dict, List

DB_PATH = Path(".clockwork/knowledge_graph.db")

LAYER_ORDER = ["frontend", "backend", "database", "infrastructure"]

class AnomalyDetector:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    def detect_all(self) -> Dict[str, List]:
        return {
            "circular_dependencies": self.detect_circular(),
            "cross_layer_violations": self.detect_cross_layer(),
            "orphan_modules":         self.detect_orphans(),
            "high_coupling":          self.detect_high_coupling(),
        }

    def detect_circular(self) -> List[str]:
        with self._conn() as conn:
            edges = conn.execute(
                "SELECT source_name, target_name FROM edges WHERE rel_type IN ('imports','depends_on')"
            ).fetchall()
        graph: Dict[str, List[str]] = {}
        for src, tgt in edges:
            if src and tgt:
                graph.setdefault(src, []).append(tgt)

        circular = []
        visited  = set()
        rec_stack = set()

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    cycle = " -> ".join(path + [neighbor])
                    if cycle not in circular:
                        circular.append(cycle)
            rec_stack.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node, [node])
        return circular[:20]

    def detect_cross_layer(self) -> List[str]:
        violations = []
        forbidden  = {
            "frontend": ["database"],
            "database": ["frontend"],
        }
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT s.layer, t.layer, s.name, t.name
                FROM edges e
                JOIN nodes s ON e.source_id = s.id
                JOIN nodes t ON e.target_id = t.id
                WHERE s.layer != '' AND t.layer != ''
                AND s.layer != t.layer
                AND e.rel_type IN ('imports','calls','depends_on')
            """).fetchall()
        for src_layer, tgt_layer, src_name, tgt_name in rows:
            blocked = forbidden.get(src_layer, [])
            if tgt_layer in blocked:
                violations.append(
                    src_name + " (" + src_layer + ") -> " + tgt_name + " (" + tgt_layer + ")"
                )
        return violations[:20]

    def detect_orphans(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT name FROM nodes
                WHERE type='file'
                AND id NOT IN (SELECT source_id FROM edges)
                AND id NOT IN (SELECT target_id FROM edges)
            """).fetchall()
        return [r[0] for r in rows]

    def detect_high_coupling(self, threshold: int = 10) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT source_name, COUNT(*) as cnt
                FROM edges
                WHERE rel_type IN ('imports','depends_on')
                GROUP BY source_name
                HAVING cnt >= ?
                ORDER BY cnt DESC
            """, (threshold,)).fetchall()
        return [{"module": r[0], "dependency_count": r[1]} for r in rows]

    def score_health(self) -> Dict:
        issues = self.detect_all()
        score  = 100
        score -= len(issues["circular_dependencies"])  * 15
        score -= len(issues["cross_layer_violations"]) * 10
        score -= len(issues["orphan_modules"])         * 2
        score -= len(issues["high_coupling"])          * 5
        score  = max(0, score)
        return {
            "health_score": score,
            "grade":        "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F",
            "issues":       {k: len(v) for k, v in issues.items()},
        }