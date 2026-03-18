import pytest
from agents.agent_registry   import AgentRegistry
from agents.task_queue        import TaskQueue, TaskItem
from agents.task_graph        import TaskGraph
from agents.router            import Router
from agents.load_balancer     import LoadBalancer
from agents.swarm.consensus   import ConsensusEngine
from agents.sandbox.executor  import SandboxExecutor

def test_agent_registry():
    reg = AgentRegistry()
    agents = reg.all()
    assert len(agents) > 0
    found = reg.find_by_capability("scan")
    assert len(found) > 0

def test_task_queue():
    q = TaskQueue()
    t = TaskItem("test_task", {"type": "scan", "target": "."}, priority=0.8)
    q.push(t)
    assert q.size() == 1
    popped = q.pop()
    assert popped is not None
    assert popped.name == "test_task"

def test_task_graph():
    g = TaskGraph()
    t1 = TaskItem("task_a", {"type": "scan",   "target": "."})
    t2 = TaskItem("task_b", {"type": "verify", "target": "."}, deps=["task_a"])
    g.add(t1)
    g.add(t2)
    roots = g.roots()
    assert any(r.name == "task_a" for r in roots)

def test_router():
    reg    = AgentRegistry()
    router = Router(reg)
    task   = {"name": "scan_repo", "action": {"type": "scan", "target": "."}}
    agent  = router.route(task)
    assert agent is not None

def test_load_balancer():
    reg = AgentRegistry()
    lb  = LoadBalancer(reg)
    stats = lb.stats()
    assert "total_agents" in stats
    assert stats["total_agents"] > 0

def test_consensus():
    engine  = ConsensusEngine()
    results = [
        {"success": True,  "output": "result_a"},
        {"success": True,  "output": "result_a"},
        {"success": False, "output": None},
    ]
    best = engine.vote(results)
    assert best is not None
    conf = engine.confidence(results)
    assert 0.0 <= conf <= 1.0

def test_sandbox_dry_run():
    executor = SandboxExecutor(dry_run=True)
    result   = executor.execute({"name": "test", "action": {"type": "scan", "target": "."}})
    assert result.success
    assert "DRY RUN" in str(result.output)