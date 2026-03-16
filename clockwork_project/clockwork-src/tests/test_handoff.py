"""
tests/test_handoff.py
Unit tests for the Clockwork Agent Handoff subsystem.
Run with:  pytest tests/test_handoff.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from clockwork.handoff import HandoffEngine, validate_before_handoff
from clockwork.handoff.aggregator import aggregate_handoff_data
from clockwork.handoff.brief_generator import render_brief
from clockwork.handoff.logger import log_handoff
from clockwork.handoff.models import HandoffData


@pytest.fixture()
def clockwork_dir(tmp_path: Path) -> Path:
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text(
        yaml.dump({
            "project_name": "test_project",
            "architecture": "layered",
            "current_summary": "Authentication module implemented.",
            "task_state": "in_progress",
        }), encoding="utf-8",
    )
    (cw / "repo_map.json").write_text(
        json.dumps({"languages": ["Python", "SQL"], "frameworks": ["Flask", "SQLAlchemy"]}),
        encoding="utf-8",
    )
    (cw / "tasks.json").write_text(
        json.dumps([{"description": "Add password reset functionality", "status": "open"}]),
        encoding="utf-8",
    )
    (cw / "skills.json").write_text(json.dumps(["Python", "Flask", "SQL"]), encoding="utf-8")
    (cw / "rules.md").write_text("# Rules\nFollow architecture boundaries.", encoding="utf-8")
    return cw


@pytest.fixture()
def repo_root(clockwork_dir: Path) -> Path:
    return clockwork_dir.parent


def test_handoff_data_to_dict():
    data = HandoffData(project="proj", architecture="layered", current_summary="Done.",
                       next_task="Add reset.", skills_required=["Python"],
                       rules_reference=".clockwork/rules.md")
    d = data.to_dict()
    assert d["project"] == "proj"
    assert "generated_at" in d


def test_aggregate_reads_context(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    assert data.project == "test_project"
    assert "Authentication" in data.current_summary


def test_aggregate_reads_tasks(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    assert "password reset" in data.next_task.lower()


def test_aggregate_reads_skills(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    assert "Python" in data.skills_required


def test_aggregate_strips_sensitive_context(tmp_path):
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text(
        yaml.dump({"project_name": "secure", "api_key": "SECRET123", "architecture": "mono",
                   "current_summary": "OK"}), encoding="utf-8")
    data = aggregate_handoff_data(cw)
    assert "SECRET123" not in json.dumps(data.to_dict())


def test_render_brief_contains_sections(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    brief = render_brief(data)
    for section in ["## Project Summary", "## Next Task", "## Skills Required",
                    "## Architecture", "## Rules"]:
        assert section in brief


def test_validation_passes_on_good_dir(clockwork_dir):
    result = validate_before_handoff(clockwork_dir)
    assert result.passed


def test_validation_fails_without_clockwork_dir(tmp_path):
    result = validate_before_handoff(tmp_path / ".clockwork")
    assert not result.passed


def test_validation_errors_on_bad_validation_log(clockwork_dir):
    log = [{"status": "failed", "reason": "Schema modified without migration"}]
    (clockwork_dir / "validation_log.json").write_text(json.dumps(log), encoding="utf-8")
    result = validate_before_handoff(clockwork_dir)
    assert not result.passed


def test_log_creates_file(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    log_handoff(clockwork_dir, data, target_agent="Claude")
    entries = json.loads((clockwork_dir / "handoff_log.json").read_text())
    assert len(entries) == 1
    assert entries[0]["handoff_to"] == "Claude"


def test_log_appends_entries(clockwork_dir):
    data = aggregate_handoff_data(clockwork_dir)
    log_handoff(clockwork_dir, data, target_agent="Claude")
    log_handoff(clockwork_dir, data, target_agent="GPT-4")
    entries = json.loads((clockwork_dir / "handoff_log.json").read_text())
    assert len(entries) == 2


def test_engine_run_produces_files(repo_root):
    engine = HandoffEngine(repo_root=repo_root)
    success, msg = engine.run(target_agent="Claude")
    assert success, msg
    handoff_dir = repo_root / ".clockwork" / "handoff"
    assert (handoff_dir / "handoff.json").exists()
    assert (handoff_dir / "next_agent_brief.md").exists()


def test_engine_handoff_json_is_valid(repo_root):
    HandoffEngine(repo_root=repo_root).run(target_agent="Claude")
    data = json.loads((repo_root / ".clockwork" / "handoff" / "handoff.json").read_text())
    assert data["project"] == "test_project"
    assert "next_task" in data


def test_engine_fails_without_init(tmp_path):
    success, msg = HandoffEngine(repo_root=tmp_path).run()
    assert not success