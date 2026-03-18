"""
clockwork/cli/commands/init.py
--------------------------------
`clockwork init` — initialise Clockwork inside a repository.

Responsibilities (spec §4):
  • create .clockwork/ directory
  • write context.yaml   (project context template)
  • write rules.md       (rule definitions template)
  • write config.yaml    (runtime configuration)
  • write tasks.json     (empty task list)
  • write skills.json    (empty skill registry)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule
)

# ── Default file contents ──────────────────────────────────────────────────

_CONTEXT_YAML = """\
# Clockwork Project Context
# -------------------------
# Maintained by: clockwork update
# Do not edit manually unless you know what you are doing.

clockwork_version: "0.1"
memory_schema_version: 1
project_name: "{project_name}"
created_at: "{created_at}"

summary: ""
architecture_overview: ""
primary_language: ""
frameworks: []
entry_points: []

current_tasks: []
recent_changes: []
"""

_RULES_MD = """\
# Clockwork Rule Definitions
# ---------------------------
# Add project-specific rules below.
# Rules are evaluated by the Rule Engine during `clockwork verify`.

## Architecture Rules

- Do not bypass the API layer.
- Do not modify database schema without a migration script.
- Do not remove core modules without explicit approval.

## File Protection Rules

- .clockwork/ must not be deleted.
- pyproject.toml must not be modified by automated agents without review.

## Naming Rules

- Python modules must use snake_case.
- Classes must use PascalCase.
"""

_CONFIG_YAML = """\
# Clockwork Runtime Configuration
# ---------------------------------

brain:
  mode: minibrain

scanner:
  ignore_dirs:
    - .git
    - __pycache__
    - node_modules
    - .venv
    - dist
    - build
  ignore_extensions:
    - .pyc
    - .pyo

packaging:
  auto_snapshot: false

logging:
  level: info
"""

_TASKS_JSON = json.dumps([], indent=2)
_SKILLS_JSON = json.dumps([], indent=2)
_AGENT_HISTORY_JSON = json.dumps([], indent=2)


# ── Command ────────────────────────────────────────────────────────────────

def cmd_init(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Re-initialise even if .clockwork/ already exists.",
    ),
) -> None:
    """
    Initialise Clockwork inside a repository.

    Creates the .clockwork/ directory and all required template files.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Init")

    if cw_dir.exists() and not force:
        warn("Clockwork is already initialised in this repository.")
        info("Use --force to re-initialise.")
        raise typer.Exit(code=0)

    try:
        _create_clockwork_dir(cw_dir, project_name=root.name)
    except OSError as exc:
        error(str(exc))
        raise typer.Exit(code=1)

    rule()
    success(f"Clockwork initialised in {root}")
    info(f"Directory: {cw_dir}")
    info("Next step: run  clockwork scan")


def _create_clockwork_dir(cw_dir: Path, project_name: str) -> None:
    """Create .clockwork/ and write all template files."""
    created_at = datetime.now(timezone.utc).isoformat()

    files: dict[str, str] = {
        "context.yaml": _CONTEXT_YAML.format(
            project_name=project_name,
            created_at=created_at,
        ),
        "rules.md": _RULES_MD,
        "config.yaml": _CONFIG_YAML,
        "tasks.json": _TASKS_JSON,
        "skills.json": _SKILLS_JSON,
        "agent_history.json": _AGENT_HISTORY_JSON,
    }

    # Sub-directories
    for sub in ("handoff", "packages", "plugins", "logs"):
        (cw_dir / sub).mkdir(parents=True, exist_ok=True)
        step(f"Created  .clockwork/{sub}/")

    for filename, content in files.items():
        dest = cw_dir / filename
        dest.write_text(content, encoding="utf-8")
        step(f"Created  .clockwork/{filename}")
