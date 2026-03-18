import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(".clockwork/knowledge_graph.db")

class QueryEngine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _conn(self):
        return sqlite3.connect(str(self.db_path))

    # ── Node queries ──────────────────────────────────────────────
    def dependents_of(self, name: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DISTINCT n.* FROM nodes n
                JOIN edges e ON e.source_id = n.id
                JOIN nodes t ON e.target_id = t.id
                WHERE t.name LIKE ? AND e.rel_type IN ('imports','depends_on')
            """, ("%" + name + "%",)).fetchall()
        return [self._node(r) for r in rows]

    def dependencies_of(self, name: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DISTINCT n.* FROM nodes n
                JOIN edges e ON e.target_id = n.id
                JOIN nodes s ON e.source_id = s.id
                WHERE s.name LIKE ? AND e.rel_type IN ('imports','depends_on')
            """, ("%" + name + "%",)).fetchall()
        return [self._node(r) for r in rows]

    def callers_of(self, func_name: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DISTINCT n.* FROM nodes n
                JOIN edges e ON e.source_id = n.id
                JOIN nodes t ON e.target_id = t.id
                WHERE t.name = ? AND e.rel_type = 'calls'
            """, (func_name,)).fetchall()
        return [self._node(r) for r in rows]

    def files_in_layer(self, layer: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM nodes WHERE layer=? AND type='file'", (layer,)
            ).fetchall()
        return [self._node(r) for r in rows]

    def find_orphans(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM nodes
                WHERE id NOT IN (SELECT source_id FROM edges)
                AND id NOT IN (SELECT target_id FROM edges)
                AND type = 'file'
            """).fetchall()
        return [self._node(r) for r in rows]

    def impact_of(self, name: str, depth: int = 3) -> List[str]:
        visited = set()
        queue   = [name]
        for _ in range(depth):
            next_q = []
            for n in queue:
                deps = self.dependents_of(n)
                for d in deps:
                    if d["name"] not in visited:
                        visited.add(d["name"])
                        next_q.append(d["name"])
            queue = next_q
        return list(visited)

    def architecture_summary(self) -> Dict:
        with self._conn() as conn:
            layer_counts = conn.execute(
                "SELECT layer, COUNT(*) FROM nodes WHERE type='file' AND layer!='' GROUP BY layer"
            ).fetchall()
            total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        return {
            "total_nodes":  total_nodes,
            "total_edges":  total_edges,
            "layers":       {r[0]: r[1] for r in layer_counts},
        }

    def shortest_path(self, src_name: str, tgt_name: str) -> List[str]:
        with self._conn() as conn:
            src = conn.execute("SELECT id FROM nodes WHERE name=?", (src_name,)).fetchone()
            tgt = conn.execute("SELECT id FROM nodes WHERE name=?", (tgt_name,)).fetchone()
        if not src or not tgt:
            return []
        visited = {src[0]: [src_name]}
        queue   = [src[0]]
        while queue:
            current = queue.pop(0)
            with self._conn() as conn:
                neighbors = conn.execute(
                    "SELECT target_id, target_name FROM edges WHERE source_id=?", (current,)
                ).fetchall()
            for nid, nname in neighbors:
                if nid not in visited:
                    visited[nid] = visited[current] + [nname]
                    if nid == tgt[0]:
                        return visited[nid]
                    queue.append(nid)
        return []

    def _node(self, row) -> Dict:
        return {
            "id": row[0], "type": row[1], "name": row[2],
            "file_path": row[3], "language": row[4], "layer": row[5],
        }