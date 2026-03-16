"""
clockwork/scanner/filters.py
------------------------------
Filtering rules for the Repository Scanner.

Determines which files and directories should be:
  • skipped entirely (ignored dirs, binary files, sensitive files)
  • flagged as sensitive and excluded from packages
  • classified as test / config / entry-point files
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import re


# ── Default ignore sets ────────────────────────────────────────────────────

DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "node_modules", ".npm", ".yarn",
    ".venv", "venv", "env", ".env_dir",
    "dist", "build", "target", "out", "bin", "obj",
    ".clockwork",
    ".idea", ".vscode", ".eclipse",
    "eggs", "*.egg-info",
    ".tox",
    "htmlcov", ".coverage",
    "site-packages",
})

DEFAULT_IGNORE_EXTENSIONS: frozenset[str] = frozenset({
    # Compiled / binary
    ".pyc", ".pyo", ".pyd",
    ".class", ".jar", ".war",
    ".o", ".obj", ".lib", ".a", ".so", ".dll", ".dylib", ".exe",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".whl", ".egg",
    # Media
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".ttf", ".woff", ".woff2", ".eot",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Database / lock
    ".db", ".sqlite", ".sqlite3",
    ".lock",   # package-lock.json excluded separately
    # IDE / OS
    ".DS_Store",
})

# Sensitive filenames — always excluded from packages, never indexed
SENSITIVE_FILENAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "credentials.json", "secrets.json", "secret.json",
    "service_account.json", "google_credentials.json",
    ".netrc", ".htpasswd",
    "id_rsa", "id_rsa.pub", "id_ed25519", "id_ed25519.pub",
    "id_dsa", "id_ecdsa",
})

SENSITIVE_EXTENSIONS: frozenset[str] = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".cer", ".crt",
})

# Entry-point filename heuristics
ENTRY_POINT_NAMES: frozenset[str] = frozenset({
    "main.py", "app.py", "server.py", "run.py", "manage.py",
    "wsgi.py", "asgi.py", "cli.py", "entrypoint.py",
    "index.js", "index.ts", "main.js", "main.ts",
    "app.js", "app.ts", "server.js", "server.ts",
    "main.go", "main.rs", "main.java", "Main.java",
    "main.c", "main.cpp",
    "program.cs",
})

# Dependency / config files of interest
DEPENDENCY_FILES: frozenset[str] = frozenset({
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "requirements-test.txt", "pipfile",
    "package.json", "yarn.lock", "package-lock.json",
    "go.mod", "go.sum",
    "cargo.toml", "cargo.lock",
    "pom.xml", "build.gradle", "settings.gradle",
    "gemfile", "gemfile.lock",
    "composer.json",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".github",
    "tox.ini", "pytest.ini", ".flake8", "mypy.ini",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json",
    "tsconfig.json", "jsconfig.json",
    "makefile", "cmakelists.txt",
})


# ── Classifier ────────────────────────────────────────────────────────────

class ScanFilter:
    """
    Encapsulates all filtering and classification logic for the scanner.

    Extra ignore dirs/extensions can be provided via config.yaml.
    """

    def __init__(
        self,
        extra_ignore_dirs: Optional[set[str]] = None,
        extra_ignore_extensions: Optional[set[str]] = None,
    ) -> None:
        self.ignore_dirs: frozenset[str] = (
            DEFAULT_IGNORE_DIRS | frozenset(extra_ignore_dirs or set())
        )
        self.ignore_extensions: frozenset[str] = (
            DEFAULT_IGNORE_EXTENSIONS | frozenset(extra_ignore_extensions or set())
        )

    # ------------------------------------------------------------------ #
    # Path-level decisions
    # ------------------------------------------------------------------ #

    def should_skip_directory(self, dir_path: Path, repo_root: Path) -> bool:
        """Return True if this directory should be ignored entirely."""
        for part in dir_path.relative_to(repo_root).parts:
            if part in self.ignore_dirs:
                return True
        return False

    def should_skip_file(self, file_path: Path) -> bool:
        """Return True if this file should be excluded from scanning."""
        name_lower = file_path.name.lower()
        ext_lower  = file_path.suffix.lower()

        # Sensitive
        if self.is_sensitive(file_path):
            return True

        # Extension-based ignore
        if ext_lower in self.ignore_extensions:
            return True

        # Hidden files (except common dotfiles we want)
        if name_lower.startswith(".") and name_lower not in {
            ".gitignore", ".editorconfig", ".eslintrc", ".prettierrc",
            ".babelrc", ".npmrc", ".yarnrc", ".flake8",
        }:
            return True

        return False

    # ------------------------------------------------------------------ #
    # Classification
    # ------------------------------------------------------------------ #

    def is_sensitive(self, file_path: Path) -> bool:
        """Return True if the file contains credentials or secrets."""
        name_lower = file_path.name.lower()
        ext_lower  = file_path.suffix.lower()
        return name_lower in SENSITIVE_FILENAMES or ext_lower in SENSITIVE_EXTENSIONS

    def is_entry_point(self, file_path: Path) -> bool:
        """Return True if the file looks like a repository entry point."""
        return file_path.name.lower() in ENTRY_POINT_NAMES

    def is_test_file(self, file_path: Path) -> bool:
        """Return True if the file appears to be a test file."""
        name = file_path.name.lower()
        parts = [p.lower() for p in file_path.parts]

        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.js")
            or name.endswith(".spec.ts")
            or "tests" in parts
            or "test" in parts
            or "__tests__" in parts
        )

    def is_config_file(self, file_path: Path) -> bool:
        """Return True if the file is a configuration / dependency file."""
        return file_path.name.lower() in DEPENDENCY_FILES

    def is_dependency_file(self, file_path: Path) -> bool:
        """Return True if the file declares project dependencies."""
        dep_names = {
            "pyproject.toml", "setup.py", "requirements.txt", "pipfile",
            "package.json", "go.mod", "cargo.toml", "pom.xml",
            "build.gradle", "gemfile",
        }
        return file_path.name.lower() in dep_names
