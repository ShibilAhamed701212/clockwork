import subprocess
import time
from typing import Dict, List, Optional

from brain.decision_engine   import DecisionEngine, Decision
from brain.planning_engine   import PlanningEngine, Task
from brain.optimization_engine import OptimizationEngine
from brain.meta_reasoning    import MetaReasoning
from brain.prioritization    import PrioritizationEngine

def _ollama_available() -> bool:
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True, timeout=3
        )
        return result.returncode == 0
    except Exception:
        return False


class MiniBrain:
    def __init__(self):
        self.decision_engine = DecisionEngine()

    def reason(self, action: Dict, context: Dict, rule_result=None) -> Decision:
        return self.decision_engine.evaluate(action, context, rule_result)

    def name(self) -> str:
        return "MiniBrain"


class OllamaBrain:
    def __init__(self, model: str = "deepseek-coder"):
        self.model = model
        self.fallback = MiniBrain()

    def reason(self, action: Dict, context: Dict, rule_result=None) -> Decision:
        prompt = self._build_prompt(action, context)
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True, text=True, timeout=30
            )
            output = result.stdout.strip()
            return self._parse_output(output, action, context, rule_result)
        except Exception as e:
            print("[OllamaBrain] Fallback to MiniBrain: " + str(e))
            return self.fallback.reason(action, context, rule_result)

    def _build_prompt(self, action: Dict, context: Dict) -> str:
        arch = context.get("repository", {}).get("architecture", "unknown")
        atype = action.get("type", "unknown")
        target = action.get("target", "")
        return (
            "Clockwork decision request.\n"
            "Architecture: " + arch + "\n"
            "Action: " + atype + " -> " + target + "\n"
            "Respond ONLY: VALID, WARNING, or REJECTED with a one-line reason."
        )

    def _parse_output(self, output: str, action: Dict, context: Dict, rule_result) -> Decision:
        upper = output.upper()
        if "REJECTED" in upper:
            return Decision(status="REJECTED", confidence=0.7, risk_level="high",
                           explanation="Ollama: " + output[:200])
        elif "WARNING" in upper:
            return Decision(status="WARNING", confidence=0.75, risk_level="medium",
                           explanation="Ollama: " + output[:200])
        return Decision(status="VALID", confidence=0.85, risk_level="low",
                       explanation="Ollama: " + output[:200])

    def name(self) -> str:
        return "OllamaBrain[" + self.model + "]"


class ExternalBrain:
    def __init__(self, provider: str = "openai", model: str = "gpt-4o", api_key: str = ""):
        self.provider = provider
        self.model    = model
        self.api_key  = api_key
        self.fallback = MiniBrain()

    def reason(self, action: Dict, context: Dict, rule_result=None) -> Decision:
        print("[ExternalBrain] External reasoning not configured — using MiniBrain fallback.")
        return self.fallback.reason(action, context, rule_result)

    def name(self) -> str:
        return "ExternalBrain[" + self.provider + "/" + self.model + "]"


class Brain:
    def __init__(self, settings=None, context=None, rule_engine=None):
        self.settings     = settings
        self.context_eng  = context
        self.rule_engine  = rule_engine
        self.decision_eng = DecisionEngine()
        self.planner      = PlanningEngine()
        self.optimizer    = OptimizationEngine()
        self.meta         = MetaReasoning()
        self.prioritizer  = PrioritizationEngine()
        self._active_brain = self._select_brain()

    def _select_brain(self):
        if self.settings and getattr(self.settings, "mode", "safe") == "aggressive":
            if _ollama_available():
                print("[Brain] Using OllamaBrain")
                return OllamaBrain()
        print("[Brain] Using MiniBrain (deterministic)")
        return MiniBrain()

    # ── Primary decision gate ─────────────────────────────────────
    def decide(self, action: Dict) -> Decision:
        context = {}
        if self.context_eng:
            context = self.context_eng.snapshot()

        rule_result = None
        if self.rule_engine:
            rule_result = self.rule_engine.validate(action)
            if not rule_result.approved:
                decision = Decision(
                    status="REJECTED",
                    confidence=1.0,
                    risk_level="high",
                    explanation="Rule Engine blocked: " + rule_result.reason,
                    suggestion="Fix rule violation first.",
                )
                self.meta.evaluate_decision(decision, action)
                return decision

        decision = self._active_brain.reason(action, context, rule_result)
        self.meta.evaluate_decision(decision, action)

        print("[Brain] Decision: " + decision.status +
              " | risk=" + decision.risk_level +
              " | conf=" + str(decision.confidence) +
              " | " + decision.explanation[:80])
        return decision

    # ── Swarm consensus ───────────────────────────────────────────
    def swarm_decide(self, action: Dict) -> Decision:
        context = self.context_eng.snapshot() if self.context_eng else {}
        rule_result = self.rule_engine.validate(action) if self.rule_engine else None
        engines = [
            MiniBrain(),
            MiniBrain(),
        ]
        if _ollama_available():
            engines.append(OllamaBrain())

        decisions = [e.reason(action, context, rule_result) for e in engines]
        final = self.decision_eng.compare(decisions)
        print("[Brain] Swarm consensus: " + final.status + " from " + str(len(engines)) + " engines")
        return final

    # ── Planning ──────────────────────────────────────────────────
    def plan(self, goal: str) -> List[Task]:
        context = self.context_eng.snapshot() if self.context_eng else {}
        tasks   = self.planner.decompose(goal, context)
        ordered = self.planner.order(tasks)
        print("[Brain] Plan: " + str(len(ordered)) + " tasks for goal: " + goal)
        return ordered

    # ── Risk assessment ───────────────────────────────────────────
    def assess_risk(self, action: Dict) -> str:
        decision = self.decide(action)
        return decision.risk_level

    # ── Meta summary ──────────────────────────────────────────────
    def meta_summary(self) -> Dict:
        summary = self.meta.summary()
        pattern = self.meta.detect_pattern()
        if pattern:
            print("[Brain] META PATTERN: " + pattern)
        return summary

    # ── Generate multiple solutions ───────────────────────────────
    def multi_solve(self, action: Dict) -> List[Decision]:
        alternatives = self.optimizer.generate_alternatives(action)
        decisions = []
        for alt in alternatives:
            d = self._active_brain.reason(alt, {})
            d.explanation = "[" + alt.get("label", "?") + "] " + d.explanation
            decisions.append(d)
        return decisions