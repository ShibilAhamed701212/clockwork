"""
tests/test_recovery_coverage.py
------------------------------
Tests for recovery module.
"""

from __future__ import annotations

import sys
from pathlib import Path
import json

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.recovery.self_healing import SelfHealing
from clockwork.recovery.rollback import RollbackManager
from clockwork.recovery.retry import RetryEngine


class TestSelfHealing:
    def test_init(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        sh = SelfHealing(repo_root=tmp_path)
        assert sh.repo_root == tmp_path

    def test_heal_scan_failure(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        sh = SelfHealing(repo_root=tmp_path)
        failure = {"type": "scan", "error": "not found"}
        result = sh.heal(failure)
        assert isinstance(result, bool)

    def test_heal_unknown_failure(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        sh = SelfHealing(repo_root=tmp_path)
        failure = {"type": "unknown", "error": "test"}
        result = sh.heal(failure)
        assert result is False


class TestRollbackManager:
    def test_init(self, tmp_path):
        rm = RollbackManager(repo_root=tmp_path)
        assert rm.repo_root == tmp_path

    def test_checkpoint(self, tmp_path):
        rm = RollbackManager(repo_root=tmp_path)
        checkpoint = rm.checkpoint("test")
        assert checkpoint is not None

    def test_list_checkpoints(self, tmp_path):
        rm = RollbackManager(repo_root=tmp_path)
        rm.checkpoint("test")
        checkpoints = rm.list_checkpoints()
        assert isinstance(checkpoints, list)

    def test_latest(self, tmp_path):
        rm = RollbackManager(repo_root=tmp_path)
        rm.checkpoint("test")
        latest = rm.latest()
        assert latest is not None


class TestRetryEngine:
    def test_init(self):
        re = RetryEngine()
        assert re.max_retries == 3

    def test_run_success(self):
        re = RetryEngine()

        def success():
            return "success"

        result = re.run(success)
        assert result == "success"

    def test_run_failure(self):
        re = RetryEngine()

        def fail():
            raise ValueError("test")

        result = re.run_safe(fail, default="failed")
        assert result == "failed"
