from __future__ import annotations

from pathlib import Path


def test_agents_compat_imports():
    from clockwork.agents.agent_registry import AgentRegistry
    from clockwork.agents.router import Router
    from clockwork.agents.task_queue import TaskItem, TaskQueue

    registry = AgentRegistry()
    router = Router(registry)
    queue = TaskQueue()
    task = TaskItem(name="scan repo", action={"type": "scan", "target": "."})
    queue.push(task)

    routed = router.route(task.to_dict())
    assert routed is not None


def test_context_compat_imports_and_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".clockwork").mkdir(parents=True, exist_ok=True)

    from clockwork.context.context_engine import ContextEngine

    engine = ContextEngine(repo_root=tmp_path)
    snapshot = engine.snapshot()
    assert isinstance(snapshot, dict)


def test_live_index_queue_and_sync_types():
    from clockwork.context.live_index.event_queue import EventQueue
    from clockwork.context.live_index.sync_engine import SyncEngine

    queue = EventQueue()
    queue.push({"type": "modified", "path": "a.py"})
    queue.push({"type": "modified", "path": "a.py"})
    events = queue.drain_deduped()
    assert len(events) == 1

    engine = SyncEngine(root=".")
    assert isinstance(engine.stats(), dict)


def test_graph_anomaly_detector_no_crash(tmp_path):
    from clockwork.graph.node_manager import NodeManager
    from clockwork.graph.anomaly_detector import AnomalyDetector

    db = tmp_path / "kg.db"
    manager = NodeManager(db)
    manager.upsert("file", "orphan.py", "orphan.py", "Python", "")

    detector = AnomalyDetector(db)
    result = detector.detect_all()

    assert "circular_dependencies" in result
    assert "orphan_modules" in result


def test_cli_utils_parser():
    from clockwork.cli.utils.parser import parse_kv_pairs

    parsed = parse_kv_pairs(["a=1", "b=two", "flag"])
    assert parsed["a"] == "1"
    assert parsed["b"] == "two"
    assert parsed["flag"] == ""
