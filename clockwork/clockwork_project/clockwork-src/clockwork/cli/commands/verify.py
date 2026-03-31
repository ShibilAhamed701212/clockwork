"""
clockwork/cli/commands/verify.py
----------------------------------
`clockwork verify` — verify repository integrity.

Pipeline (spec §6):
    Repository Diff
    ↓
    Rule Evaluation
    ↓
    Brain Analysis   (stub — full Brain subsystem implemented separately)

Now diff-aware:
  • Default: only checks files changed since last scan
  • --full: bypasses diff, checks everything
  • --staged: checks only staged files (pre-commit mode)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule, result_block, json_output,
)
from clockwork.recovery.predictor import FailurePredictor
from clockwork.validation.pipeline import ValidationPipeline


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    passed: bool = True
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)

    def fail(self, reason: str) -> None:
        self.passed = False
        self.failures.append(reason)

    def ok(self, msg: str) -> None:
        self.checks.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "warnings": self.warnings,
            "failures": self.failures,
            "changed_files": self.changed_files,
        }


# ── Command ────────────────────────────────────────────────────────────────

def cmd_verify(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
    deep: bool = typer.Option(
        False, "--deep",
        help="Run additional validation pipeline and predictive risk checks.",
    ),
    full: bool = typer.Option(
        False, "--full",
        help="Bypass diff and check all files (ignore last-scan tracking).",
    ),
    staged: bool = typer.Option(
        False, "--staged",
        help="Check only staged files (pre-commit mode).",
    ),
) -> None:
    """
    Verify repository integrity against Clockwork rules.

    Runs the Rule Engine pipeline: diff → rule evaluation → brain analysis.
    By default only checks files changed since last scan.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Verify")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    start = time.perf_counter()
    result = VerificationResult()

    # ── Git diff analysis ──────────────────────────────────────────────
    diff_info = None
    if not full:
        diff_info = _get_diff_info(root, staged=staged)
        if diff_info and not as_json:
            _display_diff_info(diff_info, staged=staged)
        if diff_info and diff_info.get("changed_files"):
            result.changed_files = diff_info["changed_files"]

    # Run each check stage
    _check_required_files(cw_dir, result)
    _check_context_schema(cw_dir, result)
    _check_repo_map(cw_dir, result)
    _check_protected_directories(cw_dir, result)
    _check_rules_parseable(cw_dir, result)

    # Diff-aware rule checking (only changed files)
    if diff_info and result.changed_files and not full:
        _check_changed_files(cw_dir, result.changed_files, result)
    elif not full and diff_info and not diff_info.get("has_changes", True):
        result.ok("No files changed since last scan")

    if deep and result.passed:
        _run_deep_validation(cw_dir, result)

    elapsed_ms = (time.perf_counter() - start) * 1000

    if as_json:
        json_output({**result.to_dict(), "elapsed_ms": round(elapsed_ms, 1)})
        raise typer.Exit(code=0 if result.passed else 1)

    # Human output
    rule()
    for msg in result.checks:
        success(msg)
    for msg in result.warnings:
        warn(msg)
    for msg in result.failures:
        typer.echo(f"  ✗ {msg}")

    rule()
    if result.passed:
        typer.echo(f"\n{'  ' + chr(10033) + ' Verification passed.'} "
                   f"({elapsed_ms:.0f} ms)")
    else:
        typer.echo(
            f"\nVerification FAILED — {len(result.failures)} issue(s) found.",
            err=True,
        )
        raise typer.Exit(code=1)


# ── Git diff helpers ───────────────────────────────────────────────────────

def _get_diff_info(root: Path, staged: bool = False) -> Optional[dict]:
    """Get git diff information. Returns None if not a git repo."""
    try:
        from clockwork.scanner.git_diff import GitDiffScanner
        scanner = GitDiffScanner(root)
        if not scanner.is_git_repo():
            return None

        if staged:
            diff = scanner.diff_staged()
        else:
            diff = scanner.diff_since_last_scan()

        changed = diff.all_changed()
        return {
            "is_git_repo": True,
            "branch": diff.current_branch,
            "commit": diff.last_commit_sha[:8] if diff.last_commit_sha else "",
            "has_changes": bool(changed),
            "changed_files": changed,
            "added": diff.added,
            "deleted": diff.deleted,
            "modified": diff.modified,
            "staged": diff.staged,
            "untracked": diff.untracked,
        }
    except Exception:
        return None


def _display_diff_info(diff_info: dict, staged: bool = False) -> None:
    """Display a summary of git diff info."""
    mode = "staged" if staged else "since last scan"
    info(f"Git: {diff_info.get('branch', '?')} @ {diff_info.get('commit', '?')}")

    if not diff_info.get("has_changes"):
        info(f"No changes {mode}")
        return

    added = diff_info.get("added", [])
    deleted = diff_info.get("deleted", [])
    modified = diff_info.get("modified", [])

    parts = []
    if added:
        parts.append(f"{len(added)} added")
    if deleted:
        parts.append(f"{len(deleted)} deleted")
    if modified:
        parts.append(f"{len(modified)} modified")

    info(f"Changes {mode}: {', '.join(parts)}")

    # Show first few files
    all_changed = diff_info.get("changed_files", [])
    for f in all_changed[:5]:
        prefix = "+"
        if f in deleted:
            prefix = "-"
        elif f in modified:
            prefix = "~"
        step(f"  {prefix} {f}")
    if len(all_changed) > 5:
        info(f"  ... and {len(all_changed) - 5} more")

    rule()


def _check_changed_files(
    cw_dir: Path, changed_files: list[str], result: VerificationResult
) -> None:
    """Run targeted checks on changed files only."""
    rules_path = cw_dir / "rules.md"
    if not rules_path.exists():
        return

    try:
        rules_content = rules_path.read_text(encoding="utf-8")
    except OSError:
        return

    # Check protected file rules
    protected_patterns = _extract_protected_patterns(rules_content)
    for f in changed_files:
        for pattern, description in protected_patterns:
            if pattern in f:
                result.warn(
                    f"Protected file modified: {f} ({description})"
                )

    result.ok(f"Checked {len(changed_files)} changed file(s) against rules")


def _extract_protected_patterns(rules_content: str) -> list[tuple[str, str]]:
    """Extract file protection patterns from rules.md."""
    patterns: list[tuple[str, str]] = []
    for line in rules_content.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        lower = line.lower()
        if "must not be" in lower or "should not be" in lower or "do not modify" in lower:
            # Extract the file/dir being protected
            words = line[2:].split()
            if words:
                target = words[0].strip("`").strip("*")
                if target and len(target) > 2:
                    patterns.append((target, line[2:]))
    return patterns


# ── Check stages ───────────────────────────────────────────────────────────

def _check_required_files(cw_dir: Path, result: VerificationResult) -> None:
    """Verify all required .clockwork files exist."""
    required = ["context.yaml", "rules.md", "config.yaml"]
    for filename in required:
        if (cw_dir / filename).exists():
            result.ok(f"Found .clockwork/{filename}")
        else:
            result.fail(f"Missing required file: .clockwork/{filename}")


def _check_context_schema(cw_dir: Path, result: VerificationResult) -> None:
    """Validate context.yaml can be parsed and has required keys."""
    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        return  # already caught above

    try:
        ctx = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        result.fail(f"context.yaml is not valid YAML: {exc}")
        return

    required_keys = ["clockwork_version", "project_name", "memory_schema_version"]
    for key in required_keys:
        if key not in ctx:
            result.warn(f"context.yaml missing recommended key: '{key}'")

    result.ok("context.yaml schema valid")


def _check_repo_map(cw_dir: Path, result: VerificationResult) -> None:
    """Validate repo_map.json is present and parseable."""
    rm_path = cw_dir / "repo_map.json"
    if not rm_path.exists():
        result.warn("repo_map.json not found — run  clockwork scan")
        return

    try:
        data = json.loads(rm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.fail(f"repo_map.json is not valid JSON: {exc}")
        return

    total = data.get("total_files", "?")
    result.ok(f"repo_map.json valid ({total} files indexed)")


def _check_protected_directories(cw_dir: Path, result: VerificationResult) -> None:
    """Ensure critical .clockwork sub-directories exist."""
    for sub in ("handoff", "packages", "logs"):
        if (cw_dir / sub).is_dir():
            result.ok(f".clockwork/{sub}/ present")
        else:
            result.warn(f".clockwork/{sub}/ missing — re-run  clockwork init")


def _check_rules_parseable(cw_dir: Path, result: VerificationResult) -> None:
    """Ensure rules.md is non-empty and readable."""
    rules_path = cw_dir / "rules.md"
    if not rules_path.exists():
        return  # caught by required files check

    try:
        content = rules_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.fail(f"Cannot read rules.md: {exc}")
        return

    if not content:
        result.warn("rules.md is empty — consider adding project rules")
    else:
        rule_count = sum(1 for line in content.splitlines() if line.startswith("- "))
        result.ok(f"rules.md readable ({rule_count} rule(s) found)")


def _run_deep_validation(cw_dir: Path, result: VerificationResult) -> None:
    """Run predictive risk checks and output validation to mirror v2 capabilities."""
    repo_map_path = cw_dir / "repo_map.json"
    context_path = cw_dir / "context.yaml"

    repo_map: dict = {}
    context: dict = {}

    if repo_map_path.exists():
        try:
            repo_map = json.loads(repo_map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            result.warn("Deep verify skipped risk prediction: repo_map.json is invalid")

    if context_path.exists():
        try:
            context = yaml.safe_load(context_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            result.warn("Deep verify skipped context-aware checks: context.yaml is invalid")

    risk = FailurePredictor().predict(repo_map, context)
    result.ok(f"predictive risk: {risk['risk_level']} ({risk['risk_score']})")
    if risk["risk_level"] == "high":
        result.warn("High predictive risk detected; run clockwork repair before major edits")

    pipeline = ValidationPipeline(context=context)
    deep_result = pipeline.run({"success": True, "proposed_changes": []}, action={"type": "verify", "target": "."})
    if deep_result.passed:
        result.ok(f"deep validation passed (score={deep_result.score})")
    else:
        for message in deep_result.errors:
            result.fail(f"Deep validation: {message}")
    for message in deep_result.warnings:
        result.warn(f"Deep validation: {message}")
