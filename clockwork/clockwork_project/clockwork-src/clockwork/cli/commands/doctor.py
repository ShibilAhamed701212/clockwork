"""
clockwork/cli/commands/doctor.py
----------------------------------
`clockwork doctor` — diagnose Clockwork installation and project health.

Checks:
  • Python version compatibility
  • Required dependencies installed
  • Optional dependencies (watchdog, networkx, mcp, ollama)
  • .clockwork directory integrity
  • context.yaml validity
  • Graph/index freshness
"""

from __future__ import annotations

import importlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header, success, info, warn, error, rule, json_output,
)


def cmd_doctor(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository.",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Diagnose Clockwork installation and project health.

    Checks Python version, dependencies, project integrity, and freshness.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    checks: list[dict] = []

    # ── Python version ────────────────────────────────────────────────────
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 10)
    checks.append({
        "name": "Python version",
        "status": "ok" if py_ok else "fail",
        "detail": py_version,
        "fix": None if py_ok else "Requires Python 3.10+",
    })

    # ── Required dependencies ─────────────────────────────────────────────
    required_deps = [
        ("typer", "typer"),
        ("yaml", "pyyaml"),
        ("git", "gitpython"),
    ]
    all_required_ok = True
    for mod_name, pkg_name in required_deps:
        try:
            importlib.import_module(mod_name)
            checks.append({
                "name": f"Dependency: {pkg_name}",
                "status": "ok",
                "detail": "installed",
                "fix": None,
            })
        except ImportError:
            all_required_ok = False
            checks.append({
                "name": f"Dependency: {pkg_name}",
                "status": "fail",
                "detail": "not installed",
                "fix": f"pip install {pkg_name}",
            })

    if all_required_ok:
        checks.append({
            "name": "All required deps",
            "status": "ok",
            "detail": "installed",
            "fix": None,
        })

    # ── Optional dependencies ─────────────────────────────────────────────
    optional_deps = [
        ("watchdog", "watchdog", "real-time watching"),
        ("networkx", "networkx", "knowledge graph"),
        ("mcp", "mcp", "MCP server"),
    ]
    for mod_name, pkg_name, feature in optional_deps:
        try:
            importlib.import_module(mod_name)
            checks.append({
                "name": f"Optional: {pkg_name}",
                "status": "ok",
                "detail": f"{feature} available",
                "fix": None,
            })
        except ImportError:
            checks.append({
                "name": f"Optional: {pkg_name}",
                "status": "warn",
                "detail": f"{feature} disabled",
                "fix": f"pip install {pkg_name}",
            })

    # ── Ollama availability ───────────────────────────────────────────────
    ollama_running = _check_ollama()
    if ollama_running:
        checks.append({
            "name": "Ollama",
            "status": "ok",
            "detail": "running (AI brain available)",
            "fix": None,
        })
    else:
        checks.append({
            "name": "Ollama",
            "status": "warn",
            "detail": "not running (AI brain disabled)",
            "fix": "Install from https://ollama.ai",
        })

    # ── GitPython availability ────────────────────────────────────────────
    git_available = _check_git(root)
    if git_available:
        checks.append({
            "name": "Git repository",
            "status": "ok",
            "detail": "detected",
            "fix": None,
        })
    else:
        checks.append({
            "name": "Git repository",
            "status": "warn",
            "detail": "not a git repository",
            "fix": "git init",
        })

    # ── .clockwork directory ──────────────────────────────────────────────
    if cw_dir.is_dir():
        checks.append({
            "name": ".clockwork initialized",
            "status": "ok",
            "detail": "found",
            "fix": None,
        })
    else:
        checks.append({
            "name": ".clockwork initialized",
            "status": "fail",
            "detail": "not found",
            "fix": "clockwork init",
        })

    # ── context.yaml validity ─────────────────────────────────────────────
    if cw_dir.is_dir():
        ctx_check = _check_context(cw_dir)
        checks.append(ctx_check)

    # ── Graph freshness ───────────────────────────────────────────────────
    if cw_dir.is_dir():
        graph_check = _check_freshness(cw_dir / "knowledge_graph.db", "Knowledge graph", "clockwork graph build")
        checks.append(graph_check)

    # ── Index freshness ───────────────────────────────────────────────────
    if cw_dir.is_dir():
        index_check = _check_freshness(cw_dir / "live_index.db", "Index", "clockwork index")
        checks.append(index_check)

    # ── Output ────────────────────────────────────────────────────────────
    if as_json:
        json_output({"checks": checks})
        return

    header("Clockwork Doctor")

    for check in checks:
        status = check["status"]
        name = check["name"]
        detail = check["detail"]
        fix = check.get("fix")

        if status == "ok":
            success(f"{name}: {detail}")
        elif status == "warn":
            warn(f"{name}: {detail}")
            if fix:
                info(f"    Fix: {fix}")
        else:
            error(f"{name}: {detail}")
            if fix:
                info(f"    Fix: {fix}")

    rule()

    ok_count = sum(1 for c in checks if c["status"] == "ok")
    warn_count = sum(1 for c in checks if c["status"] == "warn")
    fail_count = sum(1 for c in checks if c["status"] == "fail")

    if fail_count:
        error(f"{fail_count} issue(s) need attention")
    elif warn_count:
        info(f"All good with {warn_count} advisory note(s)")
    else:
        success("All checks passed")


# ── Check helpers ─────────────────────────────────────────────────────────

def _check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def _check_git(root: Path) -> bool:
    """Check if directory is a git repo."""
    try:
        import git
        git.Repo(root)
        return True
    except Exception:
        return False


def _check_context(cw_dir: Path) -> dict:
    """Validate context.yaml."""
    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        return {"name": "context.yaml", "status": "fail", "detail": "missing", "fix": "clockwork init"}
    try:
        import yaml
        data = yaml.safe_load(ctx_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"name": "context.yaml", "status": "fail", "detail": "invalid format", "fix": "clockwork init --force"}
        return {"name": "context.yaml", "status": "ok", "detail": "valid", "fix": None}
    except Exception as exc:
        return {"name": "context.yaml", "status": "fail", "detail": f"parse error: {exc}", "fix": "clockwork init --force"}


def _check_freshness(path: Path, name: str, fix_cmd: str) -> dict:
    """Check how old a file is and warn if stale."""
    if not path.exists():
        return {"name": name, "status": "warn", "detail": "not built", "fix": fix_cmd}
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - mtime).total_seconds() / 3600
        if age_hours > 24:
            return {
                "name": name,
                "status": "warn",
                "detail": f"{age_hours:.0f}h old",
                "fix": fix_cmd,
            }
        return {"name": name, "status": "ok", "detail": f"built {age_hours:.0f}h ago", "fix": None}
    except Exception:
        return {"name": name, "status": "warn", "detail": "unknown age", "fix": fix_cmd}
