"""
clockwork/cli/commands/update.py
----------------------------------
`clockwork update` — merge scanner results into context.yaml.

Reads .clockwork/repo_map.json and updates the fields inside
.clockwork/context.yaml that can be derived automatically:

  • primary_language
  • frameworks   (detected from dependency manifests)
  • entry_points
  • recent changes timestamp
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule,
)

# ── Framework fingerprints ─────────────────────────────────────────────────

# Maps a filename to the frameworks it implies when present in the repo root.
FRAMEWORK_FINGERPRINTS: dict[str, list[str]] = {
    "pyproject.toml": [],      # read dynamically
    "requirements.txt": [],    # read dynamically
    "package.json": [],        # read dynamically
    "go.mod": ["Go Modules"],
    "cargo.toml": ["Rust / Cargo"],
    "pom.xml": ["Maven / Java"],
    "build.gradle": ["Gradle / JVM"],
    "dockerfile": ["Docker"],
    "docker-compose.yml": ["Docker Compose"],
    "docker-compose.yaml": ["Docker Compose"],
    ".github": ["GitHub Actions"],
}

PYTHON_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "typer": "Typer", "click": "Click", "starlette": "Starlette",
    "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic",
    "pytest": "pytest", "celery": "Celery",
}

JS_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "react": "React", "vue": "Vue", "angular": "Angular",
    "next": "Next.js", "nuxt": "Nuxt", "express": "Express",
    "fastify": "Fastify", "svelte": "Svelte",
}


# ── Command ────────────────────────────────────────────────────────────────

def cmd_update(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
) -> None:
    """
    Merge scanner results into .clockwork/context.yaml.

    Run after `clockwork scan` to keep project context current.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Update")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    repo_map_path = cw_dir / "repo_map.json"
    if not repo_map_path.exists():
        error("repo_map.json not found.\nRun:  clockwork scan")
        raise typer.Exit(code=1)

    context_path = cw_dir / "context.yaml"
    if not context_path.exists():
        error("context.yaml not found.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    try:
        repo_map: dict = json.loads(repo_map_path.read_text(encoding="utf-8"))
        context: dict = yaml.safe_load(context_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        error(f"Failed to read project files: {exc}")
        raise typer.Exit(code=1)

    step("Deriving primary language...")
    primary_language = _derive_primary_language(repo_map)

    step("Detecting frameworks...")
    frameworks = _detect_frameworks(root, repo_map)

    step("Collecting entry points...")
    entry_points = repo_map.get("entry_points", [])

    # Prefer ContextEngine + ScanResult for merge; fall back to raw dict merge
    try:
        from clockwork.context import ContextEngine
        from clockwork.scanner.models import ScanResult
        scan_result = ScanResult.load(cw_dir)
        engine = ContextEngine(cw_dir)
        context_obj = engine.merge_scan(scan_result)
        primary_language = context_obj.primary_language
        frameworks = list(context_obj.frameworks)
        entry_points = list(context_obj.entry_points)
    except Exception:
        # Fallback: manual raw-dict merge
        context["primary_language"] = primary_language
        context["frameworks"] = sorted(set(frameworks))
        context["entry_points"] = entry_points
        context["last_updated"] = datetime.now(timezone.utc).isoformat()
        context["total_files"] = repo_map.get("total_files", 0)
        context["languages"] = repo_map.get("languages", {})
        try:
            context_path.write_text(
                yaml.dump(context, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            error(f"Failed to write context.yaml: {exc}")
            raise typer.Exit(code=1)

    rule()
    success("context.yaml updated")
    info(f"  Primary language : {primary_language or '(unknown)'}")
    info(f"  Frameworks       : {', '.join(frameworks) or '(none detected)'}")
    info(f"  Entry points     : {len(entry_points)}")
    info("\nNext step: run  clockwork verify")


# ── Derivation helpers ─────────────────────────────────────────────────────

def _derive_primary_language(repo_map: dict) -> str:
    """Return the language with the most files, or empty string."""
    languages = repo_map.get("languages", {})
    if not languages:
        return ""
    # Support both dict {lang: count} and legacy list [lang, ...]
    if isinstance(languages, list):
        return languages[0] if languages else ""
    return max(languages, key=lambda k: languages[k])


def _detect_frameworks(root: Path, repo_map: dict) -> list[str]:
    """Heuristically detect frameworks used in the repository."""
    detected: list[str] = []
    files_in_root = {
        p["path"].lower().replace("\\", "/")
        for p in repo_map.get("files", [])
        if "/" not in p["path"].replace("\\", "/")   # only root-level files
    }

    # Static fingerprints
    for filename, frameworks in FRAMEWORK_FINGERPRINTS.items():
        if filename in files_in_root:
            detected.extend(frameworks)

    # Python: parse requirements.txt / pyproject.toml
    if "requirements.txt" in files_in_root:
        detected.extend(_parse_requirements(root / "requirements.txt"))

    if "pyproject.toml" in files_in_root:
        detected.extend(_parse_pyproject(root / "pyproject.toml"))

    # JS: parse package.json
    if "package.json" in files_in_root:
        detected.extend(_parse_package_json(root / "package.json"))

    return list(dict.fromkeys(detected))  # deduplicate, preserve order


def _parse_requirements(path: Path) -> list[str]:
    """Scan requirements.txt for known framework names."""
    found: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            pkg = line.strip().lower().split("==")[0].split(">=")[0].split("[")[0]
            if pkg in PYTHON_FRAMEWORK_KEYWORDS:
                found.append(PYTHON_FRAMEWORK_KEYWORDS[pkg])
    except OSError:
        pass
    return found


def _parse_pyproject(path: Path) -> list[str]:
    """Scan pyproject.toml dependencies for known framework names (quoted form only)."""
    found: list[str] = []
    try:
        content = path.read_text(encoding="utf-8").lower()
        for keyword, name in PYTHON_FRAMEWORK_KEYWORDS.items():
            # Only match when the keyword appears as a dependency value (quoted)
            if f'"{keyword}' in content or f"'{keyword}" in content or f"\n{keyword}" in content:
                found.append(name)
    except OSError:
        pass
    return found


def _parse_package_json(path: Path) -> list[str]:
    """Scan package.json dependencies for known JS frameworks."""
    found: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        for pkg_name in all_deps:
            key = pkg_name.lstrip("@").split("/")[-1].lower()
            if key in JS_FRAMEWORK_KEYWORDS:
                found.append(JS_FRAMEWORK_KEYWORDS[key])
    except (OSError, json.JSONDecodeError):
        pass
    return found
