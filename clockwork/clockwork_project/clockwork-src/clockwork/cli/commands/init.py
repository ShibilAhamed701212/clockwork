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

clockwork_version: "0.2.0"
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

# Generated IDE/client integration artifacts are written here.
integration_output_dir: .clockwork/integrations
# Set true to also write legacy root files (CLAUDE.md, .cursorrules, ...).
legacy_root_integrations: false

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
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Run interactive setup wizard.",
    ),
    from_existing: bool = typer.Option(
        False, "--from-existing",
        help="Smart init: scan codebase and pre-fill context automatically.",
    ),
) -> None:
    """
    Initialise Clockwork inside a repository.

    Creates the .clockwork/ directory and all required template files.
    Use --interactive for a guided setup or --from-existing to auto-detect.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Init")

    if cw_dir.exists() and not force:
        warn("Clockwork is already initialised in this repository.")
        info("Use --force to re-initialise.")
        raise typer.Exit(code=0)

    # Interactive wizard
    ide_tools: list[str] = []
    if interactive:
        ide_tools = _run_interactive_wizard(root)

    try:
        _create_clockwork_dir(cw_dir, project_name=root.name)
    except OSError as exc:
        error(str(exc))
        raise typer.Exit(code=1)

    # Smart init: scan + summarize + generate IDE files
    if from_existing or interactive:
        _run_smart_init(root, cw_dir, ide_tools)

    rule()
    success(f"Clockwork initialised in {root}")
    info(f"Directory: {cw_dir}")
    if not (from_existing or interactive):
        info("Next step: run  clockwork scan")
    else:
        info("Next step: run  clockwork verify")


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
    for sub in ("handoff", "packages", "plugins", "logs", "integrations"):
        (cw_dir / sub).mkdir(parents=True, exist_ok=True)
        step(f"Created  .clockwork/{sub}/")

    for filename, content in files.items():
        dest = cw_dir / filename
        dest.write_text(content, encoding="utf-8")
        step(f"Created  .clockwork/{filename}")


# ── Interactive wizard ─────────────────────────────────────────────────────

def _run_interactive_wizard(root: Path) -> list[str]:
    """Run interactive setup prompts. Returns list of IDE tools selected."""
    info("")
    info("Welcome to Clockwork!")
    info("")

    # Project name
    detected_name = root.name
    project_name = typer.prompt("  Project name", default=detected_name)

    # Project type
    project_types = [
        "Web application (backend)",
        "Web application (frontend)",
        "CLI tool",
        "Library / package",
        "Full-stack application",
        "Data pipeline",
        "Other",
    ]
    info("\n  What kind of project is this?")
    for i, pt in enumerate(project_types, 1):
        info(f"    {i}. {pt}")
    type_choice = typer.prompt("  Select", default="3")
    try:
        selected_type = project_types[int(type_choice) - 1]
    except (ValueError, IndexError):
        selected_type = "Other"
    info(f"  → {selected_type}")

    # Primary language
    lang = _detect_primary_language(root)
    if lang:
        info(f"\n  Primary language detected: {lang}")
    else:
        lang = typer.prompt("  Primary language", default="Python")

    # AI tools
    ai_tools = ["Claude Code", "Cursor", "GitHub Copilot", "None"]
    info("\n  Which AI coding tools do you use?")
    for i, tool in enumerate(ai_tools, 1):
        info(f"    {i}. {tool}")
    tools_choice = typer.prompt("  Select (comma-separated)", default="1")

    selected_tools: list[str] = []
    for choice in tools_choice.split(","):
        try:
            idx = int(choice.strip()) - 1
            if 0 <= idx < len(ai_tools) and ai_tools[idx] != "None":
                selected_tools.append(ai_tools[idx])
        except (ValueError, IndexError):
            pass

    if selected_tools:
        info(f"  → {', '.join(selected_tools)}")

    info("")
    return selected_tools


def _detect_primary_language(root: Path) -> str:
    """Quick detection of primary language from file extensions."""
    ext_counts: dict[str, int] = {}
    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".go": "Go", ".java": "Java", ".rs": "Rust", ".rb": "Ruby",
        ".cpp": "C++", ".c": "C", ".cs": "C#",
    }
    try:
        for f in root.rglob("*"):
            if f.is_file() and not any(
                p in f.parts for p in (".git", "node_modules", ".venv", "__pycache__")
            ):
                ext = f.suffix.lower()
                if ext in lang_map:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
    except Exception:
        pass
    if ext_counts:
        top_ext = max(ext_counts, key=ext_counts.get)  # type: ignore[arg-type]
        return lang_map.get(top_ext, "")
    return ""


def _run_smart_init(root: Path, cw_dir: Path, ide_tools: list[str]) -> None:
    """Run scan, summarize, and generate IDE files after init."""
    # Run scan
    step("Running initial scan...")
    try:
        from clockwork.scanner.scanner import RepositoryScanner
        scanner = RepositoryScanner(repo_root=root, verbose=False)
        scan_result = scanner.scan()
        scan_result.save(cw_dir)
        success(f"Scanned {scan_result.total_files} files")

        # Record git scan point
        try:
            from clockwork.scanner.git_diff import GitDiffScanner
            git_scanner = GitDiffScanner(root)
            git_scanner.record_scan()
        except Exception:
            pass

    except Exception as exc:
        warn(f"Scan failed: {exc}")
        return

    # Update context with scan data
    step("Updating context...")
    try:
        from clockwork.context.engine import ContextEngine
        engine = ContextEngine(cw_dir)
        context_obj = engine.merge_scan(scan_result)

        # Summarize
        try:
            from clockwork.brain.summarizer import CodebaseSummarizer
            summarizer = CodebaseSummarizer()
            if not context_obj.summary:
                context_obj.summary = summarizer.summarize(scan_result)
            if not context_obj.architecture_overview:
                context_obj.architecture_overview = summarizer.architecture_overview(scan_result)
        except Exception:
            pass

        engine.save(context_obj)
        success("Context generated")
    except Exception as exc:
        warn(f"Context update failed: {exc}")

    # Generate IDE files
    if ide_tools:
        step("Generating IDE context files...")
        try:
            from clockwork.cli.commands.generate import generate_ide_files_auto
            tool_to_format = {
                "Claude Code": "claude-md",
                "Cursor": "cursorrules",
                "GitHub Copilot": "copilot",
            }
            formats = [tool_to_format[t] for t in ide_tools if t in tool_to_format]
            if formats:
                generated = generate_ide_files_auto(root, formats=formats)
                for g in generated:
                    success(f"Generated {Path(g).name}")
        except Exception:
            pass
    else:
        # Detect and import existing IDE context files
        existing_ide = []
        integration_dir = root / ".clockwork" / "integrations"
        candidates = [
            "CLAUDE.md",
            ".cursorrules",
            "claude.md",
            "cursor-rules.md",
            "agent-context.md",
            "agent-rules.md",
        ]
        for name in candidates:
            if (root / name).exists() or (integration_dir / name).exists():
                existing_ide.append(name)
        if existing_ide:
            info(f"  Detected existing: {', '.join(existing_ide)}")
            _import_ide_rules(root, cw_dir, existing_ide)


def _import_ide_rules(root: Path, cw_dir: Path, ide_files: list[str]) -> None:
    """Parse existing IDE context files and import conventions into rules.md."""
    imported_rules: list[str] = []

    for filename in ide_files:
        ide_path = root / filename
        if not ide_path.exists():
            integration_path = root / ".clockwork" / "integrations" / filename
            ide_path = integration_path if integration_path.exists() else ide_path
        if not ide_path.exists():
            continue
        try:
            content = ide_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Extract rule-like lines: lines starting with "- " that contain
        # directive keywords (must, should, do not, always, never, etc.)
        _DIRECTIVE_KEYWORDS = (
            "must", "should", "do not", "don't", "always", "never",
            "avoid", "prefer", "use ", "ensure", "require",
        )
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- "):
                continue
            lower = stripped.lower()
            if any(kw in lower for kw in _DIRECTIVE_KEYWORDS):
                imported_rules.append(stripped)

    if not imported_rules:
        return

    # De-duplicate against existing rules.md content
    rules_path = cw_dir / "rules.md"
    existing_content = ""
    if rules_path.exists():
        try:
            existing_content = rules_path.read_text(encoding="utf-8")
        except OSError:
            pass

    existing_lower = existing_content.lower()
    novel_rules = [
        r for r in imported_rules
        if r.lower() not in existing_lower
    ]

    if not novel_rules:
        return

    # Append imported rules
    try:
        with rules_path.open("a", encoding="utf-8") as f:
            f.write("\n\n## Imported from Existing IDE Files\n\n")
            for r in novel_rules:
                f.write(f"{r}\n")
        step(f"Imported {len(novel_rules)} rule(s) from {', '.join(ide_files)}")
    except OSError:
        pass
