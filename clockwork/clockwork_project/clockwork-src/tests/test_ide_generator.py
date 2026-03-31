"""Tests for IDE context file generation."""
from pathlib import Path
import pytest
import yaml
from clockwork.context.ide_context_generator import IDEContextGenerator


@pytest.fixture
def gen(tmp_path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text(yaml.dump({
        "project_name": "myapp",
        "summary": "A test web application.",
        "primary_language": "Python",
        "frameworks": ["FastAPI", "SQLAlchemy"],
        "entry_points": ["main.py"],
        "current_tasks": [
            {"title": "Build login API", "status": "pending"},
        ],
    }), encoding="utf-8")
    (cw / "rules.md").write_text(
        "# Rules\n- Do not bypass the API layer.\n- Run tests before commit.\n",
        encoding="utf-8"
    )
    return IDEContextGenerator(tmp_path)


def test_generate_claude_md_contains_project_name(gen):
    ctx = gen._load_context()
    content = gen.generate_claude_md(ctx, gen._load_rules(), {})
    assert "myapp" in content
    assert "FastAPI" in content


def test_generate_claude_md_contains_rules(gen):
    ctx = gen._load_context()
    rules = gen._load_rules()
    content = gen.generate_claude_md(ctx, rules, {})
    assert "API layer" in content


def test_generate_cursorrules(gen):
    ctx = gen._load_context()
    content = gen.generate_cursorrules(ctx, gen._load_rules(), {})
    assert "myapp" in content
    assert "Python" in content


def test_generate_agents_md_has_tasks(gen):
    ctx = gen._load_context()
    content = gen.generate_agents_md(ctx, gen._load_rules(), {})
    assert "Build login API" in content


def test_generate_all_writes_files(gen, tmp_path):
    results = gen.generate_all()
    assert "claude.md" in results
    assert (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / ".cursorrules").exists()
