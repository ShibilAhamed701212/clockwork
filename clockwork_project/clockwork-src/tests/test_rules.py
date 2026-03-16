"""
Tests for the Clockwork Rule Engine subsystem.
"""
from __future__ import annotations
import json
from pathlib import Path
import pytest
import yaml
from clockwork.rules.engine import RuleEngine
from clockwork.rules.evaluators import (
    ArchitectureEvaluator, ContextEvaluator, DevelopmentEvaluator, SafetyEvaluator,
)
from clockwork.rules.loader import RuleLoader
from clockwork.rules.models import (
    RuleCategory, RuleConfig, RuleReport, RuleSeverity, RuleViolation,
)


@pytest.fixture()
def tmp_repo(tmp_path: Path) -> Path:
    (tmp_path / ".clockwork").mkdir()
    return tmp_path

@pytest.fixture()
def default_config() -> RuleConfig:
    return RuleConfig()

@pytest.fixture()
def engine(tmp_repo: Path) -> RuleEngine:
    return RuleEngine(repo_root=tmp_repo)


class TestRuleConfig:
    def test_default_values(self, default_config):
        assert default_config.forbid_core_file_deletion is True
        assert default_config.require_tests_for_new_modules is True
        assert ".clockwork/context.yaml" in default_config.protected_files

    def test_from_dict_partial(self):
        config = RuleConfig.from_dict({"rules": {"forbid_core_file_deletion": False}})
        assert config.forbid_core_file_deletion is False
        assert config.require_tests_for_new_modules is True

    def test_roundtrip(self, default_config):
        restored = RuleConfig.from_dict(default_config.to_dict())
        assert restored.protected_files == default_config.protected_files


class TestRuleLoader:
    def test_load_missing_returns_defaults(self, tmp_repo):
        config = RuleLoader(tmp_repo / ".clockwork").load()
        assert isinstance(config, RuleConfig)

    def test_write_defaults_creates_file(self, tmp_repo):
        cw = tmp_repo / ".clockwork"
        assert RuleLoader(cw).write_defaults() is True
        assert (cw / "rules.yaml").exists()

    def test_write_defaults_skips_if_exists(self, tmp_repo):
        cw = tmp_repo / ".clockwork"
        loader = RuleLoader(cw)
        loader.write_defaults()
        assert loader.write_defaults() is False

    def test_load_valid_yaml(self, tmp_repo):
        cw = tmp_repo / ".clockwork"
        (cw / "rules.yaml").write_text(
            yaml.dump({"rules": {"forbid_core_file_deletion": False}}), encoding="utf-8"
        )
        assert RuleLoader(cw).load().forbid_core_file_deletion is False


class TestSafetyEvaluator:
    def _ev(self, repo, config=None):
        return SafetyEvaluator(config or RuleConfig(), repo)

    def test_protected_file_blocked(self, tmp_repo):
        v = self._ev(tmp_repo).evaluate([".clockwork/context.yaml"], [])
        assert any(x.rule_id == "protected_file_modification" for x in v)

    def test_clean_file_passes(self, tmp_repo):
        assert self._ev(tmp_repo).evaluate(["src/main.py"], []) == []

    def test_protected_directory_blocked(self, tmp_repo):
        v = self._ev(tmp_repo).evaluate(["database/schema.sql"], [])
        assert any(x.rule_id == "protected_directory_modification" for x in v)

    def test_forbidden_pattern_env(self, tmp_repo):
        v = self._ev(tmp_repo).evaluate([".env"], [])
        assert any(x.rule_id == "forbidden_file_pattern" for x in v)

    def test_core_deletion_blocked(self, tmp_repo):
        v = self._ev(tmp_repo).evaluate([], [".clockwork/context.yaml"])
        assert any(x.rule_id == "core_file_deletion" for x in v)

    def test_deletion_disabled(self, tmp_repo):
        ev = self._ev(tmp_repo, RuleConfig(forbid_core_file_deletion=False))
        assert ev.evaluate([], [".clockwork/context.yaml"]) == []


class TestArchitectureEvaluator:
    def _ev(self, repo, config=None):
        return ArchitectureEvaluator(config or RuleConfig(), repo)

    def test_layer_violation(self, tmp_repo):
        (tmp_repo / "frontend").mkdir()
        (tmp_repo / "frontend" / "app.py").write_text("from database import models\n")
        v = self._ev(tmp_repo).evaluate(["frontend/app.py"], [])
        assert any(x.rule_id == "architecture_layer_violation" for x in v)

    def test_compliant_passes(self, tmp_repo):
        (tmp_repo / "backend").mkdir()
        (tmp_repo / "backend" / "svc.py").write_text("from api import client\n")
        assert self._ev(tmp_repo).evaluate(["backend/svc.py"], []) == []

    def test_disabled(self, tmp_repo):
        ev = self._ev(tmp_repo, RuleConfig(enforce_architecture_layers=False))
        assert ev.evaluate(["frontend/app.py"], []) == []


class TestDevelopmentEvaluator:
    def _ev(self, repo, config=None):
        return DevelopmentEvaluator(config or RuleConfig(), repo)

    def test_warns_missing_test(self, tmp_repo):
        (tmp_repo / "clockwork").mkdir()
        (tmp_repo / "clockwork" / "new.py").write_text("# new\n")
        v = self._ev(tmp_repo).evaluate(["clockwork/new.py"], [])
        assert any(x.rule_id == "missing_test_file" for x in v)
        assert all(x.severity == RuleSeverity.WARN for x in v if x.rule_id == "missing_test_file")

    def test_passes_when_test_exists(self, tmp_repo):
        (tmp_repo / "clockwork").mkdir()
        (tmp_repo / "clockwork" / "foo.py").write_text("# foo\n")
        (tmp_repo / "tests").mkdir()
        (tmp_repo / "tests" / "test_foo.py").write_text("# test\n")
        assert self._ev(tmp_repo).evaluate(["clockwork/foo.py"], []) == []

    def test_passes_when_test_in_changeset(self, tmp_repo):
        (tmp_repo / "clockwork").mkdir()
        (tmp_repo / "clockwork" / "bar.py").write_text("# bar\n")
        v = self._ev(tmp_repo).evaluate(["clockwork/bar.py", "tests/test_bar.py"], [])
        assert not any(x.rule_id == "missing_test_file" for x in v)

    def test_skips_init(self, tmp_repo):
        (tmp_repo / "clockwork").mkdir()
        assert self._ev(tmp_repo).evaluate(["clockwork/__init__.py"], []) == []

    def test_disabled(self, tmp_repo):
        ev = self._ev(tmp_repo, RuleConfig(require_tests_for_new_modules=False))
        assert ev.evaluate(["clockwork/new.py"], []) == []


class TestContextEvaluator:
    def _ev(self, repo):
        return ContextEvaluator(RuleConfig(), repo)

    def test_warns_managed_file(self, tmp_repo):
        v = self._ev(tmp_repo).evaluate([".clockwork/agent_history.json"], [])
        assert any(x.rule_id == "clockwork_memory_tampered" for x in v)

    def test_passes_non_managed(self, tmp_repo):
        assert self._ev(tmp_repo).evaluate(["src/main.py"], []) == []


class TestRuleReport:
    def test_passes_no_violations(self):
        assert RuleReport().passed is True

    def test_fails_blocking(self):
        v = RuleViolation("r", RuleCategory.SAFETY, RuleSeverity.BLOCK, "msg")
        assert RuleReport(violations=[v]).passed is False

    def test_passes_warn_only(self):
        v = RuleViolation("r", RuleCategory.DEVELOPMENT, RuleSeverity.WARN, "msg")
        assert RuleReport(violations=[v]).passed is True

    def test_passes_overridden(self):
        v = RuleViolation("r", RuleCategory.SAFETY, RuleSeverity.BLOCK, "msg", overridden=True)
        assert RuleReport(violations=[v]).passed is True


class TestRuleEngine:
    def test_clean_passes(self, engine):
        assert engine.evaluate(["src/utils.py"]).passed is True

    def test_protected_file_fails(self, engine):
        report = engine.evaluate([".clockwork/context.yaml"])
        assert not report.passed
        assert any(v.rule_id == "protected_file_modification" for v in report.blocking_violations)

    def test_rule_log_written(self, engine, tmp_repo):
        engine.evaluate(["src/foo.py"])
        log = json.loads((tmp_repo / ".clockwork" / "rule_log.json").read_text())
        assert len(log) >= 1

    def test_override_log_written(self, engine, tmp_repo):
        engine.record_override("rule_a", "emergency")
        log = json.loads((tmp_repo / ".clockwork" / "override_log.json").read_text())
        assert log[0]["rule_id"] == "rule_a"

    def test_empty_changeset_passes(self, engine):
        assert engine.evaluate([]).passed is True

    def test_config_accessible(self, engine):
        assert isinstance(engine.config, RuleConfig)
