import json
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

from recovery.rollback     import RollbackManager
from recovery.retry        import RetryEngine
from recovery.self_healing import SelfHealing
from recovery.predictor    import FailurePredictor

FAILURE_LOG    = Path(".clockwork/failure_log.json")
FAILSAFE_LIMIT = 5

class RecoveryEngine:
    def __init__(self, context=None, state=None, brain=None):
        self.context   = context
        self.state     = state
        self.brain     = brain
        self.rollback  = RollbackManager()
        self.retry     = RetryEngine(max_retries=3, delay_s=0.5, backoff=2.0)
        self.healing   = SelfHealing(context=context, state=state)
        self.predictor = FailurePredictor()
        self._history: List[Dict] = []
        self._failsafe = False
        self._failure_count = 0
        FAILURE_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not FAILURE_LOG.exists():
            FAILURE_LOG.write_text("[]")

    # ── Main failure handler ──────────────────────────────────────
    def on_failure(self, failure_type: str, details: str = "",
                   path: str = "", severity: str = "medium",
                   component: str = "system") -> bool:
        failure = {
            "type":        failure_type,
            "details":     details,
            "path":        path,
            "severity":    severity,
            "component":   component,
            "timestamp":   time.time(),
            "resolved":    False,
        }
        print("[Recovery] FAILURE: " + failure_type + " [" + severity + "] " + details[:60])
        self._history.append(failure)
        self._failure_count += 1
        self._log_failure(failure)

        if self.state:
            self.state.mark_unhealthy(failure_type + ": " + details[:50])

        if self._failure_count >= FAILSAFE_LIMIT:
            self._enter_failsafe()
            return False

        if severity == "low":
            print("[Recovery] Low severity — warning only.")
            return True

        strategy = self._select_strategy(failure_type, severity)
        print("[Recovery] Strategy: " + strategy)
        result = self._execute_strategy(strategy, failure)

        if result:
            failure["resolved"] = True
            self._failure_count = max(0, self._failure_count - 1)
            if self.context:
                self.context.integrate_feedback(failure_type, success=True)
            print("[Recovery] Resolved: " + failure_type)
        else:
            if self.context:
                self.context.integrate_feedback(failure_type, success=False)
            print("[Recovery] Could not resolve: " + failure_type)

        self._update_log(failure)
        return result

    # ── Root cause analysis ───────────────────────────────────────
    def analyze_root_cause(self, failure: Dict) -> str:
        ftype   = failure.get("type","")
        details = failure.get("details","").lower()
        if "import" in details or "module" in details:
            return "missing_dependency"
        if "context" in details or "yaml" in details:
            return "context_corruption"
        if "graph" in details or "db" in details:
            return "graph_corruption"
        if "permission" in details or "access" in details:
            return "access_denied"
        if "timeout" in details:
            return "execution_timeout"
        return ftype

    # ── Strategy selection ────────────────────────────────────────
    def _select_strategy(self, failure_type: str, severity: str) -> str:
        if severity == "high":
            return "rollback"
        strategy_map = {
            "missing_file":         "heal",
            "invalid_context":      "heal",
            "context_corruption":   "heal",
            "graph_corruption":     "heal",
            "index_corruption":     "heal",
            "missing_dependency":   "heal",
            "execution_timeout":    "retry",
            "validation_failure":   "retry",
            "agent_failure":        "retry",
            "context_drift":        "rollback",
            "system_crash":         "rollback",
            "access_denied":        "report",
        }
        return strategy_map.get(failure_type, "heal")

    def _execute_strategy(self, strategy: str, failure: Dict) -> bool:
        root_cause = self.analyze_root_cause(failure)
        failure_with_root = {**failure, "type": root_cause}

        if strategy == "heal":
            return self.healing.heal(failure_with_root)

        elif strategy == "rollback":
            latest = self.rollback.latest()
            if latest:
                ok = self.rollback.rollback(latest)
                if ok and self.context:
                    self.context.load()
                return ok
            print("[Recovery] No checkpoint to rollback to.")
            return self.healing.heal(failure_with_root)

        elif strategy == "retry":
            print("[Recovery] Retry strategy — caller must re-trigger.")
            return True

        elif strategy == "report":
            print("[Recovery] SECURITY: " + failure.get("details",""))
            return False

        return False

    # ── Failsafe mode ─────────────────────────────────────────────
    def _enter_failsafe(self):
        if not self._failsafe:
            self._failsafe = True
            print("[Recovery] FAILSAFE MODE ACTIVATED — restricting execution.")
            if self.state:
                self.state.mark_unhealthy("Failsafe mode: too many failures")

    def exit_failsafe(self):
        self._failsafe = False
        self._failure_count = 0
        print("[Recovery] Failsafe mode cleared.")

    def is_failsafe(self) -> bool:
        return self._failsafe

    # ── Predict before execution ──────────────────────────────────
    def predict(self, repo_map: Dict, context: Dict) -> Dict:
        return self.predictor.predict(repo_map, context)

    # ── Safe execution wrappers ───────────────────────────────────
    def safe_execute(self, fn: Callable, *args,
                     failure_type: str = "execution_error",
                     severity: str = "medium", **kwargs):
        if self._failsafe:
            print("[Recovery] Failsafe active — blocking execution.")
            return None
        cp = self.rollback.checkpoint("pre_exec")
        try:
            return self.retry.run(fn, *args, **kwargs)
        except Exception as e:
            self.on_failure(failure_type, str(e), severity=severity)
            return None

    def checkpoint_and_run(self, fn: Callable, label: str = "", *args, **kwargs):
        cp = self.rollback.checkpoint(label or "checkpoint")
        try:
            result = fn(*args, **kwargs)
            self.rollback.cleanup_old(keep=5)
            return result
        except Exception as e:
            print("[Recovery] Rolling back after failure: " + str(e))
            self.rollback.rollback(cp)
            if self.context:
                self.context.load()
            raise

    # ── Logging ───────────────────────────────────────────────────
    def _log_failure(self, failure: Dict):
        log = json.loads(FAILURE_LOG.read_text())
        log.append(failure)
        FAILURE_LOG.write_text(json.dumps(log[-500:], indent=2))

    def _update_log(self, failure: Dict):
        try:
            log = json.loads(FAILURE_LOG.read_text())
            for entry in reversed(log):
                if entry.get("timestamp") == failure.get("timestamp"):
                    entry["resolved"] = failure.get("resolved", False)
                    break
            FAILURE_LOG.write_text(json.dumps(log[-500:], indent=2))
        except Exception:
            pass

    def get_failure_log(self, last_n: int = 50) -> List[Dict]:
        return json.loads(FAILURE_LOG.read_text())[-last_n:]

    def stats(self) -> Dict:
        log       = json.loads(FAILURE_LOG.read_text())
        total     = len(log)
        resolved  = sum(1 for e in log if e.get("resolved"))
        recent    = [e for e in log if time.time() - e.get("timestamp",0) < 3600]
        return {
            "total_failures":   total,
            "resolved":         resolved,
            "unresolved":       total - resolved,
            "recent_1h":        len(recent),
            "failure_count":    self._failure_count,
            "failsafe_active":  self._failsafe,
            "checkpoints":      len(self.rollback.list_checkpoints()),
        }

    def history(self) -> List[Dict]:
        return list(self._history)