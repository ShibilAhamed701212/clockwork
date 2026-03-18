import json
import time
from pathlib import Path
from typing import Dict

from scanner.directory_walker import DirectoryWalker
from scanner.language_detector import LanguageDetector
from scanner.dependency_analyzer import DependencyAnalyzer
from scanner.architecture_inferer import ArchitectureInferer
from scanner.relationship_mapper import RelationshipMapper

REPO_MAP_PATH = Path(".clockwork/repo_map.json")
SCANNER_OUTPUT = Path("scanner/output/repo_map.json")

class Scanner:
    def __init__(self, root: str = "."):
        self.root = Path(root).resolve()

    def run(self) -> Dict:
        print("[Scanner] Starting scan: " + str(self.root))
        t0 = time.time()

        walker = DirectoryWalker(str(self.root))
        files = walker.walk()
        print("[Scanner] Files found: " + str(len(files)))

        lang_detector = LanguageDetector(files)
        lang_data = lang_detector.detect()

        dep_analyzer = DependencyAnalyzer(self.root)
        dep_data = dep_analyzer.analyze()
        dep_names = [d["name"] for d in dep_data.get("dependencies", [])]

        framework_data = lang_detector.detect_frameworks(dep_names)
        skills = lang_detector.infer_skills(lang_data, framework_data)

        arch_inferer = ArchitectureInferer(files, self.root)
        arch_data = arch_inferer.infer()

        rel_mapper = RelationshipMapper(files, self.root)
        rel_data = rel_mapper.map()
        semantic_data = rel_mapper.infer_semantic(rel_data.get("entities", {}))

        dep_anomalies = dep_analyzer.detect_anomalies(dep_data.get("dependencies", []))

        repo_map = {
            "meta": {
                "root": str(self.root),
                "scanned_at": time.time(),
                "duration_s": round(time.time() - t0, 3),
                "total_files": len(files),
            },
            "languages": lang_data,
            "dependencies": dep_data,
            "frameworks": framework_data,
            "architecture": arch_data,
            "relationships": {
                "graph": rel_data.get("graph", {}),
                "circular_imports": rel_data.get("circular_imports", []),
                "anomalies": rel_data.get("anomalies", []) + dep_anomalies,
            },
            "semantic": semantic_data,
            "skills": skills,
            "components": arch_data.get("components", {}),
        }

        self._save(repo_map)
        elapsed = round(time.time() - t0, 3)
        print("[Scanner] Scan complete in " + str(elapsed) + "s")
        return repo_map

    def _save(self, repo_map: Dict):
        for path in [REPO_MAP_PATH, SCANNER_OUTPUT]:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(repo_map, f, indent=2)
        print("[Scanner] Repo map saved.")

    def load(self) -> Dict:
        if REPO_MAP_PATH.exists():
            with open(REPO_MAP_PATH) as f:
                return json.load(f)
        return {}