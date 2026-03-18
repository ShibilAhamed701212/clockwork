"""
clockwork/context/models.py
-----------------------------
Typed data models for the Clockwork Context Engine.

ProjectContext is the central data structure that persists in
.clockwork/context.yaml and is shared across all subsystems.

Schema version history:
  1 — initial schema (v0.1)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Any
import json


CONTEXT_SCHEMA_VERSION = 1
CLOCKWORK_VERSION = "0.1"


# ── Sub-models ─────────────────────────────────────────────────────────────

@dataclass
class TaskEntry:
    """A single tracked development task."""

    id: str
    title: str
    status: str = "pending"          # pending | in_progress | done | blocked
    priority: str = "medium"         # low | medium | high | critical
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None
    assigned_to: Optional[str] = None   # agent name or "human"
    notes: str = ""

    def mark_done(self) -> None:
        self.status = "done"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_in_progress(self, agent: Optional[str] = None) -> None:
        self.status = "in_progress"
        self.updated_at = datetime.now(timezone.utc).isoformat()
        if agent:
            self.assigned_to = agent

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TaskEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ChangeEntry:
    """A recorded repository change event."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    description: str = ""
    changed_files: list[str] = field(default_factory=list)
    agent: Optional[str] = None       # which agent made the change
    change_type: str = "update"       # update | refactor | feature | fix | docs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ArchitectureNote:
    """A recorded architectural decision or constraint."""

    id: str
    title: str
    description: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ArchitectureNote":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Main context model ─────────────────────────────────────────────────────

@dataclass
class ProjectContext:
    """
    The complete persisted project context.

    This is the canonical project memory document stored in
    .clockwork/context.yaml and shared across all Clockwork subsystems.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    clockwork_version: str = CLOCKWORK_VERSION
    memory_schema_version: int = CONTEXT_SCHEMA_VERSION
    project_name: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_updated: Optional[str] = None

    # ── Human-authored descriptions ───────────────────────────────────────
    summary: str = ""
    architecture_overview: str = ""

    # ── Scanner-derived fields (auto-updated by merge_scan) ───────────────
    primary_language: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0

    # ── Tasks ─────────────────────────────────────────────────────────────
    current_tasks: list[TaskEntry] = field(default_factory=list)

    # ── Change history ────────────────────────────────────────────────────
    recent_changes: list[ChangeEntry] = field(default_factory=list)
    max_recent_changes: int = 50   # rolling window

    # ── Architecture notes ────────────────────────────────────────────────
    architecture_notes: list[ArchitectureNote] = field(default_factory=list)

    # ── Agent metadata ────────────────────────────────────────────────────
    last_agent: Optional[str] = None
    agent_notes: str = ""

    # ── Extra fields preserved from disk (forward-compatibility) ─────────
    _extra: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def pending_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "pending"]

    @property
    def in_progress_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "in_progress"]

    @property
    def done_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "done"]

    def task_by_id(self, task_id: str) -> Optional[TaskEntry]:
        return next((t for t in self.current_tasks if t.id == task_id), None)

    # ------------------------------------------------------------------ #
    # Mutation helpers
    # ------------------------------------------------------------------ #

    def add_task(self, task: TaskEntry) -> None:
        """Add a task; replace if id already exists."""
        self.current_tasks = [t for t in self.current_tasks if t.id != task.id]
        self.current_tasks.append(task)
        self._touch()

    def remove_task(self, task_id: str) -> bool:
        """Remove task by id. Returns True if found and removed."""
        before = len(self.current_tasks)
        self.current_tasks = [t for t in self.current_tasks if t.id != task_id]
        removed = len(self.current_tasks) < before
        if removed:
            self._touch()
        return removed

    def record_change(self, change: ChangeEntry) -> None:
        """Append a change entry, trimming the rolling window."""
        self.recent_changes.append(change)
        if len(self.recent_changes) > self.max_recent_changes:
            self.recent_changes = self.recent_changes[-self.max_recent_changes:]
        self._touch()

    def add_architecture_note(self, note: ArchitectureNote) -> None:
        self.architecture_notes = [
            n for n in self.architecture_notes if n.id != note.id
        ]
        self.architecture_notes.append(note)
        self._touch()

    def _touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Produce a plain dict suitable for YAML / JSON serialisation."""
        d: dict[str, Any] = {
            "clockwork_version":      self.clockwork_version,
            "memory_schema_version":  self.memory_schema_version,
            "project_name":           self.project_name,
            "created_at":             self.created_at,
            "last_updated":           self.last_updated,
            "summary":                self.summary,
            "architecture_overview":  self.architecture_overview,
            "primary_language":       self.primary_language,
            "languages":              self.languages,
            "frameworks":             self.frameworks,
            "entry_points":           self.entry_points,
            "total_files":            self.total_files,
            "total_lines":            self.total_lines,
            "current_tasks":          [t.to_dict() for t in self.current_tasks],
            "recent_changes":         [c.to_dict() for c in self.recent_changes],
            "max_recent_changes":     self.max_recent_changes,
            "architecture_notes":     [n.to_dict() for n in self.architecture_notes],
            "last_agent":             self.last_agent,
            "agent_notes":            self.agent_notes,
        }
        # Re-attach any extra keys from disk for forward-compatibility
        d.update(self._extra)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectContext":
        """Reconstruct from a plain dict (loaded from YAML or JSON)."""
        known_keys = {f for f in cls.__dataclass_fields__ if f != "_extra"}

        tasks = [
            TaskEntry.from_dict(t)
            for t in data.get("current_tasks", [])
            if isinstance(t, dict)
        ]
        changes = [
            ChangeEntry.from_dict(c)
            for c in data.get("recent_changes", [])
            if isinstance(c, dict)
        ]
        notes = [
            ArchitectureNote.from_dict(n)
            for n in data.get("architecture_notes", [])
            if isinstance(n, dict)
        ]

        scalar_fields = {
            k: v for k, v in data.items()
            if k in known_keys
            and k not in ("current_tasks", "recent_changes", "architecture_notes")
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            **scalar_fields,
            current_tasks=tasks,
            recent_changes=changes,
            architecture_notes=notes,
            _extra=extra,
        )
