from __future__ import annotations

import time
from pathlib import Path

import pytest


def test_v2_agents_registry_and_router():
    from clockwork.agents.agent_registry import AgentRegistry
    from clockwork.agents.router import Router

    registry = AgentRegistry()
    router = Router(registry)
    task = {"name": "scan_repo", "action": {"type": "scan", "target": "."}}
    agent = router.route(task)

    assert agent is not None
    assert len(registry.all()) > 0


def test_v2_graph_stack(tmp_path):
    from clockwork.graph.node_manager import NodeManager
    from clockwork.graph.edge_manager import EdgeManager
    from clockwork.graph.query_engine import QueryEngine
    from clockwork.graph.anomaly_detector import AnomalyDetector
    from clockwork.graph.graph_builder import GraphBuilder

    db_path = tmp_path / "test_graph.db"
    nodes = NodeManager(db_path)
    edges = EdgeManager(db_path)
    query = QueryEngine(db_path)

    src = nodes.upsert("file", "app.py", "app.py", "Python", "backend")
    tgt = nodes.upsert("module", "database.py", "database.py", "Python", "database")
    assert src > 0 and tgt > 0

    edges.add(src, tgt, "imports", "app.py", "database.py")
    assert len(edges.get_outgoing(src)) == 1
    assert len(query.dependencies_of("app.py")) >= 1

    detector = AnomalyDetector(db_path)
    summary = detector.detect_all()
    assert "circular_dependencies" in summary

    builder = GraphBuilder(db_path)
    repo_map = {
        "relationships": {"graph": {"app.py": {"imports": ["database.py"]}, "database.py": {"imports": []}}},
        "dependencies": {"dependencies": [{"name": "flask"}]},
        "components": {"backend": ["app.py"]},
    }
    built = builder.build_from_repo_map(repo_map)
    assert built["total_nodes"] > 0


def test_v2_recovery_stack(tmp_path, monkeypatch):
    from clockwork.context.live_index.event_queue import EventQueue
    from clockwork.context.live_index.incremental_processor import FileIndex, IncrementalProcessor
    from clockwork.recovery.rollback import RollbackManager
    from clockwork.recovery.retry import RetryEngine
    from clockwork.recovery.predictor import FailurePredictor

    monkeypatch.chdir(tmp_path)
    cw = tmp_path / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)

    queue = EventQueue()
    queue.push({"type": "modified", "path": "requirements.txt", "ts": time.time()})
    queue.push({"type": "modified", "path": "service.py", "ts": time.time()})
    events = queue.drain_deduped()
    assert any(event["priority"] == "high" for event in events)

    idx = FileIndex(tmp_path / "idx.db")
    idx.upsert("app.py", "abc123", 1000.0, "module", "", "Python")
    assert idx.get("app.py")["hash"] == "abc123"
    idx.delete("app.py")
    assert idx.get("app.py") is None

    proc = IncrementalProcessor(repo_root=tmp_path)
    proc.index = FileIndex(tmp_path / "inc.db")
    mod = tmp_path / "mod.py"
    mod.write_text("import os\n", encoding="utf-8")
    assert proc.process_event({"type": "modified", "path": str(mod), "ts": time.time()})
    assert proc.stats()["processed"] >= 1

    context_path = cw / "context.yaml"
    context_path.write_text("test: value", encoding="utf-8")
    rollback = RollbackManager(repo_root=tmp_path)
    checkpoint = rollback.checkpoint("test")
    context_path.write_text("broken: data", encoding="utf-8")
    assert rollback.rollback(checkpoint)
    assert "test: value" in context_path.read_text(encoding="utf-8")

    retry = RetryEngine(max_retries=3, delay_s=0)
    counter = {"n": 0}

    def flaky() -> str:
        counter["n"] += 1
        if counter["n"] < 3:
            raise RuntimeError("retry")
        return "ok"

    assert retry.run(flaky) == "ok"

    predictor = FailurePredictor()
    pred = predictor.predict({"relationships": {}, "architecture": {"type": "layered", "confidence": "high"}}, {"repository": {"architecture": "layered"}})
    assert "risk_level" in pred


def test_v2_scanner_stack(tmp_path):
    from clockwork.scanner.directory_walker import DirectoryWalker
    from clockwork.scanner.language_detector import LanguageDetector
    from clockwork.scanner.dependency_analyzer import DependencyAnalyzer
    from clockwork.scanner.architecture_inferer import ArchitectureInferer
    from clockwork.scanner.relationship_mapper import RelationshipMapper

    (tmp_path / "a.py").write_text("import os\n", encoding="utf-8")
    (tmp_path / "b.ts").write_text("export const x = 1;\n", encoding="utf-8")

    walker = DirectoryWalker(tmp_path)
    files = walker.walk()
    assert len(files) >= 2

    lang = LanguageDetector(files).detect()
    assert "languages" in lang and "primary" in lang

    deps = DependencyAnalyzer(tmp_path).analyze()
    assert "dependencies" in deps

    arch = ArchitectureInferer(files, tmp_path).infer()
    assert "type" in arch and "components" in arch

    rel = RelationshipMapper(files, tmp_path).map()
    assert "graph" in rel and "circular_imports" in rel


def test_v2_registry_stack(tmp_path):
    from clockwork.registry.registry_engine import RegistryEngine

    (tmp_path / ".clockwork").mkdir(parents=True, exist_ok=True)
    reg = RegistryEngine(tmp_path)

    results = reg.search()
    assert isinstance(results, list)
    assert len(results) > 0

    entry = reg.get("security_scanner")
    assert entry is not None

    ok, _ = reg.install("security_scanner")
    assert ok

    installed = reg.list_installed()
    assert any(plugin.name == "security_scanner" for plugin in installed)

