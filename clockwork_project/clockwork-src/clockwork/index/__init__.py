"""
clockwork/index/__init__.py
----------------------------
Live Context Index subsystem.

Turns Clockwork into a real-time repository intelligence system
by watching filesystem events and updating the index, graph, and
context engine incrementally — without full rescans.

Public API::

    from clockwork.index import LiveContextIndex

    engine = LiveContextIndex(repo_root=Path("."))
    stats  = engine.build()       # initial full index
    engine.watch()                # start real-time watching
    engine.stop()                 # stop watching

CLI commands added:
    clockwork index   — build / refresh the index
    clockwork repair  — wipe and rebuild from scratch
    clockwork watch   — start real-time monitoring
"""

from clockwork.index.index_engine import LiveContextIndex
from clockwork.index.models import (
    ChangeEvent,
    EventType,
    IndexEntry,
    IndexStats,
)

__all__ = [
    "LiveContextIndex",
    "ChangeEvent",
    "EventType",
    "IndexEntry",
    "IndexStats",
]

