"""
tests/test_validation.py
------------------------
Unit tests for the Validation subsystem.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.validation.output_validator import OutputValidator
from clockwork.validation.hallucination_guard import HallucinationGuard
from clockwork.state.session_tracker import SessionTracker


class TestOutputValidator:
    def test_validate_valid_output(self):
        ov = OutputValidator()
        output = {"success": True, "proposed_changes": []}
        ok, errors = ov.validate(output)
        assert ok is True
        assert errors == []

    def test_validate_missing_success(self):
        ov = OutputValidator()
        output = {"proposed_changes": []}
        ok, errors = ov.validate(output)
        assert ok is False
        assert any("success" in e for e in errors)

    def test_validate_invalid_type(self):
        ov = OutputValidator()
        ok, errors = ov.validate("not a dict")
        assert ok is False
        assert any("must be a dict" in e for e in errors)

    def test_validate_proposed_changes_not_list(self):
        ov = OutputValidator()
        output = {"success": True, "proposed_changes": "not a list"}
        ok, errors = ov.validate(output)
        assert ok is False

    def test_validate_change_missing_file(self):
        ov = OutputValidator()
        change = {"content": "new content"}
        errors = ov._validate_change(change, 0)
        assert any("missing 'file'" in e for e in errors)

    def test_validate_change_traversal(self):
        ov = OutputValidator()
        change = {"file": "../etc/passwd"}
        errors = ov._validate_change(change, 0)
        assert any("traversal" in e for e in errors)

    def test_validate_syntax_valid(self):
        ov = OutputValidator()
        code = "def hello():\n    print('world')"
        ok, msg = ov.validate_syntax(code, "python")
        assert ok is True

    def test_validate_syntax_invalid(self):
        ov = OutputValidator()
        code = "def hello(:\n    print('world')"
        ok, msg = ov.validate_syntax(code, "python")
        assert ok is False
        assert "SyntaxError" in msg

    def test_validate_json_valid(self):
        ov = OutputValidator()
        text = '{"key": "value"}'
        ok, msg = ov.validate_json(text)
        assert ok is True

    def test_validate_json_invalid(self):
        ov = OutputValidator()
        text = '{"key": }'
        ok, msg = ov.validate_json(text)
        assert ok is False

    def test_check_minimal_diff(self):
        ov = OutputValidator()
        original = "line1\nline2\nline3"
        proposed = "line1\nline2\nline3\nline4"
        result = ov.check_minimal_diff(original, proposed)
        assert result is True


class TestHallucinationGuard:
    def test_check_clean_output(self):
        hg = HallucinationGuard()
        ok, issues = hg.check_content("This is a valid output")
        assert ok is True
        assert issues == []

    def test_check_contains_placeholder(self):
        hg = HallucinationGuard()
        ok, issues = hg.check_content("TODO: implement this feature")
        assert ok is False

    def test_check_file_references_valid(self):
        hg = HallucinationGuard()
        changes = [{"file": "src/main.py"}]
        ok, issues = hg.check_file_references(changes)
        assert ok is True

    def test_score_clean(self):
        hg = HallucinationGuard()
        score = hg.score("This is valid content")
        assert score == 1.0

    def test_score_with_issues(self):
        hg = HallucinationGuard()
        score = hg.score("TODO: implement this")
        assert score < 1.0


class TestSessionTracker:
    def test_session_init(self, tmp_path):
        tracker = SessionTracker("test-session", tmp_path)
        assert tracker.session_id == "test-session"
        assert tracker.repo_root == tmp_path

    def test_log_event(self, tmp_path):
        tracker = SessionTracker("test-session", tmp_path)
        tracker.log("test_event", {"key": "value"})
        assert len(tracker.events) == 1

    def test_duration(self, tmp_path):
        import time

        tracker = SessionTracker("test-session", tmp_path)
        time.sleep(0.1)
        duration = tracker.duration()
        assert duration > 0

    def test_summary(self, tmp_path):
        tracker = SessionTracker("test-session", tmp_path)
        summary = tracker.summary()
        assert "session_id" in summary
        assert "duration_s" in summary
        assert "events" in summary
