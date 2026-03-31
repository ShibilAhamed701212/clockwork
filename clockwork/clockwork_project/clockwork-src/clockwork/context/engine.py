"""
clockwork/context/engine.py
-----------------------------
ContextEngine — manages the lifecycle of .clockwork/context.yaml.

Responsibilities:
  • load()        — read and validate context.yaml into ProjectContext
  • save()        — write ProjectContext back to context.yaml
  • merge_scan()  — update auto-derived fields from a ScanResult
  • validate()    — check schema version and required fields
  • diff()        — detect what changed since last merge
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from clockwork.context.models import (
    ProjectContext,
    TaskEntry,
    ChangeEntry,
    ArchitectureNote,
    CONTEXT_SCHEMA_VERSION,
    CLOCKWORK_VERSION,
)


class ContextError(Exception):
    """Raised when the context cannot be loaded or is invalid."""


class ContextEngine:
    """
    Manages reading, writing, and updating .clockwork/context.yaml.

    Usage::

        engine  = ContextEngine(clockwork_dir=Path(".clockwork"))
        context = engine.load()

        # after a scan:
        engine.merge_scan(scan_result)

        # update a task:
        context.current_tasks[0].mark_done()
        engine.save(context)
    """

    CONTEXT_FILE = "context.yaml"

    # Fields that merge_scan() must NEVER overwrite when the existing
    # value is non-empty.  These are human-authored or agent-authored
    # content that scanning cannot reproduce.
    _PRESERVE_FIELDS: frozenset[str] = frozenset({
        "summary",
        "architecture_overview",
        "current_tasks",
        "architecture_notes",
        "agent_notes",
        "last_agent",
    })

    # Fields that merge_scan() ALWAYS overwrites from scanner data
    _SCANNER_FIELDS: frozenset[str] = frozenset({
        "primary_language",
        "languages",
        "frameworks",
        "entry_points",
        "total_files",
        "total_lines",
    })

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir.resolve()
        self.context_path  = self.clockwork_dir / self.CONTEXT_FILE

    # ------------------------------------------------------------------ #
    # Load / Save
    # ------------------------------------------------------------------ #

    def load(self) -> ProjectContext:
        """
        Load and return the current ProjectContext from disk.

        Raises ContextError if the file is missing or unparseable.
        """
        if not self.context_path.exists():
            raise ContextError(
                f"context.yaml not found at {self.context_path}\n"
                "Run:  clockwork init"
            )

        try:
            raw = self.context_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError as exc:
            raise ContextError(f"context.yaml is not valid YAML: {exc}") from exc
        except OSError as exc:
            raise ContextError(f"Cannot read context.yaml: {exc}") from exc

        if not isinstance(data, dict):
            raise ContextError("context.yaml must be a YAML mapping at the top level.")

        context = ProjectContext.from_dict(data)
        return context

    def load_or_default(self, project_name: str = "") -> ProjectContext:
        """
        Load context from disk, or return a fresh default context if the
        file does not yet exist.  Does not raise on missing file.
        """
        try:
            return self.load()
        except ContextError:
            return ProjectContext(project_name=project_name or self.clockwork_dir.parent.name)

    def save(self, context: ProjectContext) -> None:
        """
        Write *context* to .clockwork/context.yaml.

        Touches `last_updated` before writing.
        """
        context._touch()
        data = context.to_dict()

        try:
            self.clockwork_dir.mkdir(parents=True, exist_ok=True)
            self.context_path.write_text(
                yaml.dump(data, default_flow_style=False, allow_unicode=True,
                          sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ContextError(f"Cannot write context.yaml: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, context: Optional[ProjectContext] = None) -> list[str]:
        """
        Validate a ProjectContext (or load from disk if none given).

        Returns a list of issue strings.  Empty list = valid.
        """
        issues: list[str] = []

        try:
            ctx = context or self.load()
        except ContextError as exc:
            return [str(exc)]

        if ctx.clockwork_version != CLOCKWORK_VERSION:
            issues.append(
                f"clockwork_version mismatch: "
                f"file={ctx.clockwork_version!r}, expected={CLOCKWORK_VERSION!r}"
            )

        if ctx.memory_schema_version != CONTEXT_SCHEMA_VERSION:
            issues.append(
                f"memory_schema_version mismatch: "
                f"file={ctx.memory_schema_version}, expected={CONTEXT_SCHEMA_VERSION}"
            )

        if not ctx.project_name:
            issues.append("project_name is empty.")

        for task in ctx.current_tasks:
            if task.status not in ("pending", "in_progress", "done", "blocked"):
                issues.append(
                    f"Task '{task.id}' has unknown status: {task.status!r}"
                )

        return issues

    # ------------------------------------------------------------------ #
    # Merge with scanner output
    # ------------------------------------------------------------------ #

    def merge_scan(self, scan_result: object) -> ProjectContext:
        """
        Update auto-derived context fields from a ScanResult.

        Only overwrites fields listed in ``_SCANNER_FIELDS``.
        Fields listed in ``_PRESERVE_FIELDS`` are never overwritten
        when they already contain user-authored content.

        Returns the updated ProjectContext (also saves to disk).
        """
        # Lazy import to avoid circular dependency
        from clockwork.scanner.models import ScanResult

        if not isinstance(scan_result, ScanResult):
            raise TypeError("scan_result must be a clockwork.scanner.models.ScanResult")

        context = self.load_or_default(project_name=scan_result.project_name)

        # Capture what changed for the change log
        old_file_count  = context.total_files
        old_primary     = context.primary_language
        old_frameworks  = set(context.frameworks)

        # Overwrite scanner-derived fields
        context.primary_language = scan_result.primary_language
        context.languages        = dict(scan_result.languages)
        context.frameworks       = list(scan_result.frameworks)
        context.entry_points     = list(scan_result.entry_points)
        context.total_files      = scan_result.total_files
        context.total_lines      = scan_result.total_lines

        # Record the merge as a change event
        changes: list[str] = []
        if old_file_count != scan_result.total_files:
            delta = scan_result.total_files - old_file_count
            changes.append(
                f"File count: {old_file_count} → {scan_result.total_files} "
                f"({'+'  if delta > 0 else ''}{delta})"
            )
        if old_primary != scan_result.primary_language and scan_result.primary_language:
            changes.append(
                f"Primary language: {old_primary!r} → {scan_result.primary_language!r}"
            )
        new_frameworks = set(scan_result.frameworks) - old_frameworks
        if new_frameworks:
            changes.append(f"New frameworks detected: {', '.join(sorted(new_frameworks))}")

        if changes:
            context.record_change(ChangeEntry(
                description="Scan merge: " + "; ".join(changes),
                change_type="update",
                agent="clockwork.scanner",
            ))

        self.save(context)
        return context

    # ------------------------------------------------------------------ #
    # Diff
    # ------------------------------------------------------------------ #

    def diff(
        self, context_a: ProjectContext, context_b: ProjectContext
    ) -> dict[str, dict]:
        """
        Return a dict describing what changed between two ProjectContext
        snapshots.  Useful for verify and handoff pipelines.

        Returns::

            {
              "files": {"before": 10, "after": 12},
              "primary_language": {"before": "Python", "after": "Python"},
              ...
            }
        """
        diffs: dict[str, dict] = {}

        scalar_fields = (
            "primary_language", "total_files", "total_lines",
            "summary", "project_name",
        )
        for field in scalar_fields:
            a = getattr(context_a, field)
            b = getattr(context_b, field)
            if a != b:
                diffs[field] = {"before": a, "after": b}

        # Framework diff
        added_fw   = set(context_b.frameworks) - set(context_a.frameworks)
        removed_fw = set(context_a.frameworks) - set(context_b.frameworks)
        if added_fw or removed_fw:
            diffs["frameworks"] = {
                "added":   sorted(added_fw),
                "removed": sorted(removed_fw),
            }

        # Task diff
        ids_a = {t.id for t in context_a.current_tasks}
        ids_b = {t.id for t in context_b.current_tasks}
        added_tasks   = ids_b - ids_a
        removed_tasks = ids_a - ids_b
        if added_tasks or removed_tasks:
            diffs["tasks"] = {
                "added":   sorted(added_tasks),
                "removed": sorted(removed_tasks),
            }

        return diffs

    # ------------------------------------------------------------------ #
    # Convenience task helpers
    # ------------------------------------------------------------------ #

    def add_task(
        self,
        title: str,
        priority: str = "medium",
        notes: str = "",
        task_id: Optional[str] = None,
    ) -> TaskEntry:
        """Load context, add a task, save, and return the new TaskEntry."""
        import uuid
        context = self.load_or_default()
        task = TaskEntry(
            id=task_id or str(uuid.uuid4())[:8],
            title=title,
            priority=priority,
            notes=notes,
        )
        context.add_task(task)
        self.save(context)
        return task

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as done. Returns True if found."""
        context = self.load_or_default()
        task = context.task_by_id(task_id)
        if task is None:
            return False
        task.mark_done()
        self.save(context)
        return True

    def record_change(
        self,
        description: str,
        changed_files: Optional[list[str]] = None,
        agent: Optional[str] = None,
        change_type: str = "update",
    ) -> ChangeEntry:
        """Load context, append a change entry, save, return the entry."""
        context = self.load_or_default()
        change = ChangeEntry(
            description=description,
            changed_files=changed_files or [],
            agent=agent,
            change_type=change_type,
        )
        context.record_change(change)
        self.save(context)
        return change
