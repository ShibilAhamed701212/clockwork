"""
Clockwork — Agent Handoff System
validator.py: Pre-handoff repository integrity validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ValidationResult:
    """Result of a pre-handoff validation pass."""

    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_before_handoff(clockwork_dir: Path) -> ValidationResult:
    """
    Run all pre-handoff checks against the .clockwork directory.

    Args:
        clockwork_dir: Path to the .clockwork directory.

    Returns:
        ValidationResult with pass/fail status and diagnostic messages.
    """
    result = ValidationResult(passed=True)

    if not clockwork_dir.exists():
        result.add_error(
            "Clockwork is not initialised. Run `clockwork init` first."
        )
        return result

    context_path = clockwork_dir / "context.yaml"
    if not context_path.exists():
        result.add_error(
            "context.yaml is missing. Run `clockwork update` to regenerate."
        )

    repo_map_path = clockwork_dir / "repo_map.json"
    if not repo_map_path.exists():
        result.add_warning(
            "repo_map.json not found. Run `clockwork scan` for richer handoff data."
        )
    else:
        try:
            content = json.loads(repo_map_path.read_text(encoding="utf-8"))
            if not content:
                result.add_warning("repo_map.json is empty.")
        except json.JSONDecodeError:
            result.add_error("repo_map.json is malformed JSON.")

    rules_path = clockwork_dir / "rules.md"
    if not rules_path.exists():
        result.add_warning(
            "rules.md not found. Handoff will reference a missing rules file."
        )

    log_path = clockwork_dir / "validation_log.json"
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
            entries = log if isinstance(log, list) else [log]
            recent = entries[-1] if entries else {}
            if recent.get("status") == "failed":
                result.add_error(
                    f"Last validation failed: {recent.get('reason', 'unknown reason')}. "
                    "Resolve before generating a handoff."
                )
        except (json.JSONDecodeError, KeyError):
            result.add_warning("Could not read validation_log.json.")

    return result