from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(".clockwork/knowledge_graph.db")


class QueryEngine:
	def __init__(self, db_path: Path = DB_PATH) -> None:
		self.db_path = db_path

	def _conn(self) -> sqlite3.Connection:
		return sqlite3.connect(str(self.db_path))

	def dependents_of(self, name: str) -> list[dict]:
		with self._conn() as conn:
			rows = conn.execute(
				"""
				SELECT DISTINCT n.* FROM nodes n
				JOIN edges e ON e.source_id = n.id
				JOIN nodes t ON e.target_id = t.id
				WHERE t.name LIKE ? AND e.rel_type IN ('imports','depends_on')
				""",
				("%" + name + "%",),
			).fetchall()
		return [self._node(row) for row in rows]

	def dependencies_of(self, name: str) -> list[dict]:
		with self._conn() as conn:
			rows = conn.execute(
				"""
				SELECT DISTINCT n.* FROM nodes n
				JOIN edges e ON e.target_id = n.id
				JOIN nodes s ON e.source_id = s.id
				WHERE s.name LIKE ? AND e.rel_type IN ('imports','depends_on')
				""",
				("%" + name + "%",),
			).fetchall()
		return [self._node(row) for row in rows]

	def files_in_layer(self, layer: str) -> list[dict]:
		with self._conn() as conn:
			rows = conn.execute("SELECT * FROM nodes WHERE layer=? AND type='file'", (layer,)).fetchall()
		return [self._node(row) for row in rows]

	def find_orphans(self) -> list[dict]:
		with self._conn() as conn:
			rows = conn.execute(
				"""
				SELECT * FROM nodes
				WHERE id NOT IN (SELECT source_id FROM edges)
				AND id NOT IN (SELECT target_id FROM edges)
				AND type = 'file'
				"""
			).fetchall()
		return [self._node(row) for row in rows]

	def architecture_summary(self) -> dict:
		with self._conn() as conn:
			layer_counts = conn.execute(
				"SELECT layer, COUNT(*) FROM nodes WHERE type='file' AND layer!='' GROUP BY layer"
			).fetchall()
			total_nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
			total_edges = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
		return {
			"total_nodes": total_nodes,
			"total_edges": total_edges,
			"layers": {row[0]: row[1] for row in layer_counts},
		}

	def _node(self, row) -> dict:
		return {
			"id": row[0],
			"type": row[1],
			"name": row[2],
			"file_path": row[3],
			"language": row[4],
			"layer": row[5],
		}


__all__ = ["QueryEngine"]

