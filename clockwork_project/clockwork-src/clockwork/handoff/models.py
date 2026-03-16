"""
Clockwork — Agent Handoff System
models.py: Data models for handoff structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class HandoffData:
    """
    Complete machine-readable handoff payload.

    Aggregated from Context Engine, Repository Scanner,
    Rule Engine, and Brain Manager.
    """

    project: str
    architecture: str
    current_summary: str
    next_task: str
    skills_required: List[str]
    rules_reference: str
    frameworks: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    task_state: str = "in_progress"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialise to plain dictionary for JSON output."""
        return {
            "project": self.project,
            "architecture": self.architecture,
            "current_summary": self.current_summary,
            "next_task": self.next_task,
            "skills_required": self.skills_required,
            "frameworks": self.frameworks,
            "languages": self.languages,
            "task_state": self.task_state,
            "rules_reference": self.rules_reference,
            "generated_at": self.generated_at,
        }


@dataclass
class HandoffLogEntry:
    """Single entry written to handoff_log.json after each handoff."""

    timestamp: str
    handoff_to: str
    next_task: str
    project: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "handoff_to": self.handoff_to,
            "next_task": self.next_task,
            "project": self.project,
        }