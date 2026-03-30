"""
tests/test_index.py
---------------------
Unit tests for the Live Context Index subsystem (spec §10).

Run with:
    pytest tests/test_index.py -v
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.index.models import (
    ChangeEvent, EventType, IndexEntry, IndexStats, compute_file_hash
)
from clockwork.index.storage import IndexStorage
from clockwork.index.incremental_scanner import IncrementalScanner, _detect_layer, _detect_module_type
from clockwork.index.index_engine import LiveContextIndex


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_storage(tmp_path: Path) -> IndexStorage:
    db = tmp_path / ".clockwork" / "index.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    s = IndexStorage(db)
    s.open()
    s.initialise()
    return s


def _make_repo(tmp_path: Path) -> Path:
    """Create a minimal fake repository with Python files."""
    cw = tmp_path / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)

    (tmp_path / "clockwork").mkdir()
    (tmp_path / "clockwork" / "__init__.py").write_text("")
    (tmp_path / "clockwork" / "scanner.py").write_text(
        "import os\nfrom pathlib import Path\nimport typer\n\nclass Scanner:\n    pass\n"
    )
    (tmp_path / "clockwork" / "models.py").write_text(
        "from dataclasses import dataclass\n\n@dataclass\nclass ScanResult:\n    pass\n"
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_scanner.py").write_text(
        "import pytest\nfrom clockwork.scanner import Scanner\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    return tmp_path


def _make_engine(tmp_path: Path) -> LiveContextIndex:
    _make_repo(tmp_path)
    return LiveContextIndex(tmp_path)


# ── IndexEntry / models ────────────────────────────────────────────────────

class TestIndexEntry:
    def test_to_dict_has_required_fields(self):
        e = IndexEntry(
            file_path="clockwork/scanner.py",
            last_modified=1000.0,
            file_hash="abc123",
            language="Python",
        )
        d = e.to_dict()
        assert "file_path"     in d
        assert "last_modified" in d
        assert "file_hash"     in d
        assert "language"      in d
        assert "dependencies"  in d

    def test_compute_file_hash_returns_hex(self, tmp_path):
        f = tmp_path / "a.py"
        f.write_text("hello")
        h = compute_file_hash(str(f))
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_compute_file_hash_changes_on_content(self, tmp_path):
        f = tmp_path / "b.py"
        f.write_text("version 1")
        h1 = compute_file_hash(str(f))
        f.write_text("version 2")
        h2 = compute_file_hash(str(f))
        assert h1 != h2

    def test_compute_file_hash_missing_file(self):
        h = compute_file_hash("/nonexistent/path.py")
        assert h == ""


# ── IndexStorage ───────────────────────────────────────────────────────────

class TestIndexStorage:
    def test_creates_db(self, tmp_path):
        s = _make_storage(tmp_path)
        s.close()
        assert (tmp_path / ".clockwork" / "index.db").exists()

    def test_upsert_and_get(self, tmp_path):
        s = _make_storage(tmp_path)
        entry = IndexEntry(
            file_path="clockwork/scanner.py",
            last_modified=1000.0,
            file_hash="abc",
            language="Python",
        )
        s.upsert(entry)
        s.commit()
        retrieved = s.get("clockwork/scanner.py")
        s.close()
        assert retrieved is not None
        assert retrieved.file_path == "clockwork/scanner.py"
        assert retrieved.language == "Python"

    def test_upsert_overwrites_existing(self, tmp_path):
        s = _make_storage(tmp_path)
        e1 = IndexEntry("a.py", 1000.0, "hash1", language="Python")
        e2 = IndexEntry("a.py", 2000.0, "hash2", language="Python")
        s.upsert(e1); s.commit()
        s.upsert(e2); s.commit()
        got = s.get("a.py")
        s.close()
        assert got.file_hash == "hash2"

    def test_delete(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("x.py", 1000.0, "h1"))
        s.commit()
        s.delete("x.py")
        s.commit()
        assert s.get("x.py") is None
        s.close()

    def test_count(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("a.py", 1.0, "h1"))
        s.upsert(IndexEntry("b.py", 2.0, "h2"))
        s.commit()
        assert s.count() == 2
        s.close()

    def test_has_changed_new_file(self, tmp_path):
        s = _make_storage(tmp_path)
        assert s.has_changed("new.py", 1000.0, "somehash") is True
        s.close()

    def test_has_changed_same_hash(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("f.py", 1000.0, "stablehash"))
        s.commit()
        assert s.has_changed("f.py", 2000.0, "stablehash") is False
        s.close()

    def test_has_changed_different_hash(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("f.py", 1000.0, "oldhash"))
        s.commit()
        assert s.has_changed("f.py", 1000.0, "newhash") is True
        s.close()

    def test_meta_roundtrip(self, tmp_path):
        s = _make_storage(tmp_path)
        s.set_meta("built_at", "2026-03-15")
        s.commit()
        assert s.get_meta("built_at") == "2026-03-15"
        s.close()

    def test_all_entries(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("a.py", 1.0, "h1"))
        s.upsert(IndexEntry("b.py", 2.0, "h2"))
        s.commit()
        entries = s.all_entries()
        s.close()
        paths = {e.file_path for e in entries}
        assert "a.py" in paths
        assert "b.py" in paths

    def test_drop_all_resets(self, tmp_path):
        s = _make_storage(tmp_path)
        s.upsert(IndexEntry("a.py", 1.0, "h1"))
        s.commit()
        s.drop_all()
        assert s.count() == 0
        s.close()


# ── IncrementalScanner ─────────────────────────────────────────────────────

class TestIncrementalScanner:
    def test_scan_python_file(self, tmp_path):
        f = tmp_path / "scanner.py"
        f.write_text("import os\nfrom pathlib import Path\nclass Scanner:\n    pass\n")
        scanner = IncrementalScanner()
        entry = scanner.scan_file(str(f), str(tmp_path))
        assert entry is not None
        assert entry.language == "Python"
        assert entry.file_hash != ""
        assert entry.size_bytes > 0

    def test_scan_extracts_python_imports(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("import typer\nfrom pathlib import Path\nfrom clockwork.scanner import Scanner\n")
        scanner = IncrementalScanner()
        entry = scanner.scan_file(str(f), str(tmp_path))
        deps = json.loads(entry.dependencies)
        assert "typer" in deps
        assert "pathlib" in deps

    def test_scan_yaml_file(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("key: value\n")
        entry = IncrementalScanner().scan_file(str(f), str(tmp_path))
        assert entry is not None
        assert entry.language == "YAML"
        assert entry.module_type == "config"

    def test_scan_missing_file_returns_none(self, tmp_path):
        entry = IncrementalScanner().scan_file(str(tmp_path / "ghost.py"), str(tmp_path))
        assert entry is None

    def test_scan_relative_path(self, tmp_path):
        sub = tmp_path / "clockwork"
        sub.mkdir()
        f = sub / "engine.py"
        f.write_text("pass")
        entry = IncrementalScanner().scan_file(str(f), str(tmp_path))
        assert "/" in entry.file_path
        assert not entry.file_path.startswith(str(tmp_path))

    def test_detect_layer_frontend(self):
        assert _detect_layer("frontend/app.js") == "frontend"

    def test_detect_layer_database(self):
        assert _detect_layer("db/models.py") == "database"

    def test_detect_module_type_test(self):
        assert _detect_module_type("tests/test_scanner.py") == "test"

    def test_detect_module_type_config(self):
        assert _detect_module_type("pyproject.toml") == "config"

    def test_detect_module_type_source(self):
        assert _detect_module_type("clockwork/scanner.py") == "source"


# ── LiveContextIndex ───────────────────────────────────────────────────────

class TestLiveContextIndex:
    def test_build_creates_index_db(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats  = engine.build()
        assert (tmp_path / ".clockwork" / "index.db").exists()
        assert stats.indexed_files > 0

    def test_build_stats_totals(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats  = engine.build()
        assert stats.total_files >= stats.indexed_files + stats.skipped_files

    def test_build_skips_unchanged_files(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats1 = engine.build()
        stats2 = engine.build()
        # second build should skip all files (nothing changed)
        assert stats2.skipped_files >= stats1.indexed_files

    def test_get_entry_after_build(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        entry = engine.get_entry("clockwork/scanner.py")
        assert entry is not None
        assert entry.language == "Python"

    def test_count_after_build(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        assert engine.count() > 0

    def test_all_entries_after_build(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        entries = engine.all_entries()
        paths = {e.file_path for e in entries}
        assert "clockwork/scanner.py" in paths

    def test_repair_wipes_and_rebuilds(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        count_before = engine.count()
        stats = engine.repair()
        assert stats.indexed_files > 0
        assert engine.count() == count_before

    def test_update_file_adds_new_entry(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()

        new_file = tmp_path / "clockwork" / "new_module.py"
        new_file.write_text("import os\nclass NewModule:\n    pass\n")

        engine.update_file(str(new_file))
        entry = engine.get_entry("clockwork/new_module.py")
        assert entry is not None
        assert entry.language == "Python"

    def test_update_file_handles_deletion(self, tmp_path):
        engine = _make_engine(tmp_path)
        engine.build()
        # update a path that doesn't exist → should remove from index
        engine.update_file(str(tmp_path / "clockwork" / "ghost.py"))
        assert engine.get_entry("clockwork/ghost.py") is None

    def test_elapsed_ms_reasonable(self, tmp_path):
        engine = _make_engine(tmp_path)
        stats  = engine.build()
        # small repo should build fast (spec §13: single file < 50ms, large < 500ms)
        assert stats.elapsed_ms < 5000  # generous upper bound for CI


# ── ChangeEvent ────────────────────────────────────────────────────────────

class TestChangeEvent:
    def test_to_dict(self):
        ev = ChangeEvent(
            event_type=EventType.MODIFIED,
            file_path="clockwork/scanner.py",
            timestamp=1000.0,
        )
        d = ev.to_dict()
        assert d["event_type"] == "modified"
        assert d["file_path"]  == "clockwork/scanner.py"
        assert d["timestamp"]  == 1000.0

