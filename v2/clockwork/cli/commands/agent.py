import time
from brain.brain       import Brain
from rules.rule_engine import RuleEngine
from agents.runtime    import AgentRuntime
from cli.utils         import output as out

class AgentCommand:
    def __init__(self, settings, state, context):
        self.settings = settings
        self.state    = state
        self.context  = context

    def execute(self, goal: str = "analyze repository", json_mode: bool = False,
                auto_priority: bool = False, explain: bool = False):
        out.check_initialized()
        out.header("Agent Execution")
        out.info("Goal: " + goal)
        self.state.emit_event("agent_started", {"goal": goal})
        t0          = time.time()
        rule_engine = RuleEngine()
        brain       = Brain(settings=self.settings, context=self.context, rule_engine=rule_engine)
        runtime     = AgentRuntime(settings=self.settings, context=self.context,
                                   brain=brain, rule_engine=rule_engine)
        tasks = brain.plan(goal)
        out.result("Tasks planned", len(tasks))
        completed, rejected = [], []
        for task in tasks:
            decision = brain.decide(task.action)
            if decision.approved():
                result = runtime.submit(task.name, task.action)
                if result.get("success", True) is not False:
                    completed.append(task.name)
                    out.success("Task: " + task.name)
                    if explain and result.get("explanation"):
                        exp = result["explanation"]
                        out.info("  Change: " + str(exp.get("change","")))
                        out.info("  Reason: " + str(exp.get("reason","")))
                else:
                    rejected.append(task.name)
                    out.warn("Task failed: " + task.name)
            else:
                rejected.append(task.name)
                out.warn("Rejected: " + task.name + " | " + decision.explanation[:60])
                if decision.risk_level == "high":
                    out.error("High risk — stopping.")
                    break
        elapsed = round(time.time() - t0, 3)
        meta    = brain.meta_summary()
        self.state.emit_event("agent_completed", {"goal": goal, "completed": len(completed), "total": len(tasks)})
        result_data = {"goal": goal, "completed": len(completed), "rejected": len(rejected),
                       "total": len(tasks), "duration": elapsed, "meta": meta}
        if json_mode:
            out.json_output(result_data)
        else:
            out.result("Completed", str(len(completed)) + "/" + str(len(tasks)))
            out.result("Duration",  str(elapsed) + "s")
            if meta.get("pattern"):
                out.warn("Pattern: " + meta["pattern"])
            out.success("Agent execution complete.")
        return result_data