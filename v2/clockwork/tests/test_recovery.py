import pytest
import tempfile
import time
from pathlib import Path
from context.live_index.event_queue           import EventQueue
from context.live_index.incremental_processor import IncrementalProcessor, FileIndex
from recovery.rollback      import RollbackManager
from recovery.retry         import RetryEngine
from recovery.self_healing  import SelfHealing
from recovery.predictor     import FailurePredictor

# ── EventQueue tests ─────────────────────────────────────────────
def test_event_queue_push_pop():
    q = EventQueue()
    q.push({"type": "modified", "path": "app.py", "ts": 1.0})
    assert q.size() == 1
    e = q.pop()
    assert e["type"] == "modified"

def test_event_queue_priority():
    q = EventQueue()
    q.push({"type": "modified", "path": "readme.md",        "ts": 1.0})
    q.push({"type": "modified", "path": "requirements.txt", "ts": 1.0})
    q.push({"type": "modified", "path": "service.py",       "ts": 1.0})
    events = q.drain_deduped()
    assert len(events) == 3
    assert "high" in [e["priority"] for e in events]

def test_event_queue_dedup():
    q = EventQueue()
    for _ in range(5):
        q.push({"type": "modified", "path": "same.py", "ts": 1.0})
    assert len(q.drain_deduped()) == 1

# ── FileIndex tests ──────────────────────────────────────────────
def test_file_index(tmp_path):
    idx = FileIndex(tmp_path / "test.db")
    idx.upsert("app.py", "abc123", 1000.0, "module", "flask", "Python")
    rec = idx.get("app.py")
    assert rec["hash"]     == "abc123"
    assert rec["language"] == "Python"
    idx.delete("app.py")
    assert idx.get("app.py") is None

# ── RollbackManager tests ────────────────────────────────────────
def test_rollback_checkpoint_and_restore(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cw = tmp_path / ".clockwork"
    cw.mkdir()
    (cw / "context.yaml").write_text("test: value")
    rb = RollbackManager()
    cp = rb.checkpoint("test")
    assert Path(cp).exists()
    (cw / "context.yaml").write_text("corrupted: data")
    ok = rb.rollback(cp)
    assert ok
    assert "test: value" in (cw / "context.yaml").read_text()

def test_rollback_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".clockwork").mkdir()
    rb = RollbackManager()
    rb.checkpoint("first")
    rb.checkpoint("second")
    cps = rb.list_checkpoints()
    assert len(cps) >= 2

# ── RetryEngine tests ────────────────────────────────────────────
def test_retry_success():
    engine  = RetryEngine(max_retries=3, delay_s=0)
    counter = {"n": 0}
    def fn():
        counter["n"] += 1
        if counter["n"] < 3:
            raise ValueError("Not yet")
        return "done"
    result = engine.run(fn)
    assert result == "done"
    assert counter["n"] == 3

def test_retry_safe_returns_default():
    engine = RetryEngine(max_retries=2, delay_s=0)
    def fail():
        raise RuntimeError("always fails")
    result = engine.run_safe(fail, default="fallback")
    assert result == "fallback"

# ── FailurePredictor tests ───────────────────────────────────────
def test_predictor_low_risk():
    pred     = FailurePredictor()
    repo_map = {"relationships":{},"architecture":{"confidence":"high","type":"layered"}}
    context  = {"repository":{"architecture":"layered"}}
    result   = pred.predict(repo_map, context)
    assert result["risk_level"] in ("low","medium","high")
    assert "recommendation" in result

def test_predictor_high_risk():
    pred = FailurePredictor()
    repo_map = {
        "relationships": {"circular_imports":["a->b->a"],"anomalies":["x","y","z"]},
        "architecture":  {"confidence":"low","type":"layered"},
    }
    context = {"repository":{"architecture":"monolith"}}
    result  = pred.predict(repo_map, context)
    assert result["risk_score"] > 0.3

# ── IncrementalProcessor tests ───────────────────────────────────
def test_incremental_stats():
    proc  = IncrementalProcessor()
    stats = proc.stats()
    assert "processed" in stats and "errors" in stats

def test_incremental_process_file(tmp_path):
    db   = tmp_path / "idx.db"
    proc = IncrementalProcessor()
    proc.index = FileIndex(db)
    f    = tmp_path / "mod.py"
    f.write_text("import os\ndef hello(): pass\n")
    result = proc.process_event({"type":"modified","path":str(f),"ts":1.0})
    assert result is True
    rec = proc.index.get(str(f))
    assert rec is not None