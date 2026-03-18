from pathlib import Path
from typing import Dict, List

ARCH_SIGNALS = {
    "layered":      ["controllers", "services", "models", "views", "repositories"],
    "microservices":["services", "gateway", "broker", "queue", "event"],
    "cli":          ["cli", "commands", "args", "parser"],
    "monolith":     ["app.py", "main.py", "index.js", "server.py"],
}

COMPONENT_SIGNALS = {
    "backend":      [".py", ".go", ".rs", ".java"],
    "frontend":     [".jsx", ".tsx", ".vue", ".html", ".css"],
    "database":     ["models.py", "schema.py", "migrations", "db.py"],
    "infrastructure":["Dockerfile", "docker-compose.yml", ".terraform", "k8s"],
}

class ArchitectureInferer:
    def __init__(self, files: List[Path], root: Path):
        self.files = files
        self.root = root
        self.names = [str(f.relative_to(root)).lower() for f in files]
        self.dirs = list({f.parent.name.lower() for f in files})

    def infer(self) -> Dict:
        arch_type = self._detect_architecture()
        components = self._detect_components()
        layers = self._detect_layers()
        return {
            "type": arch_type,
            "components": components,
            "layers": layers,
            "confidence": self._score_confidence(arch_type),
        }

    def _detect_architecture(self) -> str:
        scores = {}
        for arch, signals in ARCH_SIGNALS.items():
            score = sum(1 for s in signals if any(s in n for n in self.dirs + self.names))
            scores[arch] = score
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else "unknown"

    def _detect_components(self) -> Dict[str, List[str]]:
        components: Dict[str, List[str]] = {}
        for comp, signals in COMPONENT_SIGNALS.items():
            matched = []
            for f in self.files:
                if any(str(f).endswith(s) or f.name == s for s in signals):
                    matched.append(f.name)
            if matched:
                components[comp] = matched[:10]
        return components

    def _detect_layers(self) -> List[str]:
        layer_keywords = ["api", "core", "utils", "models", "services", "cli", "tests", "config"]
        return [d for d in self.dirs if d in layer_keywords]

    def _score_confidence(self, arch_type: str) -> str:
        if arch_type == "unknown":
            return "low"
        signals = ARCH_SIGNALS.get(arch_type, [])
        hits = sum(1 for s in signals if any(s in n for n in self.dirs + self.names))
        if hits >= 3:
            return "high"
        elif hits >= 1:
            return "medium"
        return "low"