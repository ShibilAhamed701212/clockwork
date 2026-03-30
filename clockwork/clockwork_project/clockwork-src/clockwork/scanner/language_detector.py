from __future__ import annotations

from pathlib import Path


_EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
}


def detect_language(file_path: str) -> str:
    return _EXT_MAP.get(Path(file_path).suffix.lower(), "Other")


class LanguageDetector:
    """Compatibility wrapper that summarizes language distribution for file lists."""

    def __init__(self, files: list[str]) -> None:
        self.files = files

    def detect(self) -> dict:
        counts: dict[str, int] = {}
        for file_path in self.files:
            language = detect_language(file_path)
            counts[language] = counts.get(language, 0) + 1
        primary = "Other"
        if counts:
            primary = max(counts, key=counts.get)
        return {"languages": counts, "primary": primary}


