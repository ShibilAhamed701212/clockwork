"""
tests/test_live_index_coverage.py
-------------------------------
Tests for live_index module.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.context.live_index.watcher import FileWatcher
from clockwork.context.live_index.sync_engine import SyncEngine


class TestFileWatcher:
    def test_watcher_init_with_callback(self):
        def on_event(event):
            pass

        fw = FileWatcher(root=".", on_event=on_event)
        assert fw is not None
        assert fw.is_running() is False

    def test_start_stop(self):
        def on_event(event):
            pass

        fw = FileWatcher(root=".", on_event=on_event)
        fw.start()
        assert fw.is_running() is True
        fw.stop()
        assert fw.is_running() is False


class TestSyncEngine:
    def test_sync_engine_init(self, tmp_path):
        se = SyncEngine(root=str(tmp_path))
        assert se is not None

    def test_stats(self, tmp_path):
        se = SyncEngine(root=str(tmp_path))
        stats = se.stats()
        assert isinstance(stats, dict)
