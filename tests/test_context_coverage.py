"""
tests/test_context_coverage.py
---------------------------
Tests for context module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.context.context_engine import ContextEngine


class TestContextEngine:
    def test_init(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        engine = ContextEngine(repo_root=tmp_path)
        assert engine.repo_root == tmp_path

    def test_snapshot(self, tmp_path):
        cw = tmp_path / ".clockwork"
        cw.mkdir(parents=True, exist_ok=True)
        engine = ContextEngine(repo_root=tmp_path)
        snapshot = engine.snapshot()
        assert isinstance(snapshot, dict)
