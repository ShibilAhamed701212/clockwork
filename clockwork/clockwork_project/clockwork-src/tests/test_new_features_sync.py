from __future__ import annotations

import json
from pathlib import Path

import yaml

from clockwork.config.settings import load_settings
from clockwork.recovery.recovery_engine import RecoveryEngine
from clockwork.state.state_machine import StateMachine
from clockwork.state.state_manager import StateManager
from clockwork.validation.pipeline import ValidationPipeline


def _init_clockwork(root: Path) -> None:
    cw = root / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    (cw / "config.yaml").write_text(
        yaml.safe_dump({"mode": "balanced", "autonomy": "partial", "validation": "moderate"}),
        encoding="utf-8",
    )
    (cw / "context.yaml").write_text(yaml.safe_dump({"repository": {"architecture": "cli"}}), encoding="utf-8")
    (cw / "repo_map.json").write_text(json.dumps({"relationships": {}, "architecture": {}}), encoding="utf-8")


def test_state_manager_uses_loaded_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_clockwork(tmp_path)

    settings = load_settings(tmp_path)
    manager = StateManager(settings)
    snapshot = manager.snapshot()

    assert snapshot["mode"] == "balanced"
    assert snapshot["autonomy"] == "partial"
    assert snapshot["validation"] == "moderate"


def test_state_machine_transition():
    machine = StateMachine()
    assert machine.transition("scanning")
    assert machine.transition("indexing")
    assert machine.current() == "indexing"


def test_recovery_engine_handles_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_clockwork(tmp_path)

    manager = StateManager(load_settings(tmp_path))
    engine = RecoveryEngine(state=manager)
    missing_file = tmp_path / "generated" / "new.json"
    resolved = engine.on_failure("missing_file", path=str(missing_file), severity="medium")

    assert resolved
    assert missing_file.exists()


def test_validation_pipeline_flags_unsafe_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _init_clockwork(tmp_path)

    context = yaml.safe_load((tmp_path / ".clockwork" / "context.yaml").read_text(encoding="utf-8"))
    pipeline = ValidationPipeline(context=context)
    result = pipeline.run(
        {
            "success": True,
            "proposed_changes": [{"file": "../escape.py", "content": "print('x')"}],
        }
    )

    assert not result.passed
    assert any("Unsafe file path" in msg for msg in result.errors)


def test_recovery_and_state_use_repo_root_not_cwd(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo_root.mkdir(parents=True)
    outside.mkdir(parents=True)
    _init_clockwork(repo_root)

    monkeypatch.chdir(outside)

    settings = load_settings(repo_root)
    manager = StateManager(settings, repo_root=repo_root)
    manager.persist()
    assert (repo_root / ".clockwork" / "state.json").exists()
    assert not (outside / ".clockwork" / "state.json").exists()

    engine = RecoveryEngine(state=manager, repo_root=repo_root)
    resolved = engine.on_failure("missing_file", path="generated/inside.json", severity="medium")
    assert resolved
    assert (repo_root / "generated" / "inside.json").exists()
    assert not (outside / "generated" / "inside.json").exists()


