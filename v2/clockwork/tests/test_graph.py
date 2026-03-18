import pytest
import tempfile
from pathlib import Path
from graph.node_manager     import NodeManager
from graph.edge_manager     import EdgeManager
from graph.query_engine     import QueryEngine
from graph.anomaly_detector import AnomalyDetector
from graph.graph_builder    import GraphBuilder

@pytest.fixture
def tmp_db(tmp_path):
    return tmp_path / "test_graph.db"

def test_node_manager(tmp_db):
    nm = NodeManager(tmp_db)
    nid = nm.upsert("file", "app.py", "backend/app.py", "Python", "backend")
    assert nid > 0
    node = nm.get(nid)
    assert node["name"] == "app.py"
    assert node["layer"] == "backend"

def test_edge_manager(tmp_db):
    nm = NodeManager(tmp_db)
    em = EdgeManager(tmp_db)
    src = nm.upsert("file",   "app.py",      "app.py",      "Python", "backend")
    tgt = nm.upsert("module", "database.py", "database.py", "Python", "database")
    em.add(src, tgt, "imports", "app.py", "database.py")
    outgoing = em.get_outgoing(src)
    assert len(outgoing) == 1
    assert outgoing[0]["rel_type"] == "imports"

def test_query_engine(tmp_db):
    nm = NodeManager(tmp_db)
    em = EdgeManager(tmp_db)
    qe = QueryEngine(tmp_db)
    a = nm.upsert("file", "a.py", "a.py", "Python", "backend")
    b = nm.upsert("file", "b.py", "b.py", "Python", "database")
    em.add(a, b, "imports", "a.py", "b.py")
    deps = qe.dependencies_of("a.py")
    assert len(deps) >= 1
    summary = qe.architecture_summary()
    assert "total_nodes" in summary

def test_anomaly_detector_no_crash(tmp_db):
    nm = NodeManager(tmp_db)
    nm.upsert("file", "orphan.py", "orphan.py", "Python", "")
    detector = AnomalyDetector(tmp_db)
    result = detector.detect_all()
    assert "circular_dependencies" in result
    assert "orphan_modules" in result

def test_graph_builder_from_repo_map(tmp_db):
    builder = GraphBuilder(tmp_db)
    repo_map = {
        "languages":     {"languages": {"Python": 5}},
        "dependencies":  {"dependencies": [{"name": "flask", "version": ">=2.0"}]},
        "components":    {"backend": ["app.py"]},
        "architecture":  {"type": "layered"},
        "relationships": {
            "graph": {
                "app.py": {"imports": ["database.py"]},
                "database.py": {"imports": []},
            }
        },
    }
    summary = builder.build_from_repo_map(repo_map)
    assert summary["total_nodes"] > 0
    health = builder.health_check()
    assert "health_score" in health
    assert "grade" in health