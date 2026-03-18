"""
clockwork/index/incremental_scanner.py
----------------------------------------
Incremental file scanner for the Live Context Index.

Instead of rescanning the entire repository, this module scans
only a single changed file and returns its metadata — feeding
the index storage and graph updater.

Spec §6 pipeline:
    File Modified → Incremental Parser → Dependency Update → Graph Update
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from .models import IndexEntry, compute_file_hash


# ── Language detection ─────────────────────────────────────────────────────

_EXT_LANGUAGE: dict[str, str] = {
    ".py":   "Python",   ".js":  "JavaScript", ".ts":  "TypeScript",
    ".jsx":  "JavaScript", ".tsx": "TypeScript", ".go":  "Go",
    ".rs":   "Rust",     ".java": "Java",       ".rb":  "Ruby",
    ".php":  "PHP",      ".cs":   "C#",         ".cpp": "C++",
    ".c":    "C",        ".h":    "C/C++ Header",
    ".yaml": "YAML",     ".yml":  "YAML",       ".json": "JSON",
    ".md":   "Markdown", ".toml": "TOML",       ".sh":  "Shell",
    ".sql":  "SQL",
}

_MODULE_TYPE_RULES = [
    (lambda p: "test" in p.lower() or p.endswith("_test.py"), "test"),
    (lambda p: p.endswith((".yaml", ".yml", ".toml", ".json", ".cfg", ".ini")), "config"),
    (lambda p: p.endswith((".py", ".js", ".ts", ".go", ".rs", ".java")), "source"),
]

_LAYER_PATTERNS: dict[str, list[str]] = {
    "frontend":       ["frontend", "ui", "client", "web", "static", "public"],
    "backend":        ["backend", "server", "api", "app", "core", "services"],
    "database":       ["database", "db", "models", "migrations", "schema"],
    "infrastructure": ["infra", "infrastructure", "devops", "docker", "scripts"],
    "tests":          ["tests", "test", "spec"],
}

_SENSITIVE = {".env", "credentials.json", "secrets.json", ".netrc", "id_rsa"}


class IncrementalScanner:
    """
    Scans a single file and returns an IndexEntry.

    All analysis is purely static — no code is executed (spec §16).
    """

    def scan_file(self, file_path: str, repo_root: str) -> Optional[IndexEntry]:
        """
        Scan one file and return an IndexEntry, or None if the file
        should be skipped (binary, sensitive, or non-existent).
        """
        abs_path = Path(file_path)
        if not abs_path.exists() or not abs_path.is_file():
            return None

        filename = abs_path.name
        if filename in _SENSITIVE or filename.startswith(".env"):
            return None

        # relative path for storage
        try:
            rel_path = str(abs_path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(abs_path).replace("\\", "/")

        ext      = abs_path.suffix.lower()
        language = _EXT_LANGUAGE.get(ext, "Other")
        mtime    = abs_path.stat().st_mtime
        size     = abs_path.stat().st_size
        fhash    = compute_file_hash(file_path)
        layer    = _detect_layer(rel_path)
        mod_type = _detect_module_type(rel_path)
        deps     = self._extract_dependencies(abs_path, language)

        return IndexEntry(
            file_path=rel_path,
            last_modified=mtime,
            file_hash=fhash,
            size_bytes=size,
            language=language,
            module_type=mod_type,
            dependencies=json.dumps(deps),
            layer=layer,
        )

    # ── dependency extraction ──────────────────────────────────────────────

    def _extract_dependencies(self, path: Path, language: str) -> list[str]:
        """Extract import strings from a source file (static only)."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        if language == "Python":
            return self._python_imports(content)
        if language in ("JavaScript", "TypeScript"):
            return self._js_imports(content)
        if language == "Go":
            return self._go_imports(content)
        return []

    def _python_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            # fallback: regex
            for m in re.finditer(r"^\s*(?:import|from)\s+([\w.]+)", source, re.MULTILINE):
                imports.append(m.group(1))
        return list(dict.fromkeys(imports))  # deduplicate, preserve order

    def _js_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        for m in re.finditer(
            r"""(?:import|require)\s*[\(\s]['"]([^'"]+)['"]""", source
        ):
            imports.append(m.group(1))
        return list(dict.fromkeys(imports))

    def _go_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        block = re.search(r'import\s*\(([^)]+)\)', source, re.DOTALL)
        if block:
            for m in re.finditer(r'"([^"]+)"', block.group(1)):
                imports.append(m.group(1))
        for m in re.finditer(r'^\s*import\s+"([^"]+)"', source, re.MULTILINE):
            imports.append(m.group(1))
        return list(dict.fromkeys(imports))


# ── helpers ────────────────────────────────────────────────────────────────

def _detect_layer(rel_path: str) -> str:
    norm = rel_path.lower()
    for layer, keywords in _LAYER_PATTERNS.items():
        for kw in keywords:
            if f"/{kw}/" in norm or norm.startswith(kw + "/"):
                return layer
    if "test" in norm:
        return "tests"
    return "backend"


def _detect_module_type(rel_path: str) -> str:
    for rule, kind in _MODULE_TYPE_RULES:
        if rule(rel_path):
            return kind
    return "other"

