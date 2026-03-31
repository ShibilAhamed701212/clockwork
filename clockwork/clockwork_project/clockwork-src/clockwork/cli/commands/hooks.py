"""
clockwork/cli/commands/hooks.py
clockwork hooks — manage git hooks for repository governance.
"""
from __future__ import annotations
import stat
from pathlib import Path
from typing import Optional
import typer
from clockwork.cli.output import header, success, info, warn, error, rule

hooks_app = typer.Typer(name="hooks",
    help="Manage git hooks for Clockwork governance.", no_args_is_help=True)

PRE_COMMIT_CONTENT = """#!/bin/sh
# Clockwork pre-commit hook
# Runs clockwork verify against staged files and blocks commit on violations.
VERIFY_OUTPUT=$(clockwork verify --staged --json 2>&1)
VERIFY_EXIT=$?
if [ $VERIFY_EXIT -ne 0 ]; then
  echo "Clockwork: verification command failed; blocking commit"
  echo "$VERIFY_OUTPUT"
  exit 1
fi

echo "$VERIFY_OUTPUT" | python3 -c "
import sys, json
try:
    r = json.load(sys.stdin)
    if not r.get('passed', True):
        print('Clockwork: commit blocked due to rule violations')
        for f in r.get('failures', []):
            print('  \\xe2\\x9c\\x97', f)
        for w in r.get('warnings', []):
            print('  !', w)
        sys.exit(1)
except Exception:
    print('Clockwork: invalid verification output; blocking commit')
    sys.exit(1)
"
if [ $? -ne 0 ]; then
  exit 1
fi
"""

@hooks_app.command("install")
def hooks_install(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    force: bool = typer.Option(False, "--force", "-f",
                               help="Overwrite existing hook."),
) -> None:
    """Install Clockwork pre-commit hook."""
    root = (repo_root or Path.cwd()).resolve()
    git_hooks = root / ".git" / "hooks"
    header("Clockwork Hooks")
    if not git_hooks.is_dir():
        error("Not a git repository (no .git/hooks found).")
        raise typer.Exit(code=1)
    hook_path = git_hooks / "pre-commit"
    if hook_path.exists() and not force:
        warn("pre-commit hook already exists. Use --force to overwrite.")
        raise typer.Exit(code=0)
    hook_path.write_text(PRE_COMMIT_CONTENT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC
                    | stat.S_IXGRP | stat.S_IXOTH)
    rule()
    success("Pre-commit hook installed.")
    info("  Location : .git/hooks/pre-commit")
    info("  Trigger  : clockwork verify --staged on every git commit")
    info("\nTo uninstall: clockwork hooks remove")

@hooks_app.command("remove")
def hooks_remove(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Remove the Clockwork pre-commit hook."""
    root = (repo_root or Path.cwd()).resolve()
    hook_path = root / ".git" / "hooks" / "pre-commit"
    if not hook_path.exists():
        warn("No pre-commit hook found.")
        raise typer.Exit(code=0)
    content = hook_path.read_text(encoding="utf-8")
    if "Clockwork" not in content:
        warn("Existing hook was not installed by Clockwork. Aborting.")
        raise typer.Exit(code=1)
    hook_path.unlink()
    success("Pre-commit hook removed.")

@hooks_app.command("status")
def hooks_status(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Show hook installation status."""
    root = (repo_root or Path.cwd()).resolve()
    hook_path = root / ".git" / "hooks" / "pre-commit"
    header("Hook Status")
    if not hook_path.exists():
        warn("pre-commit hook: not installed")
        info("  Run: clockwork hooks install")
    else:
        content = hook_path.read_text(encoding="utf-8")
        if "Clockwork" in content:
            success("pre-commit hook: installed (Clockwork managed)")
        else:
            warn("pre-commit hook: installed (NOT Clockwork managed)")
