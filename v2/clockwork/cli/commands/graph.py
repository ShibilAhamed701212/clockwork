import json
from pathlib import Path
from graph.graph_builder    import GraphBuilder
from graph.query_engine     import QueryEngine
from graph.anomaly_detector import AnomalyDetector

class GraphCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, query: str = "status"):
        print("[Graph] Query: " + query)
        self.state.emit_event("graph_queried", {"query": query})

        repo_map_path = Path(".clockwork/repo_map.json")
        db_path       = Path(".clockwork/knowledge_graph.db")

        if query == "build":
            return self._build(repo_map_path)
        elif query == "status":
            return self._status(db_path, repo_map_path)
        elif query == "anomalies":
            return self._anomalies(db_path)
        elif query == "health":
            return self._health(db_path)
        elif query == "deps":
            return self._deps(repo_map_path)
        elif query == "tasks":
            return self._tasks()
        else:
            return self._status(db_path, repo_map_path)

    def _build(self, repo_map_path):
        if not repo_map_path.exists():
            print("[Graph] No repo_map.json. Run 'clockwork scan' first.")
            return {}
        with open(repo_map_path) as f:
            repo_map = json.load(f)
        builder = GraphBuilder()
        summary = builder.build_from_repo_map(repo_map)
        compressed = builder.compress()
        self.context.set("graph_summary", compressed)
        print("[Graph] Nodes: " + str(summary["total_nodes"]))
        print("[Graph] Edges: " + str(summary["total_edges"]))
        print("[Graph] Layers: " + str(summary.get("layers",{})))
        return summary

    def _status(self, db_path, repo_map_path):
        if db_path.exists():
            builder = GraphBuilder()
            summary = builder.summary()
            health  = builder.health_check()
            print("[Graph] Nodes: " + str(summary["total_nodes"]))
            print("[Graph] Edges: " + str(summary["total_edges"]))
            print("[Graph] Health: " + str(health["grade"]) + " (" + str(health["health_score"]) + "/100)")
            print("[Graph] Layers: " + str(summary.get("layers",{})))
            return summary
        elif repo_map_path.exists():
            with open(repo_map_path) as f:
                repo_map = json.load(f)
            meta  = repo_map.get("meta", {})
            langs = repo_map.get("languages", {})
            arch  = repo_map.get("architecture", {})
            print("[Graph] Files:        " + str(meta.get("total_files",0)))
            print("[Graph] Language:     " + str(langs.get("primary","unknown")))
            print("[Graph] Architecture: " + str(arch.get("type","unknown")))
            return repo_map
        else:
            print("[Graph] No graph data. Run 'clockwork graph --query build'")
            return {}

    def _anomalies(self, db_path):
        if not db_path.exists():
            print("[Graph] No graph DB. Run 'clockwork graph --query build' first.")
            return {}
        detector  = AnomalyDetector()
        anomalies = detector.detect_all()
        print("[Graph] Anomaly Report:")
        for atype, items in anomalies.items():
            print("  " + atype + ": " + str(len(items)))
            for item in items[:3]:
                print("    - " + str(item))
        return anomalies

    def _health(self, db_path):
        if not db_path.exists():
            print("[Graph] No graph DB.")
            return {}
        health = GraphBuilder().health_check()
        print("[Graph] Health Score: " + str(health["health_score"]) + "/100 Grade: " + health["grade"])
        for k, v in health["issues"].items():
            print("  " + k + ": " + str(v))
        return health

    def _deps(self, repo_map_path):
        if not repo_map_path.exists():
            print("[Graph] No repo_map.json.")
            return {}
        with open(repo_map_path) as f:
            repo_map = json.load(f)
        deps = repo_map.get("dependencies", {}).get("dependencies", [])
        print("[Graph] Dependencies (" + str(len(deps)) + "):")
        for d in deps[:20]:
            print("  - " + d.get("name","") + " " + d.get("version",""))
        return deps

    def _tasks(self):
        tasks_path = Path(".clockwork/tasks.json")
        if tasks_path.exists():
            tasks = json.loads(tasks_path.read_text())
            print("[Graph] Tasks (" + str(len(tasks)) + "):")
            for t in tasks[:10]:
                print("  [" + t.get("status","?") + "] " + t.get("name",""))
            return tasks
        print("[Graph] No tasks file.")
        return []