"""
clockwork/cli/commands/scan.py
--------------------------------
`clockwork scan` — analyse repository structure and write repo_map.json.

The scanner walks the repository tree, detects languages, counts files,
identifies entry points, and stores results in .clockwork/repo_map.json.

When the full Repository Scanner subsystem (clockwork/scanner/) is
implemented it will be called here.  Until then this module provides a
self-contained implementation that satisfies the spec and produces a
well-structured repo_map.json.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, result_block, rule, json_output,
)

# ── Language detection by extension ───────────────────────────────────────

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py":    "Python",
    ".js":    "JavaScript",
    ".ts":    "TypeScript",
    ".jsx":   "JavaScript",
    ".tsx":   "TypeScript",
    ".go":    "Go",
    ".rs":    "Rust",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".cs":    "C#",
    ".cpp":   "C++",
    ".c":     "C",
    ".h":     "C/C++ Header",
    ".html":  "HTML",
    ".css":   "CSS",
    ".scss":  "SCSS",
    ".yaml":  "YAML",
    ".yml":   "YAML",
    ".json":  "JSON",
    ".md":    "Markdown",
    ".sh":    "Shell",
    ".bash":  "Shell",
    ".sql":   "SQL",
    ".tf":    "Terraform",
    ".toml":  "TOML",
    ".xml":   "XML",
    ".dart":  "Dart",
    ".swift": "Swift",
}

SENSITIVE_FILES: set[str] = {
    ".env", ".env.local", ".env.production",
    "credentials.json", "secrets.json", "secret.json",
    ".netrc", "id_rsa", "id_ed25519",
}

DEFAULT_IGNORE_DIRS: set[str] = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
    "eggs", "*.egg-info",
}


# ── Command ────────────────────────────────────────────────────────────────

def cmd_scan(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Analyse repository structure and write .clockwork/repo_map.json.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Scan")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    # Load config for ignore rules (used by fallback scanner)
    ignore_dirs = _load_ignore_dirs(cw_dir)

    start = time.perf_counter()

    if not as_json:
        step("Walking repository tree...")

    # Prefer the full RepositoryScanner subsystem; fall back to inline scanner
    try:
        from clockwork.scanner import RepositoryScanner
        scanner = RepositoryScanner(repo_root=root, verbose=False)
        result = scanner.scan()
        output_path = result.save(cw_dir)
        repo_map = result.to_dict()
    except Exception:
        repo_map = _scan_repository(root, ignore_dirs)
        output_path = cw_dir / "repo_map.json"
        output_path.write_text(
            json.dumps(repo_map, indent=2, default=str),
            encoding="utf-8",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    if as_json:
        json_output(repo_map)
        return

    # Human-readable summary
    languages = repo_map.get("languages", {})
    total_files = repo_map.get("total_files", 0)

    rule()
    success(f"Scan complete in {elapsed_ms:.0f} ms")
    info(f"Total files scanned : {total_files}")
    info(f"Output              : .clockwork/repo_map.json")

    if languages:
        result_block(
            "Detected languages",
            [f"{lang}  ({count} files)" for lang, count in
             sorted(languages.items(), key=lambda x: -x[1])]
        )

    if repo_map.get("entry_points"):
        result_block("Entry points", repo_map["entry_points"])

    info("\nNext step: run  clockwork update")


# ── Scanner implementation ─────────────────────────────────────────────────

def _load_ignore_dirs(cw_dir: Path) -> set[str]:
    """Load ignore_dirs from config.yaml, falling back to defaults."""
    config_path = cw_dir / "config.yaml"
    try:
        if config_path.exists():
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            dirs = cfg.get("scanner", {}).get("ignore_dirs", [])
            return DEFAULT_IGNORE_DIRS | set(dirs)
    except Exception:
        pass
    return DEFAULT_IGNORE_DIRS


def _scan_repository(root: Path, ignore_dirs: set[str]) -> dict:
    """
    Walk *root*, collect file metadata, detect languages, find entry points.
    Returns a repo_map dict ready for JSON serialisation.
    """
    language_counts: dict[str, int] = defaultdict(int)
    all_files: list[dict] = []
    entry_points: list[str] = []
    dir_tree: dict[str, list[str]] = defaultdict(list)

    for path in sorted(root.rglob("*")):
        # Skip ignored directories
        if any(part in ignore_dirs for part in path.parts):
            continue

        # Skip sensitive filenames
        if path.name.lower() in SENSITIVE_FILES:
            continue

        if not path.is_file():
            continue

        rel = str(path.relative_to(root))
        ext = path.suffix.lower()
        language = EXTENSION_LANGUAGE_MAP.get(ext, "Other")

        if language != "Other":
            language_counts[language] += 1

        try:
            size_bytes = path.stat().st_size
        except OSError:
            size_bytes = 0

        file_entry: dict = {
            "path": rel,
            "extension": ext,
            "language": language,
            "size_bytes": size_bytes,
        }
        all_files.append(file_entry)

        # Track per-directory members
        dir_tree[str(path.parent.relative_to(root))].append(path.name)

        # Detect common entry points
        if _is_entry_point(path, root):
            entry_points.append(rel)

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "total_files": len(all_files),
        "languages": dict(sorted(language_counts.items(), key=lambda x: -x[1])),
        "entry_points": entry_points,
        "files": all_files,
        "directory_tree": {k: v for k, v in sorted(dir_tree.items())},
    }


def _is_entry_point(path: Path, root: Path) -> bool:
    """Heuristic detection of repository entry points."""
    name = path.name.lower()
    entry_point_names = {
        "main.py", "app.py", "server.py", "run.py", "manage.py",
        "index.js", "index.ts", "main.js", "main.ts",
        "main.go", "main.rs", "main.java",
        "pyproject.toml", "package.json", "go.mod", "cargo.toml",
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile",
    }
    return name in entry_point_names
