"""
tests/test_v2_improvements.py
-------------------------------
Tests for Clockwork v2.1 gap fixes:
  - Version consistency
  - IDE file import in --from-existing
  - _preserve_fields formalization in ContextEngine
"""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import pytest


# ── Version consistency ───────────────────────────────────────────────────

class TestVersionConsistency:
    """All version constants must match pyproject.toml."""

    def test_context_models_version(self):
        from clockwork.context.models import CLOCKWORK_VERSION
        assert CLOCKWORK_VERSION == "0.2.0"

    def test_packaging_models_version(self):
        from clockwork.packaging.models import CLOCKWORK_VERSION
        assert CLOCKWORK_VERSION == "0.2.0"

    def test_pyproject_version(self):
        """pyproject.toml version should be 0.2.0."""
        import tomllib
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            assert data["project"]["version"] == "0.2.0"

    def test_init_template_version(self):
        """The init template should emit the current version."""
        from clockwork.cli.commands.init import _CONTEXT_YAML
        assert 'clockwork_version: "0.2.0"' in _CONTEXT_YAML


# ── IDE file import ───────────────────────────────────────────────────────

class TestIDEFileImport:
    """Tests for _import_ide_rules in init.py."""

    def test_import_from_claude_md(self, tmp_path: Path):
        """Rules from CLAUDE.md should be appended to rules.md."""
        from clockwork.cli.commands.init import _import_ide_rules

        # Create a CLAUDE.md with rules
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "# Project\n\n"
            "## Conventions\n\n"
            "- Always use type hints\n"
            "- Never use bare except\n"
            "- Some non-directive line\n"
            "- Use pathlib for all paths\n",
            encoding="utf-8",
        )

        # Create .clockwork with existing rules.md
        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        rules_path.write_text(
            "# Rules\n\n- Do not modify .clockwork/\n",
            encoding="utf-8",
        )

        _import_ide_rules(tmp_path, cw_dir, ["CLAUDE.md"])

        content = rules_path.read_text(encoding="utf-8")
        assert "Imported from Existing IDE Files" in content
        assert "- Always use type hints" in content
        assert "- Never use bare except" in content
        assert "- Use pathlib for all paths" in content
        # Non-directive line should NOT be imported
        assert "Some non-directive line" not in content

    def test_import_skips_duplicates(self, tmp_path: Path):
        """Rules already in rules.md should not be duplicated."""
        from clockwork.cli.commands.init import _import_ide_rules

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "- Do not modify .clockwork/\n"
            "- Always use type hints\n",
            encoding="utf-8",
        )

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        rules_path.write_text(
            "# Rules\n\n- Do not modify .clockwork/\n",
            encoding="utf-8",
        )

        _import_ide_rules(tmp_path, cw_dir, ["CLAUDE.md"])

        content = rules_path.read_text(encoding="utf-8")
        # "Do not modify .clockwork/" should appear only once (original)
        count = content.lower().count("do not modify .clockwork/")
        assert count == 1
        # But the new "Always use type hints" should be added
        assert "- Always use type hints" in content

    def test_import_from_cursorrules(self, tmp_path: Path):
        """Rules from .cursorrules should also be imported."""
        from clockwork.cli.commands.init import _import_ide_rules

        cursorrules = tmp_path / ".cursorrules"
        cursorrules.write_text(
            "- Prefer composition over inheritance\n"
            "- Use snake_case for functions\n",
            encoding="utf-8",
        )

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        rules_path.write_text("# Rules\n", encoding="utf-8")

        _import_ide_rules(tmp_path, cw_dir, [".cursorrules"])

        content = rules_path.read_text(encoding="utf-8")
        assert "- Prefer composition over inheritance" in content
        assert "- Use snake_case for functions" in content

    def test_import_no_rules_found(self, tmp_path: Path):
        """When no directive rules are found, rules.md should not be modified."""
        from clockwork.cli.commands.init import _import_ide_rules

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text(
            "# Project\n\nJust a description.\n",
            encoding="utf-8",
        )

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        original = "# Rules\n"
        rules_path.write_text(original, encoding="utf-8")

        _import_ide_rules(tmp_path, cw_dir, ["CLAUDE.md"])

        assert rules_path.read_text(encoding="utf-8") == original

    def test_import_missing_ide_file(self, tmp_path: Path):
        """Missing IDE files should be silently skipped."""
        from clockwork.cli.commands.init import _import_ide_rules

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        original = "# Rules\n"
        rules_path.write_text(original, encoding="utf-8")

        # This should not raise
        _import_ide_rules(tmp_path, cw_dir, ["CLAUDE.md", ".cursorrules"])
        assert rules_path.read_text(encoding="utf-8") == original

    def test_import_multiple_files(self, tmp_path: Path):
        """Rules from both CLAUDE.md and .cursorrules should be merged."""
        from clockwork.cli.commands.init import _import_ide_rules

        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("- Always use type hints\n", encoding="utf-8")

        cursorrules = tmp_path / ".cursorrules"
        cursorrules.write_text("- Never use global state\n", encoding="utf-8")

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()
        rules_path = cw_dir / "rules.md"
        rules_path.write_text("# Rules\n", encoding="utf-8")

        _import_ide_rules(tmp_path, cw_dir, ["CLAUDE.md", ".cursorrules"])

        content = rules_path.read_text(encoding="utf-8")
        assert "- Always use type hints" in content
        assert "- Never use global state" in content


# ── _preserve_fields in ContextEngine ─────────────────────────────────────

class TestPreserveFields:
    """ContextEngine must declare explicit field preservation."""

    def test_preserve_fields_constant_exists(self):
        from clockwork.context.engine import ContextEngine
        assert hasattr(ContextEngine, "_PRESERVE_FIELDS")
        assert isinstance(ContextEngine._PRESERVE_FIELDS, frozenset)

    def test_scanner_fields_constant_exists(self):
        from clockwork.context.engine import ContextEngine
        assert hasattr(ContextEngine, "_SCANNER_FIELDS")
        assert isinstance(ContextEngine._SCANNER_FIELDS, frozenset)

    def test_preserve_fields_includes_critical_fields(self):
        from clockwork.context.engine import ContextEngine
        for field in ("summary", "architecture_overview", "current_tasks", "agent_notes"):
            assert field in ContextEngine._PRESERVE_FIELDS

    def test_scanner_fields_includes_scan_derived(self):
        from clockwork.context.engine import ContextEngine
        for field in ("primary_language", "frameworks", "total_files", "entry_points"):
            assert field in ContextEngine._SCANNER_FIELDS

    def test_no_overlap(self):
        """Preserve and scanner field sets must be disjoint."""
        from clockwork.context.engine import ContextEngine
        overlap = ContextEngine._PRESERVE_FIELDS & ContextEngine._SCANNER_FIELDS
        assert not overlap, f"Fields in both sets: {overlap}"

    def test_merge_scan_preserves_summary(self, tmp_path: Path):
        """merge_scan must not overwrite a non-empty summary."""
        from clockwork.context.engine import ContextEngine
        from clockwork.scanner.models import ScanResult
        import yaml

        cw_dir = tmp_path / ".clockwork"
        cw_dir.mkdir()

        # Write context with a human-authored summary
        ctx_data = {
            "clockwork_version": "0.2.0",
            "memory_schema_version": 1,
            "project_name": "test",
            "summary": "Manually written project description",
            "architecture_overview": "Custom arch overview",
            "primary_language": "Python",
            "frameworks": [],
            "entry_points": [],
            "total_files": 0,
            "total_lines": 0,
            "current_tasks": [],
            "recent_changes": [],
            "architecture_notes": [],
        }
        (cw_dir / "context.yaml").write_text(
            yaml.dump(ctx_data), encoding="utf-8"
        )

        engine = ContextEngine(cw_dir)
        scan = ScanResult(
            project_name="test",
            primary_language="TypeScript",
            total_files=42,
            total_lines=5000,
        )

        result = engine.merge_scan(scan)

        # Scanner fields SHOULD be updated
        assert result.primary_language == "TypeScript"
        assert result.total_files == 42

        # Preserved fields SHOULD NOT be overwritten
        assert result.summary == "Manually written project description"
        assert result.architecture_overview == "Custom arch overview"
