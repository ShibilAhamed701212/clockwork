"""
Tests for Phase 4: CodebaseSummarizer.
"""
from __future__ import annotations

import pytest

from clockwork.brain.summarizer import CodebaseSummarizer


@pytest.fixture
def summarizer():
    return CodebaseSummarizer()


@pytest.fixture
def sample_scan_data():
    return {
        "project_name": "clockwork-src",
        "primary_language": "Python",
        "languages": {"Python": 80, "YAML": 10, "Markdown": 5},
        "frameworks": ["Typer", "pytest"],
        "total_files": 95,
        "total_lines": 12000,
        "entry_points": ["clockwork/cli/app.py", "pyproject.toml"],
        "test_files": ["tests/test_a.py", "tests/test_b.py"] * 10,  # 20 test files
        "config_files": ["pyproject.toml", ".clockwork/config.yaml"],
        "files": [
            {"path": "src/main.py", "symbols": [{"name": "main", "kind": "function"}], "imports": [], "is_test": False},
        ],
        "directory_tree": {
            "cli": ["app.py", "output.py"],
            "scanner": ["scanner.py", "models.py"],
            "brain": ["minibrain.py"],
            "context": ["engine.py", "models.py"],
            "graph": ["storage.py", "queries.py"],
        },
    }


class TestSummarize:
    def test_returns_string(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        assert isinstance(result, str)
        assert len(result) > 20

    def test_contains_project_name(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        assert "clockwork-src" in result

    def test_contains_language(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        assert "Python" in result

    def test_contains_framework(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        # Should mention at least one framework descriptor
        assert "typer" in result.lower() or "cli" in result.lower() or "framework" in result.lower()

    def test_contains_file_count(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        assert "95" in result

    def test_empty_data_no_crash(self, summarizer):
        result = summarizer.summarize({})
        assert isinstance(result, str)

    def test_test_coverage_mention(self, summarizer, sample_scan_data):
        result = summarizer.summarize(sample_scan_data)
        assert "test" in result.lower()


class TestArchitectureOverview:
    def test_returns_string(self, summarizer, sample_scan_data):
        result = summarizer.architecture_overview(sample_scan_data)
        assert isinstance(result, str)
        assert len(result) > 20

    def test_mentions_modules(self, summarizer, sample_scan_data):
        result = summarizer.architecture_overview(sample_scan_data)
        # Should mention some of the key modules
        assert "cli" in result.lower() or "scanner" in result.lower() or "Key modules" in result

    def test_mentions_framework(self, summarizer, sample_scan_data):
        result = summarizer.architecture_overview(sample_scan_data)
        assert "Typer" in result or "pytest" in result

    def test_empty_data_no_crash(self, summarizer):
        result = summarizer.architecture_overview({})
        assert isinstance(result, str)


class TestDetectConventions:
    def test_returns_list(self, summarizer, sample_scan_data):
        result = summarizer.detect_conventions(sample_scan_data)
        assert isinstance(result, list)

    def test_detects_pyproject(self, summarizer, sample_scan_data):
        result = summarizer.detect_conventions(sample_scan_data)
        assert any("pyproject" in c.lower() for c in result)

    def test_detects_testing_framework(self, summarizer, sample_scan_data):
        result = summarizer.detect_conventions(sample_scan_data)
        assert any("pytest" in c.lower() for c in result)

    def test_empty_data_no_crash(self, summarizer):
        result = summarizer.detect_conventions({})
        assert isinstance(result, list)
