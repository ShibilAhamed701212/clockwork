"""
clockwork/scanner/language.py
-------------------------------
Language detection for repository files.

Detection strategy (in order of priority):
  1. Exact filename match  (e.g. Makefile, Dockerfile)
  2. File extension match
  3. Shebang line sniff    (#!/usr/bin/env python3)
  4. Content heuristics    (fallback)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


# ── Extension → language map ───────────────────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    # Python
    ".py": "Python", ".pyi": "Python", ".pyw": "Python",
    # JavaScript / TypeScript
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    # Web
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS", ".less": "LESS",
    # Data / Config
    ".json": "JSON", ".jsonc": "JSON",
    ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".ini": "INI", ".cfg": "INI", ".conf": "INI",
    ".xml": "XML", ".xsd": "XML", ".xsl": "XML",
    ".env": "ENV",
    # Systems
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala",
    ".swift": "Swift",
    ".m": "Objective-C",
    # Scripting
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".rb": "Ruby", ".erb": "Ruby",
    ".php": "PHP",
    ".pl": "Perl", ".pm": "Perl",
    ".lua": "Lua",
    ".r": "R", ".R": "R",
    # Data science
    ".ipynb": "Jupyter",
    # Infrastructure
    ".tf": "Terraform", ".tfvars": "Terraform",
    ".dockerfile": "Dockerfile",
    # Docs
    ".md": "Markdown", ".mdx": "Markdown",
    ".rst": "reStructuredText",
    ".tex": "LaTeX",
    # DB
    ".sql": "SQL",
    # Other
    ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".clj": "Clojure",
    ".groovy": "Groovy",
    ".gradle": "Groovy",
    ".proto": "Protobuf",
    ".graphql": "GraphQL", ".gql": "GraphQL",
}

# Exact filename → language (case-insensitive)
FILENAME_MAP: dict[str, str] = {
    "makefile": "Makefile",
    "dockerfile": "Dockerfile",
    "jenkinsfile": "Groovy",
    "vagrantfile": "Ruby",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "procfile": "Config",
    "brewfile": "Ruby",
    ".gitignore": "Config",
    ".gitattributes": "Config",
    ".editorconfig": "Config",
    ".npmrc": "Config",
    ".yarnrc": "Config",
    ".babelrc": "JSON",
    ".eslintrc": "JSON",
    ".prettierrc": "JSON",
    "pyproject.toml": "TOML",
    "cargo.toml": "TOML",
    "go.mod": "Go",
    "go.sum": "Go",
    "requirements.txt": "Config",
    "pipfile": "TOML",
    "setup.py": "Python",
    "setup.cfg": "INI",
    "tox.ini": "INI",
    "conftest.py": "Python",
}

# Shebang prefixes → language
SHEBANG_MAP: dict[str, str] = {
    "python": "Python",
    "python3": "Python",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "ruby": "Ruby",
    "perl": "Perl",
    "php": "PHP",
    "lua": "Lua",
    "rscript": "R",
}


class LanguageDetector:
    """
    Detects the programming language of a single file using a multi-strategy
    approach.  All analysis is static — no code is executed.
    """

    def detect(self, path: Path) -> str:
        """
        Return the detected language name for *path*.

        Returns ``"Other"`` when no match is found.
        """
        # 1. Exact filename
        name_lower = path.name.lower()
        if name_lower in FILENAME_MAP:
            return FILENAME_MAP[name_lower]

        # 2. Extension
        ext = path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        # 3. No extension — try shebang
        if not ext:
            lang = self._detect_shebang(path)
            if lang:
                return lang

        return "Other"

    def _detect_shebang(self, path: Path) -> Optional[str]:
        """Read the first line and check for a shebang."""
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                first_line = fh.readline(200).strip()
        except OSError:
            return None

        if not first_line.startswith("#!"):
            return None

        # e.g.  #!/usr/bin/env python3  or  #!/bin/bash
        parts = first_line[2:].strip().split()
        if not parts:
            return None

        interpreter = parts[-1].lower()   # handle /usr/bin/env python3
        interpreter_base = Path(interpreter).name

        return SHEBANG_MAP.get(interpreter_base)

    # ------------------------------------------------------------------ #
    # Bulk helpers
    # ------------------------------------------------------------------ #

    def detect_primary_language(self, language_counts: dict[str, int]) -> str:
        """
        Return the language with the highest file count.

        Config/data languages (YAML, JSON, TOML, Markdown, INI, Config, Other)
        are deprioritised so the primary code language surfaces.
        """
        NON_CODE = {"YAML", "JSON", "TOML", "Markdown", "INI", "Config",
                    "Other", "ENV", "reStructuredText", "LaTeX", "XML"}

        code_langs = {k: v for k, v in language_counts.items() if k not in NON_CODE}
        if code_langs:
            return max(code_langs, key=lambda k: code_langs[k])

        if language_counts:
            return max(language_counts, key=lambda k: language_counts[k])

        return ""

    @staticmethod
    def extension_for(language: str) -> list[str]:
        """Return all file extensions associated with *language*."""
        return [ext for ext, lang in EXTENSION_MAP.items() if lang == language]
