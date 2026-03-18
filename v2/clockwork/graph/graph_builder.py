import time
from pathlib import Path
from typing import Dict, List

from graph.node_manager    import NodeManager
from graph.edge_manager    import EdgeManager
from graph.query_engine    import QueryEngine
from graph.anomaly_detector import AnomalyDetector

LAYER_RULES = {
    "frontend":      ["frontend", "ui", "views", "components", "pages", "static"],
    "backend":       ["backend", "api", "routes", "controllers", "services", "core"],
    "database":      ["database", "db", "models", "migrations", "schemas", "repositories"],
    "infrastructure":["infra", "config", "docker", "deploy", "scripts", "ci"],
}

class GraphBuilder:
    def __init__(self, db_path: Path = Path(".clockwork/knowledge_graph.db")):
        self.nodes    = NodeManager(db_path)
        self.edges    = EdgeManager(db_path)
        self.query    = QueryEngine(db_path)
        self.anomaly  = AnomalyDetector(db_path)

    def build_from_repo_map(self, repo_map: Dict) -> Dict:
        print("[GraphBuilder] Building knowledge graph...")
        t0 = time.time()

        files = self._extract_files(repo_map)
        for fpath, fdata in files.items():
            lang  = fdata.get("language", "")
            layer = self._infer_layer(fpath)
            nid   = self.nodes.upsert("file", fpath, fpath, lang, layer)
            for imp in fdata.get("imports", []):
                tid = self.nodes.upsert("module", imp, "", lang, "")
                self.edges.add(nid, tid, "imports", fpath, imp)
            for fn in fdata.get("functions", []):
                fid = self.nodes.upsert("function", fn, fpath, lang, layer)
                self.edges.add(nid, fid, "contains", fpath, fn)
            for cls in fdata.get("classes", []):
                cid = self.nodes.upsert("class", cls, fpath, lang, layer)
                self.edges.add(nid, cid, "contains", fpath, cls)

        deps = repo_map.get("dependencies", {}).get("dependencies", [])
        for dep in deps:
            name = dep.get("name", "")
            if name:
                self.nodes.upsert("dependency", name, "", "", "external")

        for arch_comp, comp_files in repo_map.get("components", {}).items():
            for cf in (comp_files or []):
                self.nodes.upsert("service", arch_comp, "", "", arch_comp)

        elapsed = round(time.time() - t0, 3)
        summary = self.summary()
        print("[GraphBuilder] Graph built in " + str(elapsed) + "s | " +
              str(summary["total_nodes"]) + " nodes | " + str(summary["total_edges"]) + " edges")
        return summary

    def _extract_files(self, repo_map: Dict) -> Dict:
        result = {}
        graph  = repo_map.get("relationships", {}).get("graph", {})
        entities = {}
        for fpath, fdata in graph.items():
            result[fpath] = {
                "imports":   fdata.get("imports", []),
                "language":  self._detect_lang(fpath),
                "functions": [],
                "classes":   [],
            }
        lang_data = repo_map.get("languages", {}).get("languages", {})
        for lang, count in lang_data.items():
            pass
        return result

    def _infer_layer(self, file_path: str) -> str:
        lower = file_path.lower().replace("\\", "/")
        for layer, keywords in LAYER_RULES.items():
            if any(kw in lower for kw in keywords):
                return layer
        return "backend"

    def _detect_lang(self, path: str) -> str:
        ext_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                   ".go": "Go", ".rs": "Rust", ".java": "Java"}
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, "unknown")

    def incremental_update(self, changed_files: List[str], repo_map: Dict):
        print("[GraphBuilder] Incremental update: " + str(len(changed_files)) + " files")
        for fpath in changed_files:
            self.nodes.clear_by_file(fpath)
            layer = self._infer_layer(fpath)
            lang  = self._detect_lang(fpath)
            nid   = self.nodes.upsert("file", fpath, fpath, lang, layer)
            self.edges.delete_by_source(nid)
        self.build_from_repo_map(repo_map)

    def summary(self) -> Dict:
        node_counts = self.nodes.count()
        edge_counts = self.edges.count()
        arch_summary = self.query.architecture_summary()
        return {
            "total_nodes":   sum(node_counts.values()),
            "total_edges":   sum(edge_counts.values()),
            "node_breakdown": node_counts,
            "edge_breakdown": edge_counts,
            "layers":         arch_summary.get("layers", {}),
        }

    def health_check(self) -> Dict:
        return self.anomaly.score_health()

    def compress(self) -> Dict:
        summary     = self.summary()
        arch        = self.query.architecture_summary()
        anomalies   = self.anomaly.detect_all()
        orphans     = self.query.find_orphans()
        return {
            "summary":   summary,
            "layers":    arch["layers"],
            "anomaly_count": sum(len(v) for v in anomalies.values()),
            "orphans":   len(orphans),
            "health":    self.health_check(),
        }