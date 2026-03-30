from __future__ import annotations

import time
from pathlib import Path

from clockwork.graph.anomaly_detector import AnomalyDetector
from clockwork.graph.edge_manager import EdgeManager
from clockwork.graph.node_manager import NodeManager
from clockwork.graph.query_engine import QueryEngine


LAYER_RULES = {
	"frontend": ["frontend", "ui", "views", "components", "pages", "static"],
	"backend": ["backend", "api", "routes", "controllers", "services", "core"],
	"database": ["database", "db", "models", "migrations", "schemas", "repositories"],
	"infrastructure": ["infra", "config", "docker", "deploy", "scripts", "ci"],
}


class GraphBuilder:
	def __init__(self, db_path: Path = Path(".clockwork/knowledge_graph.db")) -> None:
		self.nodes = NodeManager(db_path)
		self.edges = EdgeManager(db_path)
		self.query = QueryEngine(db_path)
		self.anomaly = AnomalyDetector(db_path)

	def build_from_repo_map(self, repo_map: dict) -> dict:
		files = self._extract_files(repo_map)
		for file_path, file_data in files.items():
			language = file_data.get("language", "")
			layer = self._infer_layer(file_path)
			node_id = self.nodes.upsert("file", file_path, file_path, language, layer)
			for imported in file_data.get("imports", []):
				target_id = self.nodes.upsert("module", imported, "", language, "")
				self.edges.add(node_id, target_id, "imports", file_path, imported)

		dependencies = repo_map.get("dependencies", {}).get("dependencies", [])
		for dep in dependencies:
			name = dep.get("name", "")
			if name:
				self.nodes.upsert("dependency", name, "", "", "external")

		for component in repo_map.get("components", {}).keys():
			self.nodes.upsert("service", component, "", "", component)

		return self.summary()

	def _extract_files(self, repo_map: dict) -> dict:
		result: dict[str, dict] = {}
		graph = repo_map.get("relationships", {}).get("graph", {})
		for file_path, file_data in graph.items():
			result[file_path] = {
				"imports": file_data.get("imports", []),
				"language": self._detect_lang(file_path),
				"functions": [],
				"classes": [],
			}
		return result

	def _infer_layer(self, file_path: str) -> str:
		lower = file_path.lower().replace("\\", "/")
		for layer, keywords in LAYER_RULES.items():
			if any(keyword in lower for keyword in keywords):
				return layer
		return "backend"

	def _detect_lang(self, path: str) -> str:
		ext_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".go": "Go", ".rs": "Rust", ".java": "Java"}
		return ext_map.get(Path(path).suffix.lower(), "unknown")

	def incremental_update(self, changed_files: list[str], repo_map: dict) -> None:
		for file_path in changed_files:
			self.nodes.clear_by_file(file_path)
		self.build_from_repo_map(repo_map)

	def summary(self) -> dict:
		node_counts = self.nodes.count()
		edge_counts = self.edges.count()
		architecture = self.query.architecture_summary()
		return {
			"total_nodes": sum(node_counts.values()),
			"total_edges": sum(edge_counts.values()),
			"node_breakdown": node_counts,
			"edge_breakdown": edge_counts,
			"layers": architecture.get("layers", {}),
		}

	def health_check(self) -> dict:
		return self.anomaly.score_health()

	def compress(self) -> dict:
		anomalies = self.anomaly.detect_all()
		return {
			"summary": self.summary(),
			"layers": self.query.architecture_summary().get("layers", {}),
			"anomaly_count": sum(len(value) for value in anomalies.values()),
			"orphans": len(self.query.find_orphans()),
			"health": self.health_check(),
		}


__all__ = ["GraphBuilder"]

