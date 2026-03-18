import ast
import re
from pathlib import Path
from typing import Dict, List, Set

class RelationshipMapper:
    def __init__(self, files: List[Path], root: Path):
        self.files = [f for f in files if f.suffix == ".py"]
        self.root = root

    def map(self) -> Dict:
        graph = {}
        entities = {}
        for f in self.files:
            rel = str(f.relative_to(self.root))
            imports, funcs, classes = self._parse_file(f)
            graph[rel] = {"imports": imports}
            entities[rel] = {"functions": funcs, "classes": classes}
        anomalies = self._detect_anomalies(graph)
        circular = self._detect_circular(graph)
        return {
            "graph": graph,
            "entities": entities,
            "anomalies": anomalies,
            "circular_imports": circular,
        }

    def _parse_file(self, path: Path):
        imports, funcs, classes = [], [], []
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.FunctionDef):
                    funcs.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except Exception:
            pass
        return imports, funcs, classes

    def _detect_anomalies(self, graph: Dict) -> List[str]:
        issues = []
        for fname, data in graph.items():
            if not data["imports"] and fname != "__init__.py":
                issues.append("No imports in: " + fname)
        return issues

    def _detect_circular(self, graph: Dict) -> List[str]:
        circular = []
        module_map = {}
        for fname in graph:
            mod = fname.replace("/", ".").replace("\\", ".").replace(".py", "")
            module_map[mod] = graph[fname]["imports"]
        for mod, imports in module_map.items():
            for imp in imports:
                if imp in module_map and mod in module_map.get(imp, []):
                    pair = sorted([mod, imp])
                    entry = pair[0] + " <-> " + pair[1]
                    if entry not in circular:
                        circular.append(entry)
        return circular

    def infer_semantic(self, entities: Dict) -> Dict:
        semantic = {}
        patterns = {
            "get": "data_retrieval", "fetch": "data_retrieval",
            "set": "data_mutation", "update": "data_mutation",
            "create": "creation", "build": "creation",
            "delete": "deletion", "remove": "deletion",
            "validate": "validation", "check": "validation",
            "run": "execution", "execute": "execution",
            "parse": "parsing", "analyze": "analysis",
        }
        for fname, data in entities.items():
            file_semantics = []
            for fn in data.get("functions", []):
                for keyword, meaning in patterns.items():
                    if fn.lower().startswith(keyword):
                        file_semantics.append(fn + " -> " + meaning)
                        break
            if file_semantics:
                semantic[fname] = file_semantics
        return semantic