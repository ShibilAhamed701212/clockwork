import time
from typing import Dict, List
from agents.agent_registry import AgentRegistry
from agents.task_graph     import TaskGraph
from agents.task_queue     import TaskItem
from agents.router         import Router
from agents.sandbox.executor import SandboxExecutor

class SwarmCoordinator:
    def __init__(self, registry: AgentRegistry, dry_run: bool = False):
        self.registry = registry
        self.router   = Router(registry)
        self.executor = SandboxExecutor(dry_run=dry_run)
        self.results: List[Dict] = []

    def run(self, tasks: List[TaskItem], mode: str = "safe") -> List[Dict]:
        print("[Swarm] Coordinating " + str(len(tasks)) + " tasks | mode=" + mode)
        graph     = TaskGraph()
        for t in tasks:
            graph.add(t)

        ordered   = graph.topological_order()
        completed = []

        for task in ordered:
            agent = self.router.route(task.to_dict(), mode=mode)
            agent_name = agent.name if agent else "general_agent"

            result = self.executor.execute(task.to_dict(), agent_name=agent_name)

            if result.success:
                task.status = "completed"
                task.result = result.to_dict()
                completed.append(task.name)
                self.registry.increment_done(agent_name)
                self.registry.set_status(agent_name, "idle")
                print("[Swarm] OK: " + task.name + " (" + agent_name + ")")
            else:
                task.status = "failed"
                print("[Swarm] FAIL: " + task.name + " | " + result.error)
                if mode == "safe":
                    print("[Swarm] Stopping on first failure (safe mode).")
                    break

            self.results.append({
                "task":    task.name,
                "agent":   agent_name,
                "success": result.success,
                "explanation": result.explanation,
            })

        summary = graph.summary()
        print("[Swarm] Done: " + str(summary["completed"]) + "/" + str(summary["total"]) + " tasks completed.")
        return self.results

    def parallel_run(self, task_groups: List[List[TaskItem]]) -> List[Dict]:
        import threading
        all_results: List[Dict] = []
        threads = []
        lock = threading.Lock()

        def run_group(group):
            results = self.run(group, mode="aggressive")
            with lock:
                all_results.extend(results)

        for group in task_groups:
            t = threading.Thread(target=run_group, args=(group,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return all_results