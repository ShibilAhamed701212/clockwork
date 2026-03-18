"""
Clockwork — Agent Handoff System
engine.py: Orchestrates the complete handoff generation pipeline.

Pipeline:
  1. Validate repository state
  2. Aggregate data from all subsystems
  3. Render human-readable brief (next_agent_brief.md)
  4. Write machine-readable JSON (handoff.json)
  5. Log the handoff event
"""

from __future__ import annotations

import json
from pathlib import Path

from .aggregator import aggregate_handoff_data
from .brief_generator import render_brief
from .logger import log_handoff
from .models import HandoffData
from .validator import ValidationResult, validate_before_handoff


class HandoffEngine:
    """
    Main entry-point for the Agent Handoff subsystem.

    Usage::

        engine = HandoffEngine(repo_root=Path("."))
        result = engine.run(target_agent="Claude")
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.handoff_dir = self.clockwork_dir / "handoff"

    def run(self, target_agent: str = "unknown") -> tuple[bool, str]:
        """
        Execute the full handoff pipeline.

        Args:
            target_agent: Label for the agent receiving the handoff.

        Returns:
            (success: bool, message: str)
        """
        validation: ValidationResult = validate_before_handoff(self.clockwork_dir)
        if not validation.passed:
            reasons = "\n".join(f"  * {e}" for e in validation.errors)
            return False, f"Handoff blocked - validation failed:\n{reasons}"

        data: HandoffData = aggregate_handoff_data(self.clockwork_dir)

        self.handoff_dir.mkdir(parents=True, exist_ok=True)

        brief_md = render_brief(data)
        brief_path = self.handoff_dir / "next_agent_brief.md"
        brief_path.write_text(brief_md, encoding="utf-8")

        handoff_path = self.handoff_dir / "handoff.json"
        handoff_path.write_text(
            json.dumps(data.to_dict(), indent=2), encoding="utf-8"
        )

        log_handoff(self.clockwork_dir, data, target_agent=target_agent)

        warn_text = ""
        if validation.warnings:
            warn_lines = "\n".join(f"  ! {w}" for w in validation.warnings)
            warn_text = f"\nWarnings:\n{warn_lines}"

        return True, (
            f"Handoff generated successfully.\n"
            f"  -> {brief_path.relative_to(self.repo_root)}\n"
            f"  -> {handoff_path.relative_to(self.repo_root)}"
            f"{warn_text}"
        )