"""
tests/test_brain.py

Unit tests for the Clockwork Brain subsystem.

Run with:
    pytest tests/test_brain.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.brain.base import BrainResult, BrainStatus, RiskLevel
from clockwork.brain.brain_manager import BrainManager
from clockwork.brain.external_brain import ExternalBrain
from clockwork.brain.minibrain import MiniBrain
from clockwork.brain.ollama_brain import OllamaBrain


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_context(**overrides: Any) -> dict[str, Any]:
    base = {
        "project": "test_project",
        "frameworks": ["flask", "sqlalchemy"],
        "modules": ["clockwork.brain", "clockwork.scanner"],
    }
    base.update(overrides)
    return base


def make_diff(
    added: list[str] | None = None,
    deleted: list[str] | None = None,
    modified: list[str] | None = None,
    file_contents: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "added":         added         or [],
        "deleted":       deleted       or [],
        "modified":      modified      or [],
        "file_contents": file_contents or {},
    }


EMPTY_RULES: list[dict[str, Any]] = []


# ---------------------------------------------------------------------------
# BrainResult
# ---------------------------------------------------------------------------

class TestBrainResult:
    def test_to_dict_keys(self) -> None:
        r = BrainResult(BrainStatus.VALID, 0.9, RiskLevel.LOW, "All good.")
        assert set(r.to_dict().keys()) == {"status","confidence","risk_level","explanation","violations","warnings"}

    def test_passed_valid(self)    -> None: assert BrainResult(BrainStatus.VALID,    0.9, RiskLevel.LOW, "").passed is True
    def test_passed_warning(self)  -> None: assert BrainResult(BrainStatus.WARNING,  0.6, RiskLevel.LOW, "").passed is True
    def test_not_passed_rejected(self) -> None: assert BrainResult(BrainStatus.REJECTED, 0.9, RiskLevel.HIGH, "").passed is False


# ---------------------------------------------------------------------------
# MiniBrain
# ---------------------------------------------------------------------------

class TestMiniBrain:
    def setup_method(self) -> None:
        self.brain = MiniBrain()
        self.ctx   = make_context()

    def test_clean_diff_valid(self) -> None:
        result = self.brain.analyze_change(self.ctx, make_diff(modified=["clockwork/scanner/scanner.py"]), EMPTY_RULES)
        assert result.status == BrainStatus.VALID

    def test_core_deletion_rejected(self) -> None:
        result = self.brain.analyze_change(self.ctx, make_diff(deleted=["clockwork/brain/__init__.py"]), EMPTY_RULES)
        assert result.status == BrainStatus.REJECTED
        assert any("core module deletion" in v.lower() for v in result.violations)

    def test_missing_framework_in_requirements(self) -> None:
        diff = make_diff(modified=["requirements.txt"], file_contents={"requirements.txt": "requests==2.31.0\n"})
        result = self.brain.analyze_change(self.ctx, diff, EMPTY_RULES)
        assert result.status == BrainStatus.REJECTED
        assert any("flask" in v.lower() for v in result.violations)

    def test_frontend_db_import_rejected(self) -> None:
        code = "import sqlalchemy\n"
        diff = make_diff(modified=["frontend/views.py"], file_contents={"frontend/views.py": code})
        result = self.brain.analyze_change(self.ctx, diff, EMPTY_RULES)
        assert result.status == BrainStatus.REJECTED
        assert any("architecture violation" in v.lower() for v in result.violations)

    def test_context_yaml_modified_warning(self) -> None:
        diff = make_diff(modified=[".clockwork/context.yaml"])
        result = self.brain.analyze_change(self.ctx, diff, EMPTY_RULES)
        assert any("context.yaml" in w for w in result.warnings)

    def test_path_rule_violation(self) -> None:
        rules = [{"id": "no-env","description": "No .env","pattern": r"\.env$","applies_to": "path"}]
        result = self.brain.analyze_change(self.ctx, make_diff(added=[".env"]), rules)
        assert result.status == BrainStatus.REJECTED

    def test_content_rule_violation(self) -> None:
        rules = [{"id": "no-secrets","description": "No hardcoded keys","pattern": r"API_KEY\s*=\s*['\"][^'\"]{8,}['\"]","applies_to": "content"}]
        diff  = make_diff(modified=["config.py"], file_contents={"config.py": 'API_KEY = "supersecretvalue123"\n'})
        result = self.brain.analyze_change(self.ctx, diff, rules)
        assert result.status == BrainStatus.REJECTED

    def test_new_module_warning(self) -> None:
        diff   = make_diff(added=["clockwork/new_feature/processor.py"])
        result = self.brain.analyze_change(self.ctx, diff, EMPTY_RULES)
        assert any("new module introduced" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# OllamaBrain (mocked HTTP)
# ---------------------------------------------------------------------------

class TestOllamaBrain:
    def _mock_resp(self, payload: dict[str, Any]) -> MagicMock:
        resp = MagicMock()
        resp.read.return_value = json.dumps({"response": json.dumps(payload)}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__  = MagicMock(return_value=False)
        return resp

    def test_valid_response(self) -> None:
        payload = {"status":"VALID","confidence":0.88,"risk_level":"low","explanation":"ok","violations":[],"warnings":[]}
        with patch("urllib.request.urlopen", return_value=self._mock_resp(payload)):
            result = OllamaBrain().analyze_change(make_context(), make_diff(), EMPTY_RULES)
        assert result.status == BrainStatus.VALID

    def test_network_error_returns_warning(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("refused")):
            result = OllamaBrain().analyze_change(make_context(), make_diff(), EMPTY_RULES)
        assert result.status == BrainStatus.WARNING


# ---------------------------------------------------------------------------
# ExternalBrain (mocked HTTP)
# ---------------------------------------------------------------------------

class TestExternalBrain:
    def _make(self, provider: str = "openai") -> ExternalBrain:
        return ExternalBrain({"provider": provider, "model": "gpt-4o", "api_key": "test"})

    def _openai_resp(self, payload: dict[str, Any]) -> MagicMock:
        body = {"choices": [{"message": {"content": json.dumps(payload)}}]}
        resp = MagicMock()
        resp.read.return_value = json.dumps(body).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__  = MagicMock(return_value=False)
        return resp

    def test_openai_valid(self) -> None:
        payload = {"status":"VALID","confidence":0.91,"risk_level":"low","explanation":"ok","violations":[],"warnings":[]}
        with patch("urllib.request.urlopen", return_value=self._openai_resp(payload)):
            result = self._make("openai").analyze_change(make_context(), make_diff(), EMPTY_RULES)
        assert result.status == BrainStatus.VALID

    def test_api_failure_returns_warning(self) -> None:
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = self._make().analyze_change(make_context(), make_diff(), EMPTY_RULES)
        assert result.status == BrainStatus.WARNING


# ---------------------------------------------------------------------------
# BrainManager
# ---------------------------------------------------------------------------

class TestBrainManager:
    def setup_method(self) -> None:
        self.manager = BrainManager.__new__(BrainManager)
        self.manager._clockwork_dir = Path("/nonexistent/.clockwork")
        self.manager._config        = {}

    def test_clean_diff_valid(self) -> None:
        assert self.manager.run(make_context(), make_diff(), EMPTY_RULES).status == BrainStatus.VALID

    def test_core_deletion_rejected(self) -> None:
        diff = make_diff(deleted=["clockwork/__init__.py"])
        assert self.manager.run(make_context(), diff, EMPTY_RULES).status == BrainStatus.REJECTED

    def test_merge_prefers_rejected(self) -> None:
        valid    = BrainResult(BrainStatus.VALID,    0.9, RiskLevel.LOW,  "ok")
        rejected = BrainResult(BrainStatus.REJECTED, 0.95, RiskLevel.HIGH, "bad", violations=["v1"])
        merged   = BrainManager._merge(valid, rejected)
        assert merged.status == BrainStatus.REJECTED
        assert "v1" in merged.violations

    def test_merge_averages_confidence(self) -> None:
        a = BrainResult(BrainStatus.VALID,   0.8, RiskLevel.LOW, "ok")
        b = BrainResult(BrainStatus.WARNING, 0.6, RiskLevel.LOW, "hmm")
        assert BrainManager._merge(a, b).confidence == pytest.approx(0.7)
