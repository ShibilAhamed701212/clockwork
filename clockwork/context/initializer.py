"""
Clockwork Context Initializer
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any
import yaml

logger = logging.getLogger(__name__)

CLOCKWORK_DIR = ".clockwork"
CONTEXT_FILE = "context.yaml"
CONTEXT_VERSION = 1

_EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".go": "go", ".rb": "ruby", ".java": "java", ".rs": "rust",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c",
}

_FRAMEWORK_HINTS = [
    ("flask", "Flask"), ("django", "Django"), ("fastapi", "FastAPI"),
    ("react", "React"), ("vue", "Vue"), ("express", "Express"),
    ("sqlalchemy", "SQLAlchemy"), ("celery", "Celery"),
    ("typer", "Typer"), ("click", "Click"),
]

class ContextInitializer:
    def __init__(self, repo_root="."): 
        self.repo_root = Path(repo_root).resolve()
        self.clockwork_dir = self.repo_root / CLOCKWORK_DIR
        self.context_path = self.clockwork_dir / CONTEXT_FILE

    def initialize(self):
        project_name = self.repo_root.name
        languages = self._detect_languages()
        frameworks = self._detect_frameworks()
        architecture = self._infer_architecture()
        skills = list(languages.keys()) + [f for f in frameworks if f not in languages]

        context = {
            "clockwork_context_version": CONTEXT_VERSION,
            "project": {"name": project_name, "type": "unknown", "version": "0.1"},
            "repository": {"architecture": architecture, "languages": languages},
            "frameworks": frameworks,
            "current_state": {
                "summary": "Initial repository scan complete.",
                "next_task": "Define first development task.",
                "blockers": [],
            },
            "skills_required": skills,
        }
        self._persist(context)
        return context

    def _detect_languages(self):
        counts = {}
        ignore_dirs = {".git", ".clockwork", "__pycache__", "node_modules", ".venv", "venv"}
        for path in self.repo_root.rglob("*"):
            if any(part in ignore_dirs for part in path.parts):
                continue
            if path.is_file() and path.suffix in _EXT_TO_LANG:
                lang = _EXT_TO_LANG[path.suffix]
                counts[lang] = counts.get(lang, 0) + 1
        if not counts:
            return {}
        total = sum(counts.values())
        return {lang: round(count / total * 100) for lang, count in sorted(counts.items(), key=lambda x: -x[1])}

    def _detect_frameworks(self):
        dep_text = self._read_dependency_files()
        found, seen = [], set()
        for fragment, label in _FRAMEWORK_HINTS:
            if fragment in dep_text and label not in seen:
                found.append(label)
                seen.add(label)
        return found

    def _infer_architecture(self):
        subdirs = {p.name for p in self.repo_root.iterdir() if p.is_dir()}
        if {"frontend", "backend", "api"}.intersection(subdirs): return "fullstack"
        if {"services", "microservices"}.intersection(subdirs): return "microservices"
        if {"src", "lib", "pkg"}.intersection(subdirs): return "layered"
        if (self.repo_root / "pyproject.toml").exists(): return "python_package"
        return "flat"

    def _read_dependency_files(self):
        parts = []
        for name in ["requirements.txt", "pyproject.toml", "package.json", "Pipfile", "setup.cfg"]:
            path = self.repo_root / name
            if path.exists():
                try: parts.append(path.read_text(encoding="utf-8").lower())
                except OSError: pass
        return "\n".join(parts)

    def _persist(self, context):
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.context_path.with_suffix(".yaml.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                yaml.dump(context, fh, default_flow_style=False, allow_unicode=True)
            tmp.replace(self.context_path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Cannot write context file: {exc}") from exc

def initialize_clockwork_dir(repo_root: str = '.', force: bool = False) -> dict:
    """Convenience wrapper around ContextInitializer.initialize()."""
    return ContextInitializer(repo_root).initialize()
