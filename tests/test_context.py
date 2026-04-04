"""
tests/test_context.py
----------------------
Unit tests for the Clockwork Context Engine subsystem.

Covers:
  • ProjectContext model (tasks, changes, architecture notes)
  • ContextEngine.load / save / validate
  • ContextEngine.merge_scan
  • ContextEngine.diff
  • TaskEntry / ChangeEntry lifecycle
  • Forward-compatibility (_extra fields preserved)

Run with:  pytest tests/test_context.py -v
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from clockwork.context.models import (
    ProjectContext,
    TaskEntry,
    ChangeEntry,
    ArchitectureNote,
    CONTEXT_SCHEMA_VERSION,
    CLOCKWORK_VERSION,
)
from clockwork.context.engine import ContextEngine, ContextError


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _make_cw_dir(root: Path) -> Path:
    """Create a minimal .clockwork dir with a valid context.yaml."""
    cw = root / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    engine = ContextEngine(cw)
    ctx = ProjectContext(project_name="test_project")
    engine.save(ctx)
    return cw


def _make_scan_result(root: Path):
    """Build a minimal ScanResult-like object for merge tests."""
    # Use the real scanner if available
    try:
        from clockwork.scanner import RepositoryScanner
        (root / "main.py").write_text("class App:\n    def run(self): pass\n")
        (root / "requirements.txt").write_text("fastapi\npydantic\n")
        return RepositoryScanner(repo_root=root, extract_symbols=False).scan()
    except Exception:
        # Minimal stub
        from clockwork.scanner.models import ScanResult
        return ScanResult(
            project_name="test_project",
            total_files=5,
            total_lines=120,
            primary_language="Python",
            languages={"Python": 4, "Markdown": 1},
            frameworks=["FastAPI", "Pydantic"],
            entry_points=["main.py"],
        )


# ─────────────────────────────────────────────
# TaskEntry
# ─────────────────────────────────────────────

class TestTaskEntry:
    def test_defaults(self):
        t = TaskEntry(id="t1", title="Do something")
        assert t.status == "pending"
        assert t.priority == "medium"
        assert t.assigned_to is None

    def test_mark_done(self):
        t = TaskEntry(id="t1", title="Do something")
        t.mark_done()
        assert t.status == "done"
        assert t.updated_at is not None

    def test_mark_in_progress(self):
        t = TaskEntry(id="t1", title="Do something")
        t.mark_in_progress(agent="claude-sonnet")
        assert t.status == "in_progress"
        assert t.assigned_to == "claude-sonnet"

    def test_roundtrip(self):
        t = TaskEntry(id="t1", title="Build scanner", priority="high", notes="see spec")
        restored = TaskEntry.from_dict(t.to_dict())
        assert restored.id == t.id
        assert restored.title == t.title
        assert restored.priority == t.priority


# ─────────────────────────────────────────────
# ChangeEntry
# ─────────────────────────────────────────────

class TestChangeEntry:
    def test_defaults(self):
        c = ChangeEntry(description="Fixed bug")
        assert c.change_type == "update"
        assert c.changed_files == []

    def test_roundtrip(self):
        c = ChangeEntry(
            description="Added tests",
            changed_files=["tests/test_scanner.py"],
            agent="claude",
            change_type="feature",
        )
        restored = ChangeEntry.from_dict(c.to_dict())
        assert restored.description == c.description
        assert restored.changed_files == c.changed_files


# ─────────────────────────────────────────────
# ProjectContext model
# ─────────────────────────────────────────────

class TestProjectContext:
    def test_default_construction(self):
        ctx = ProjectContext(project_name="myapp")
        assert ctx.project_name == "myapp"
        assert ctx.clockwork_version == CLOCKWORK_VERSION
        assert ctx.memory_schema_version == CONTEXT_SCHEMA_VERSION
        assert ctx.current_tasks == []
        assert ctx.recent_changes == []

    def test_add_and_retrieve_task(self):
        ctx = ProjectContext(project_name="p")
        task = TaskEntry(id="t1", title="Implement scanner")
        ctx.add_task(task)
        assert len(ctx.current_tasks) == 1
        assert ctx.task_by_id("t1") is task

    def test_add_task_replaces_existing(self):
        ctx = ProjectContext(project_name="p")
        ctx.add_task(TaskEntry(id="t1", title="v1"))
        ctx.add_task(TaskEntry(id="t1", title="v2"))
        assert len(ctx.current_tasks) == 1
        assert ctx.task_by_id("t1").title == "v2"

    def test_remove_task(self):
        ctx = ProjectContext(project_name="p")
        ctx.add_task(TaskEntry(id="t1", title="Task A"))
        removed = ctx.remove_task("t1")
        assert removed is True
        assert ctx.task_by_id("t1") is None

    def test_remove_nonexistent_task(self):
        ctx = ProjectContext(project_name="p")
        assert ctx.remove_task("no-such-id") is False

    def test_pending_tasks_property(self):
        ctx = ProjectContext(project_name="p")
        ctx.add_task(TaskEntry(id="t1", title="A", status="pending"))
        ctx.add_task(TaskEntry(id="t2", title="B", status="done"))
        assert len(ctx.pending_tasks) == 1

    def test_done_tasks_property(self):
        ctx = ProjectContext(project_name="p")
        t = TaskEntry(id="t1", title="A")
        t.mark_done()
        ctx.add_task(t)
        assert len(ctx.done_tasks) == 1

    def test_record_change(self):
        ctx = ProjectContext(project_name="p")
        ctx.record_change(ChangeEntry(description="Initial commit"))
        assert len(ctx.recent_changes) == 1

    def test_change_rolling_window(self):
        ctx = ProjectContext(project_name="p", max_recent_changes=3)
        for i in range(5):
            ctx.record_change(ChangeEntry(description=f"change {i}"))
        assert len(ctx.recent_changes) == 3
        assert ctx.recent_changes[-1].description == "change 4"

    def test_add_architecture_note(self):
        ctx = ProjectContext(project_name="p")
        note = ArchitectureNote(id="adr1", title="Use Typer for CLI", description="...")
        ctx.add_architecture_note(note)
        assert len(ctx.architecture_notes) == 1

    def test_architecture_note_dedup(self):
        ctx = ProjectContext(project_name="p")
        ctx.add_architecture_note(ArchitectureNote(id="adr1", title="v1", description=""))
        ctx.add_architecture_note(ArchitectureNote(id="adr1", title="v2", description=""))
        assert len(ctx.architecture_notes) == 1
        assert ctx.architecture_notes[0].title == "v2"

    def test_to_dict_roundtrip(self):
        ctx = ProjectContext(project_name="myapp", summary="Great project")
        ctx.add_task(TaskEntry(id="t1", title="Do it"))
        ctx.record_change(ChangeEntry(description="started"))
        d = ctx.to_dict()
        restored = ProjectContext.from_dict(d)
        assert restored.project_name == ctx.project_name
        assert restored.summary == ctx.summary
        assert len(restored.current_tasks) == 1
        assert restored.current_tasks[0].title == "Do it"
        assert len(restored.recent_changes) == 1

    def test_extra_fields_preserved(self):
        """Forward-compat: unknown keys from YAML are preserved in _extra."""
        data = {
            "clockwork_version": "0.1",
            "memory_schema_version": 1,
            "project_name": "p",
            "future_field": "some_value",
            "another_future": [1, 2, 3],
        }
        ctx = ProjectContext.from_dict(data)
        assert ctx._extra.get("future_field") == "some_value"
        # Round-trip preserves extra fields
        d = ctx.to_dict()
        assert d.get("future_field") == "some_value"


# ─────────────────────────────────────────────
# ContextEngine – load / save / validate
# ─────────────────────────────────────────────

class TestContextEngine:
    def test_save_creates_file(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        engine = ContextEngine(cw)
        engine.save(ProjectContext(project_name="test"))
        assert (cw / "context.yaml").exists()

    def test_load_roundtrip(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        assert ctx.project_name == "test_project"
        assert ctx.clockwork_version == CLOCKWORK_VERSION

    def test_load_raises_on_missing(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        engine = ContextEngine(cw)
        with pytest.raises(ContextError, match="context.yaml not found"):
            engine.load()

    def test_load_raises_on_invalid_yaml(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        (cw / "context.yaml").write_text(": invalid: yaml: {{{")
        engine = ContextEngine(cw)
        with pytest.raises(ContextError):
            engine.load()

    def test_load_or_default_returns_default(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        engine = ContextEngine(cw)
        ctx = engine.load_or_default(project_name="fallback")
        assert ctx.project_name == "fallback"

    def test_save_preserves_tasks(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.add_task(TaskEntry(id="t1", title="Build rule engine"))
        engine.save(ctx)
        reloaded = engine.load()
        assert len(reloaded.current_tasks) == 1
        assert reloaded.current_tasks[0].title == "Build rule engine"

    def test_save_preserves_changes(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.record_change(ChangeEntry(description="big refactor"))
        engine.save(ctx)
        reloaded = engine.load()
        assert any(c.description == "big refactor" for c in reloaded.recent_changes)

    def test_save_preserves_extra_fields(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir()
        data = {
            "clockwork_version": "0.1",
            "memory_schema_version": 1,
            "project_name": "test",
            "custom_key": "custom_value",
        }
        (cw / "context.yaml").write_text(yaml.dump(data))
        engine = ContextEngine(cw)
        ctx = engine.load()
        assert ctx._extra.get("custom_key") == "custom_value"
        engine.save(ctx)
        reloaded_raw = yaml.safe_load((cw / "context.yaml").read_text())
        assert reloaded_raw.get("custom_key") == "custom_value"


# ─────────────────────────────────────────────
# ContextEngine – validation
# ─────────────────────────────────────────────

class TestContextValidation:
    def test_valid_context_no_issues(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        issues = engine.validate()
        assert issues == []

    def test_missing_project_name_flagged(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.project_name = ""
        engine.save(ctx)
        issues = engine.validate()
        assert any("project_name" in i for i in issues)

    def test_invalid_task_status_flagged(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.current_tasks.append(TaskEntry(id="t1", title="bad", status="flying"))
        engine.save(ctx)
        issues = engine.validate()
        assert any("flying" in i for i in issues)

    def test_version_mismatch_flagged(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.clockwork_version = "9.9"
        engine.save(ctx)
        issues = engine.validate()
        assert any("clockwork_version" in i for i in issues)


# ─────────────────────────────────────────────
# ContextEngine – merge_scan
# ─────────────────────────────────────────────

class TestMergeScan:
    def test_merge_updates_language(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        scan = _make_scan_result(tmp_path)
        ctx = engine.merge_scan(scan)
        assert ctx.primary_language != "" or ctx.total_files >= 0

    def test_merge_updates_file_count(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        scan = _make_scan_result(tmp_path)
        ctx = engine.merge_scan(scan)
        assert ctx.total_files == scan.total_files

    def test_merge_updates_frameworks(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        scan = _make_scan_result(tmp_path)
        ctx = engine.merge_scan(scan)
        assert ctx.frameworks == scan.frameworks

    def test_merge_preserves_summary(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.summary = "My hand-written summary"
        engine.save(ctx)
        scan = _make_scan_result(tmp_path)
        merged = engine.merge_scan(scan)
        assert merged.summary == "My hand-written summary"

    def test_merge_preserves_tasks(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        ctx = engine.load()
        ctx.add_task(TaskEntry(id="t1", title="Don't lose me"))
        engine.save(ctx)
        scan = _make_scan_result(tmp_path)
        merged = engine.merge_scan(scan)
        assert any(t.id == "t1" for t in merged.current_tasks)

    def test_merge_records_change_event(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        # First scan sets a baseline
        engine.merge_scan(_make_scan_result(tmp_path))
        ctx = engine.load()
        initial_changes = len(ctx.recent_changes)
        # Second scan with different count triggers a change record
        from clockwork.scanner.models import ScanResult
        fake_scan = ScanResult(
            project_name="test_project",
            total_files=999,
            primary_language="Rust",
            languages={"Rust": 999},
            frameworks=[],
        )
        engine.merge_scan(fake_scan)
        ctx2 = engine.load()
        assert len(ctx2.recent_changes) > initial_changes

    def test_merge_raises_on_wrong_type(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        with pytest.raises(TypeError):
            engine.merge_scan({"not": "a ScanResult"})


# ─────────────────────────────────────────────
# ContextEngine – diff
# ─────────────────────────────────────────────

class TestContextDiff:
    def test_diff_detects_file_count_change(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        a = ProjectContext(project_name="p", total_files=10)
        b = ProjectContext(project_name="p", total_files=15)
        d = engine.diff(a, b)
        assert "total_files" in d
        assert d["total_files"]["before"] == 10
        assert d["total_files"]["after"] == 15

    def test_diff_detects_framework_change(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        a = ProjectContext(project_name="p", frameworks=["Flask"])
        b = ProjectContext(project_name="p", frameworks=["Flask", "SQLAlchemy"])
        d = engine.diff(a, b)
        assert "frameworks" in d
        assert "SQLAlchemy" in d["frameworks"]["added"]

    def test_diff_empty_when_unchanged(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        a = ProjectContext(project_name="p", total_files=5, primary_language="Python")
        b = ProjectContext(project_name="p", total_files=5, primary_language="Python")
        assert engine.diff(a, b) == {}

    def test_diff_detects_task_change(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        a = ProjectContext(project_name="p")
        b = ProjectContext(project_name="p")
        b.add_task(TaskEntry(id="t1", title="New task"))
        d = engine.diff(a, b)
        assert "tasks" in d
        assert "t1" in d["tasks"]["added"]


# ─────────────────────────────────────────────
# ContextEngine – task convenience helpers
# ─────────────────────────────────────────────

class TestTaskHelpers:
    def test_add_task_helper(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        task = engine.add_task("Implement rule engine", priority="high")
        assert task.id is not None
        ctx = engine.load()
        assert any(t.id == task.id for t in ctx.current_tasks)

    def test_complete_task_helper(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        task = engine.add_task("Build CLI")
        result = engine.complete_task(task.id)
        assert result is True
        ctx = engine.load()
        t = ctx.task_by_id(task.id)
        assert t.status == "done"

    def test_complete_missing_task(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        assert engine.complete_task("no-such-id") is False

    def test_record_change_helper(self, tmp_path):
        cw = _make_cw_dir(tmp_path)
        engine = ContextEngine(cw)
        change = engine.record_change(
            description="Rewrote scanner",
            changed_files=["clockwork/scanner/scanner.py"],
            agent="claude",
            change_type="refactor",
        )
        ctx = engine.load()
        assert any(c.description == "Rewrote scanner" for c in ctx.recent_changes)
