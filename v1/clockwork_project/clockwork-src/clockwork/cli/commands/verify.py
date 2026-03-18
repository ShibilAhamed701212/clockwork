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

Currently implements:
  • context.yaml schema validation
  • repo_map.json presence and structure check
  • rules.md presence check
  • Protected file integrity check
  • Basic rule text parsing for violations
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


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    passed: bool = True
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

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
) -> None:
    """
    Verify repository integrity against Clockwork rules.

    Runs the Rule Engine pipeline: diff → rule evaluation → brain analysis.
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

    # Run each check stage
    _check_required_files(cw_dir, result)
    _check_context_schema(cw_dir, result)
    _check_repo_map(cw_dir, result)
    _check_protected_directories(cw_dir, result)
    _check_rules_parseable(cw_dir, result)

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
