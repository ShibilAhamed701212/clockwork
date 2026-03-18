import json
import re
from pathlib import Path
from typing import Dict, List

DEP_FILES = {
    "requirements.txt": "pip",
    "pyproject.toml": "poetry",
    "package.json": "npm",
    "Cargo.toml": "cargo",
    "go.mod": "go",
}

class DependencyAnalyzer:
    def __init__(self, root: Path):
        self.root = root

    def analyze(self) -> Dict:
        results = {"system": None, "dependencies": [], "raw": {}}
        for filename, system in DEP_FILES.items():
            fp = self.root / filename
            if fp.exists():
                results["system"] = system
                deps = self._parse(fp, system)
                results["dependencies"] = deps
                results["raw"][filename] = deps
                break
        return results

    def _parse(self, path: Path, system: str) -> List[Dict]:
        deps = []
        try:
            if system == "pip":
                deps = self._parse_requirements(path)
            elif system == "npm":
                deps = self._parse_package_json(path)
            elif system == "poetry":
                deps = self._parse_toml(path)
            elif system == "go":
                deps = self._parse_go_mod(path)
        except Exception as e:
            print("[DependencyAnalyzer] Parse error: " + str(e))
        return deps

    def _parse_requirements(self, path: Path) -> List[Dict]:
        deps = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"([a-zA-Z0-9_\-]+)([>=<!].+)?", line)
            if match:
                deps.append({"name": match.group(1), "version": (match.group(2) or "").strip()})
        return deps

    def _parse_package_json(self, path: Path) -> List[Dict]:
        data = json.loads(path.read_text())
        deps = []
        for section in ("dependencies", "devDependencies"):
            for name, ver in data.get(section, {}).items():
                deps.append({"name": name, "version": ver})
        return deps

    def _parse_toml(self, path: Path) -> List[Dict]:
        deps = []
        in_deps = False
        for line in path.read_text().splitlines():
            line = line.strip()
            if line in ("[tool.poetry.dependencies]", "[dependencies]"):
                in_deps = True
                continue
            if line.startswith("[") and in_deps:
                in_deps = False
            if in_deps and "=" in line:
                name, ver = line.split("=", 1)
                deps.append({"name": name.strip(), "version": ver.strip().strip('"')})
        return deps

    def _parse_go_mod(self, path: Path) -> List[Dict]:
        deps = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if line.startswith("require ") or (line and not line.startswith("//")):
                parts = line.split()
                if len(parts) == 2 and "/" in parts[0]:
                    deps.append({"name": parts[0], "version": parts[1]})
        return deps

    def detect_anomalies(self, deps: List[Dict]) -> List[str]:
        issues = []
        names = [d["name"].lower() for d in deps]
        seen = set()
        for name in names:
            if name in seen:
                issues.append("Duplicate dependency: " + name)
            seen.add(name)
        return issues