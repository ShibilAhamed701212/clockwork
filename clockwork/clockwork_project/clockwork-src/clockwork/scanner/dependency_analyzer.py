from __future__ import annotations

from pathlib import Path

from clockwork.scanner.language_detector import detect_language
from clockwork.scanner.symbols import SymbolExtractor


def analyze_dependencies(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return {"imports": [], "language": "Other", "functions": [], "classes": []}
    language = detect_language(str(path))
    extractor = SymbolExtractor()
    definitions, imports = extractor.extract(path, language=language)
    return {
        "imports": imports,
        "language": language,
        "functions": [symbol.name for symbol in definitions if symbol.kind == "function"],
        "classes": [symbol.name for symbol in definitions if symbol.kind == "class"],
    }


class DependencyAnalyzer:
    """Compatibility analyzer that aggregates dependencies across a repository root."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def analyze(self) -> dict:
        dependencies: dict[str, list[str]] = {}
        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in {".py", ".js", ".ts", ".tsx", ".jsx"}:
                continue
            result = analyze_dependencies(str(file_path))
            dependencies[str(file_path)] = result.get("imports", [])
        return {"dependencies": dependencies}


