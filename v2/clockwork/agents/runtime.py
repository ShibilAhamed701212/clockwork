import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from agents.agent_registry    import AgentRegistry
from agents.task_queue         import TaskQueue, TaskItem
from agents.task_graph         import TaskGraph
from agents.router             import Router
from agents.load_balancer      import LoadBalancer
from agents.swarm.coordinator  import SwarmCoordinator
from agents.swarm.consensus    import ConsensusEngine
from agents.sandbox.executor   import SandboxExecutor
from validation.pipeline       import ValidationPipeline
from recovery.rollback         import RollbackManager
from recovery.retry            import RetryEngine
from recovery.self_healing     import SelfHealing

AGENT_LOG  = Path("logs/agent.log")
TASKS_FILE = Path(".clockwork/tasks.json")
AGENT_LOG_JSON = Path(".clockwork/agent_log.json")

class AgentRuntime:
    def __init__(self, settings=None, context=None, brain=None, rule_engine=None):
        self.settings    = settings
        self.context     = context
        self.brain       = brain
        self.rule_engine = rule_engine
        self.registry    = AgentRegistry()
        self.queue       = TaskQueue()
        self.graph       = TaskGraph()
        self.router      = Router(self.registry)
        self.balancer    = LoadBalancer(self.registry)
        self.consensus   = ConsensusEngine()
        dry_run          = getattr(getattr(settings,"execution",None),"dry_run",False)
        self.executor    = SandboxExecutor(dry_run=dry_run)
        mode             = getattr(settings,"mode","safe")
        self.coordinator = SwarmCoordinator(self.registry, dry_run=dry_run)
        ctx_snap         = context.snapshot() if context else {}
        self.validator   = ValidationPipeline(context=ctx_snap, rule_engine=rule_engine)
        self.rollback    = RollbackManager()
        self.retry       = RetryEngine(max_retries=3, delay_s=0.5)
        self.healing     = SelfHealing(context=context, state=None)
        self._ensure_dirs()

    def _ensure_dirs(self):
        AGENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AGENT_LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
        if not AGENT_LOG_JSON.exists():
            AGENT_LOG_JSON.write_text("[]")

    def submit(self, name: str, action: Dict, priority: float = 0.5,
               deps: List[str] = []) -> Dict:
        task = TaskItem(name=name, action=action, priority=priority, deps=deps)
        self.queue.push(task)
        self.graph.add(task)
        print("[Runtime] Task submitted: " + name)

        if self.brain:
            decision = self.brain.decide(action)
            if not decision.approved():
                self.queue.fail(task.id, decision.explanation)
                self._log_agent(name, "system", task.id, "rejected", decision.explanation)
                return {"success": False, "error": decision.explanation}

        agent      = self.router.route(task.to_dict(), mode=getattr(self.settings,"mode","safe"))
        agent_name = agent.name if agent else "general_agent"
        result     = self.executor.execute(task.to_dict(), agent_name=agent_name)

        if result.success:
            v_result = self.validator.run(
                {"success": True, "proposed_changes": [], "output": result.output},
                action
            )
            if not v_result.passed:
                self.queue.fail(task.id, "Validation failed: " + str(v_result.errors))
                self._log_agent(name, agent_name, task.id, "validation_failed", str(v_result.errors))
                return {"success": False, "error": "Validation: " + str(v_result.errors)}

            self.queue.complete(task.id, result.output)
            self.registry.increment_done(agent_name)
            if self.context:
                self.context.record_action(name, agent=agent_name)
                if result.explanation:
                    self.context.record_decision(
                        result.explanation.get("change", name),
                        result.explanation.get("reason","")
                    )
            self._log_agent(name, agent_name, task.id, "completed", "")
        else:
            self.queue.fail(task.id, result.error)
            self.healing.heal({"type":"execution_error","details":result.error,"path":action.get("target","")})
            self._log_agent(name, agent_name, task.id, "failed", result.error)

        self._persist_tasks()
        return result.to_dict()

    def run_plan(self, tasks: List[TaskItem]) -> List[Dict]:
        mode = getattr(self.settings,"mode","safe")
        cp   = self.rollback.checkpoint("pre_plan")
        try:
            results = self.coordinator.run(tasks, mode=mode)
            self.rollback.cleanup_old(keep=5)
            return results
        except Exception as e:
            print("[Runtime] Plan failed — rolling back: " + str(e))
            self.rollback.rollback(cp)
            return []

    def run_pipeline(self, goal: str) -> Dict:
        print("[Runtime] Pipeline for: " + goal)
        pipeline_tasks = [
            TaskItem("scan",   {"type":"scan",  "target":"."},                      priority=1.0),
            TaskItem("update", {"type":"update","target":".clockwork/context.yaml"},priority=0.9, deps=["scan"]),
            TaskItem("verify", {"type":"verify","target":"rules"},                  priority=0.8, deps=["update"]),
            TaskItem("graph",  {"type":"graph", "target":"."},                      priority=0.7, deps=["verify"]),
        ]
        results = self.run_plan(pipeline_tasks)
        summary = {
            "goal":    goal,
            "total":   len(results),
            "success": sum(1 for r in results if r.get("success")),
            "failed":  sum(1 for r in results if not r.get("success")),
        }
        if self.context:
            self.context.set("last_pipeline", summary)
        return summary

    def _log_agent(self, task_name: str, agent: str, task_id: str,
                   status: str, details: str):
        entry = {"timestamp": time.time(), "agent": agent, "task_id": task_id,
                 "task_name": task_name, "status": status,
                 "details": details[:200]}
        with open(AGENT_LOG, "a") as f:
            f.write("[" + str(round(time.time(),2)) + "] " + task_name +
                    " | " + agent + " | " + status + "\n")
        log = json.loads(AGENT_LOG_JSON.read_text())
        log.append(entry)
        AGENT_LOG_JSON.write_text(json.dumps(log[-500:], indent=2))

    def _persist_tasks(self):
        with open(TASKS_FILE,"w") as f:
            json.dump(self.queue.all(), f, indent=2)

    def status(self) -> Dict:
        return {
            "queue":   self.queue.stats(),
            "agents":  self.balancer.stats(),
            "graph":   self.graph.summary(),
        }