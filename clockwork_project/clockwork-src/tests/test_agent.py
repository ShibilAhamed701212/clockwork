"""
tests/test_agent.py
---------------------
Unit tests for the Agent Runtime subsystem (spec §11).

Run with:
    pytest tests/test_agent.py -v
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from clockwork.agent.models import (
    Agent, Capability, Task, TaskStatus, ValidationResult
)
from clockwork.agent.registry import AgentRegistry
from clockwork.agent.lock_manager import FileLockError, LockManager
from clockwork.agent.router import TaskRouter
from clockwork.agent.runtime import AgentRuntime


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_cw(tmp_path: Path) -> Path:
    cw = tmp_path / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    return cw


def _make_registry(tmp_path: Path) -> AgentRegistry:
    cw = _make_cw(tmp_path)
    r  = AgentRegistry(cw)
    r.initialise()
    return r


def _make_runtime(tmp_path: Path) -> AgentRuntime:
    _make_cw(tmp_path)
    rt = AgentRuntime(tmp_path)
    rt.initialise()
    return rt


def _agent(name: str, caps=None, priority: int = 10) -> Agent:
    return Agent(name=name, capabilities=caps or [Capability.CODING], priority=priority)


def _task(desc: str = "Do something", cap: str = Capability.CODING) -> Task:
    return Task.new(desc, cap)


# ── Agent model ────────────────────────────────────────────────────────────

class TestAgentModel:
    def test_can_handle_matching_cap(self):
        a = _agent("bot", [Capability.CODING, Capability.TESTING])
        assert a.can_handle(Capability.CODING) is True

    def test_can_handle_missing_cap(self):
        a = _agent("bot", [Capability.CODING])
        assert a.can_handle(Capability.DOCUMENTATION) is False

    def test_to_dict_roundtrip(self):
        a = _agent("claude", [Capability.CODING], priority=1)
        d = a.to_dict()
        a2 = Agent.from_dict(d)
        assert a2.name == a.name
        assert a2.capabilities == a.capabilities
        assert a2.priority == a.priority


# ── Task model ─────────────────────────────────────────────────────────────

class TestTaskModel:
    def test_new_generates_unique_ids(self):
        t1 = Task.new("a")
        t2 = Task.new("b")
        assert t1.task_id != t2.task_id

    def test_initial_status_is_pending(self):
        t = Task.new("do something")
        assert t.status == TaskStatus.PENDING

    def test_assign(self):
        t = _task()
        t.assign("claude")
        assert t.status == TaskStatus.ASSIGNED
        assert t.assigned_agent == "claude"

    def test_complete(self):
        t = _task()
        t.complete("done")
        assert t.status == TaskStatus.COMPLETED
        assert t.result == "done"
        assert t.is_terminal()

    def test_fail(self):
        t = _task()
        t.fail("something broke")
        assert t.status == TaskStatus.FAILED
        assert t.is_terminal()

    def test_reject(self):
        t = _task()
        t.reject(["rule violation"])
        assert t.status == TaskStatus.REJECTED
        assert "rule violation" in t.validation_errors
        assert t.is_terminal()

    def test_to_dict_roundtrip(self):
        t  = Task.new("implement login", Capability.CODING)
        d  = t.to_dict()
        t2 = Task.from_dict(d)
        assert t2.task_id == t.task_id
        assert t2.description == t.description
        assert t2.required_capability == t.required_capability


# ── AgentRegistry ──────────────────────────────────────────────────────────

class TestAgentRegistry:
    def test_register_and_list(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(_agent("bot1"))
        agents = r.list_agents()
        assert any(a.name == "bot1" for a in agents)

    def test_duplicate_register_returns_false(self, tmp_path):
        r = _make_registry(tmp_path)
        assert r.register_agent(_agent("bot1")) is True
        assert r.register_agent(_agent("bot1")) is False

    def test_get_agent(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(_agent("bot2"))
        a = r.get_agent("bot2")
        assert a is not None
        assert a.name == "bot2"

    def test_get_missing_agent_returns_none(self, tmp_path):
        r = _make_registry(tmp_path)
        assert r.get_agent("ghost") is None

    def test_remove_agent(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(_agent("bot3"))
        assert r.remove_agent("bot3") is True
        assert r.get_agent("bot3") is None

    def test_agents_for_capability_sorted_by_priority(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(Agent("slow", [Capability.CODING], priority=5))
        r.register_agent(Agent("fast", [Capability.CODING], priority=1))
        caps = r.agents_for_capability(Capability.CODING)
        assert caps[0].name == "fast"

    def test_agents_for_capability_filters_correctly(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(Agent("coder", [Capability.CODING]))
        r.register_agent(Agent("tester", [Capability.TESTING]))
        coders = r.agents_for_capability(Capability.CODING)
        assert all(a.can_handle(Capability.CODING) for a in coders)
        assert not any(a.name == "tester" for a in coders)

    def test_add_and_list_tasks(self, tmp_path):
        r = _make_registry(tmp_path)
        t = _task("write tests")
        r.add_task(t)
        tasks = r.list_tasks()
        assert any(x.task_id == t.task_id for x in tasks)

    def test_update_task(self, tmp_path):
        r = _make_registry(tmp_path)
        t = _task()
        r.add_task(t)
        t.complete("done")
        r.update_task(t)
        t2 = r.get_task(t.task_id)
        assert t2.status == TaskStatus.COMPLETED

    def test_pending_tasks(self, tmp_path):
        r = _make_registry(tmp_path)
        t1 = _task("pending one")
        t2 = _task("pending two")
        t2.complete()
        r.add_task(t1)
        r.add_task(t2)
        pending = r.pending_tasks()
        assert any(x.task_id == t1.task_id for x in pending)
        assert not any(x.task_id == t2.task_id for x in pending)

    def test_log_writes_entry(self, tmp_path):
        r = _make_registry(tmp_path)
        t = _task()
        r.log("claude", t, "completed", "all good")
        log = r.read_log()
        assert len(log) == 1
        assert log[0]["agent"] == "claude"
        assert log[0]["status"] == "completed"

    def test_stats(self, tmp_path):
        r = _make_registry(tmp_path)
        t1 = _task(); r.add_task(t1)
        t2 = _task(); t2.complete(); r.add_task(t2)
        s = r.stats()
        assert s[TaskStatus.PENDING]   >= 1
        assert s[TaskStatus.COMPLETED] >= 1


# ── LockManager ────────────────────────────────────────────────────────────

class TestLockManager:
    def test_acquire_and_release(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("backend/auth.py", "agent_a")
        assert lm.is_locked("backend/auth.py")
        lm.release("backend/auth.py", "agent_a")
        assert not lm.is_locked("backend/auth.py")

    def test_double_acquire_same_agent_ok(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("a.py", "agent_a")
        lm.acquire("a.py", "agent_a")   # should not raise
        lm.release("a.py", "agent_a")

    def test_acquire_locked_by_other_raises(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("a.py", "agent_a")
        with pytest.raises(FileLockError):
            lm.acquire("a.py", "agent_b")
        lm.release("a.py", "agent_a")

    def test_release_by_non_holder_returns_false(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("a.py", "agent_a")
        assert lm.release("a.py", "agent_b") is False
        lm.release("a.py", "agent_a")

    def test_release_all(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("a.py", "agent_a")
        lm.acquire("b.py", "agent_a")
        released = lm.release_all("agent_a")
        assert released == 2
        assert not lm.is_locked("a.py")
        assert not lm.is_locked("b.py")

    def test_lock_holder(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("x.py", "agent_x")
        assert lm.lock_holder("x.py") == "agent_x"
        lm.release("x.py", "agent_x")
        assert lm.lock_holder("x.py") is None

    def test_list_locks(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("a.py", "agent_a")
        lm.acquire("b.py", "agent_b")
        locks = lm.list_locks()
        assert len(locks) == 2
        lm.release_all("agent_a")
        lm.release_all("agent_b")

    def test_context_manager(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        with lm.locked("c.py", "agent_c"):
            assert lm.is_locked("c.py")
        assert not lm.is_locked("c.py")

    def test_stale_lock_auto_cleared(self, tmp_path):
        lm = LockManager(_make_cw(tmp_path))
        lm.acquire("stale.py", "old_agent")
        # manually backdate the lock
        lp = lm._lock_path("stale.py")
        d  = json.loads(lp.read_text())
        d["acquired_at"] = time.time() - 400   # older than TTL
        lp.write_text(json.dumps(d))
        # now a new agent should be able to acquire it
        lm.acquire("stale.py", "new_agent")
        assert lm.lock_holder("stale.py") == "new_agent"
        lm.release("stale.py", "new_agent")


# ── TaskRouter ─────────────────────────────────────────────────────────────

class TestTaskRouter:
    def test_route_returns_best_agent(self, tmp_path):
        r  = _make_registry(tmp_path)
        r.register_agent(Agent("slow", [Capability.CODING], priority=5))
        r.register_agent(Agent("fast", [Capability.CODING], priority=1))
        router = TaskRouter(r)
        t      = _task()
        agent  = router.route(t)
        assert agent is not None
        assert agent.name == "fast"

    def test_route_returns_none_when_no_match(self, tmp_path):
        r  = _make_registry(tmp_path)
        r.register_agent(Agent("coder", [Capability.CODING]))
        router = TaskRouter(r)
        t      = Task.new("write docs", Capability.DOCUMENTATION)
        assert router.route(t) is None

    def test_dispatch_assigns_task(self, tmp_path):
        r = _make_registry(tmp_path)
        r.register_agent(Agent("bot", [Capability.CODING], priority=1))
        t = _task()
        r.add_task(t)
        router  = TaskRouter(r)
        assigned = router.dispatch(t)
        assert assigned == "bot"
        updated = r.get_task(t.task_id)
        assert updated.assigned_agent == "bot"


# ── AgentRuntime ───────────────────────────────────────────────────────────

class TestAgentRuntime:
    def test_register_and_list_agents(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("claude", [Capability.CODING], 1))
        agents = rt.list_agents()
        assert any(a.name == "claude" for a in agents)

    def test_add_task_auto_assigns(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("claude", [Capability.CODING], 1))
        task = rt.add_task("Implement auth", Capability.CODING)
        assert task.assigned_agent == "claude"

    def test_add_task_no_agent_stays_pending(self, tmp_path):
        rt   = _make_runtime(tmp_path)
        task = rt.add_task("Implement auth", Capability.CODING)
        assert task.status == TaskStatus.PENDING
        assert task.assigned_agent == ""

    def test_run_task_returns_validation_result(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("claude", [Capability.CODING], 1))
        task   = rt.add_task("write tests", Capability.CODING)
        result = rt.run_task(task.task_id)
        assert isinstance(result, ValidationResult)

    def test_run_task_unknown_id(self, tmp_path):
        rt     = _make_runtime(tmp_path)
        result = rt.run_task("task_nonexistent")
        assert result.passed is False

    def test_fail_task(self, tmp_path):
        rt   = _make_runtime(tmp_path)
        task = rt.add_task("a task")
        rt.fail_task(task.task_id, "timeout")
        updated = rt.get_task(task.task_id)
        assert updated.status == TaskStatus.FAILED

    def test_retry_task(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("bot1", [Capability.CODING], 1))
        rt.register_agent(_agent("bot2", [Capability.CODING], 2))
        task = rt.add_task("do something")
        rt.fail_task(task.task_id, "error")
        assigned = rt.retry_task(task.task_id)
        assert assigned is not None

    def test_stats(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("bot"))
        rt.add_task("task 1")
        rt.add_task("task 2")
        s = rt.stats()
        assert s["agents"] >= 1
        assert s["total_tasks"] >= 2

    def test_remove_agent(self, tmp_path):
        rt = _make_runtime(tmp_path)
        rt.register_agent(_agent("temp_bot"))
        assert rt.remove_agent("temp_bot") is True
        assert rt.get_agent("temp_bot") is None

    def test_list_tasks_with_status_filter(self, tmp_path):
        rt = _make_runtime(tmp_path)
        t1 = rt.add_task("pending task")
        pending = rt.list_tasks(TaskStatus.PENDING)
        ids = {t.task_id for t in pending}
        assert t1.task_id in ids

