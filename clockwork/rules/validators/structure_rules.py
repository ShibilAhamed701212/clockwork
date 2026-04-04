from __future__ import annotations

from pathlib import Path


class StructureRules:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()

    def validate_structure(self) -> tuple[bool, list[str]]:
        issues: list[str] = []
        if not (self.repo_root / ".clockwork").exists():
            issues.append("Missing .clockwork directory")
        if not (self.repo_root / "clockwork").exists() and not (self.repo_root / "src").exists():
            issues.append("No recognizable source directory found")
        return len(issues) == 0, issues

