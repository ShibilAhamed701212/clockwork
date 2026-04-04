"""
Tests for Phase 3: IDE Context File Generation.
"""
from __future__ import annotations

import pytest

from clockwork.context.ide_context_generator import IDEContextGenerator


@pytest.fixture
def sample_context():
    return {
        "project_name": "TestProject",
        "summary": "A test project for validating context generation.",
        "architecture_overview": "Follows CLI architecture with modular commands.",
        "primary_language": "Python",
        "languages": {"Python": 50, "YAML": 10},
        "frameworks": ["Typer", "pytest"],
        "total_files": 60,
        "total_lines": 5000,
        "entry_points": ["main.py", "cli/app.py"],
        "clockwork_version": "0.2",
        "current_tasks": [
            {"title": "Add feature X", "status": "in_progress"},
            {"title": "Fix bug Y", "status": "done"},
        ],
    }


@pytest.fixture
def sample_rules():
    return """# Project Rules
- All new files must have docstrings
- Do not modify clockwork/ directory
- Tests must mirror source structure in tests/
"""


@pytest.fixture
def generator(tmp_path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    return IDEContextGenerator(tmp_path)


class TestCLAUDEMD:
    def test_generates_nonempty(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_project_name(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert "TestProject" in result

    def test_contains_tech_stack(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert "Python" in result
        assert "Typer" in result

    def test_contains_conventions(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert "docstrings" in result

    def test_contains_entry_points(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert "main.py" in result

    def test_contains_tasks(self, generator, sample_context, sample_rules):
        result = generator.generate_claude_md(sample_context, sample_rules)
        assert "Add feature X" in result

    def test_empty_context_no_crash(self, generator):
        result = generator.generate_claude_md({}, "")
        assert isinstance(result, str)


class TestCursorRules:
    def test_generates_nonempty(self, generator, sample_context, sample_rules):
        result = generator.generate_cursorrules(sample_context, sample_rules)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_contains_project_name(self, generator, sample_context, sample_rules):
        result = generator.generate_cursorrules(sample_context, sample_rules)
        assert "TestProject" in result

    def test_contains_conventions(self, generator, sample_context, sample_rules):
        result = generator.generate_cursorrules(sample_context, sample_rules)
        assert "docstrings" in result


class TestAgentsMD:
    def test_generates_nonempty(self, generator, sample_context, sample_rules):
        result = generator.generate_agents_md(sample_context, sample_rules)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_contains_frameworks(self, generator, sample_context, sample_rules):
        result = generator.generate_agents_md(sample_context, sample_rules)
        assert "Typer" in result or "pytest" in result


class TestCopilotInstructions:
    def test_generates_nonempty(self, generator, sample_context, sample_rules):
        result = generator.generate_copilot_instructions(sample_context, sample_rules)
        assert isinstance(result, str)
        assert len(result) > 30

    def test_contains_language(self, generator, sample_context, sample_rules):
        result = generator.generate_copilot_instructions(sample_context, sample_rules)
        assert "Python" in result
