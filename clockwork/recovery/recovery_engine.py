from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clockwork.recovery.predictor import FailurePredictor
from clockwork.recovery.retry import RetryEngine
from clockwork.recovery.rollback import RollbackManager
from clockwork.recovery.self_healing import SelfHealing

FAILURE_LOG = Path(".clockwork/failure_log.json")
FAILSAFE_LIMIT = 5


class RecoveryEngine:
    def __init__(
        self,
        context: object | None = None,
        state: object | None = None,
        brain: object | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.context = context
        self.state = state
        self.brain = brain
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.failure_log = self.repo_root / FAILURE_LOG
        self.rollback = RollbackManager(repo_root=self.repo_root)
        self.retry = RetryEngine(max_retries=3, delay_s=0.5, backoff=2.0)
        self.healing = SelfHealing(context=context, state=state, repo_root=self.repo_root)
        self.predictor = FailurePredictor()
        self._history: list[dict[str, Any]] = []
        self._failsafe = False
        self._failure_count = 0

        self.failure_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.failure_log.exists():
            self.failure_log.write_text("[]", encoding="utf-8")

    def on_failure(
        self,
        failure_type: str,
        details: str = "",
        path: str = "",
        severity: str = "medium",
        component: str = "system",
    ) -> bool:
        failure = {
            "type": failure_type,
            "details": details,
            "path": path,
            "severity": severity,
            "component": component,
            "timestamp": time.time(),
            "resolved": False,
        }
        self._history.append(failure)
        self._failure_count += 1
        self._log_failure(failure)

        if self.state and hasattr(self.state, "mark_unhealthy"):
            self.state.mark_unhealthy(f"{failure_type}: {details[:50]}")

        if self._failure_count >= FAILSAFE_LIMIT:
            self._enter_failsafe()
            return False

        if severity == "low":
            return True

        strategy = self._select_strategy(failure_type, severity)
        result = self._execute_strategy(strategy, failure)

        if result:
            failure["resolved"] = True
            self._failure_count = max(0, self._failure_count - 1)

        self._update_log(failure)
        return result

    def analyze_root_cause(self, failure: dict) -> str:
        details = str(failure.get("details", "")).lower()
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
        return str(failure.get("type", "unknown"))

    def _select_strategy(self, failure_type: str, severity: str) -> str:
        if severity == "high":
            return "rollback"
        strategy_map = {
            "missing_file": "heal",
            "invalid_context": "heal",
            "context_corruption": "heal",
            "graph_corruption": "heal",
            "index_corruption": "heal",
            "missing_dependency": "heal",
            "execution_timeout": "retry",
            "validation_failure": "retry",
            "agent_failure": "retry",
            "context_drift": "rollback",
            "system_crash": "rollback",
            "access_denied": "report",
        }
        return strategy_map.get(failure_type, "heal")

    def _execute_strategy(self, strategy: str, failure: dict) -> bool:
        root_cause = self.analyze_root_cause(failure)
        failure_with_root = {**failure, "type": root_cause}

        if strategy == "heal":
            return self.healing.heal(failure_with_root)

        if strategy == "rollback":
            latest = self.rollback.latest()
            if latest:
                return self.rollback.rollback(latest)
            return self.healing.heal(failure_with_root)

        if strategy == "retry":
            return True

        if strategy == "report":
            return False

        return False

    def _enter_failsafe(self) -> None:
        self._failsafe = True
        if self.state and hasattr(self.state, "mark_unhealthy"):
            self.state.mark_unhealthy("Failsafe mode: too many failures")

    def exit_failsafe(self) -> None:
        self._failsafe = False
        self._failure_count = 0

    def is_failsafe(self) -> bool:
        return self._failsafe

    def predict(self, repo_map: dict, context: dict) -> dict:
        return self.predictor.predict(repo_map, context)

    def safe_execute(
        self,
        fn: Callable[..., Any],
        *args: Any,
        failure_type: str = "execution_error",
        severity: str = "medium",
        **kwargs: Any,
    ) -> Any:
        if self._failsafe:
            return None
        self.rollback.checkpoint("pre_exec")
        try:
            return self.retry.run(fn, *args, **kwargs)
        except Exception as exc:
            self.on_failure(failure_type, str(exc), severity=severity)
            return None

    def get_failure_log(self, last_n: int = 50) -> list[dict]:
        return json.loads(self.failure_log.read_text(encoding="utf-8"))[-last_n:]

    def stats(self) -> dict:
        log = json.loads(self.failure_log.read_text(encoding="utf-8"))
        total = len(log)
        resolved = sum(1 for item in log if item.get("resolved"))
        recent = [item for item in log if time.time() - item.get("timestamp", 0) < 3600]
        return {
            "total_failures": total,
            "resolved": resolved,
            "unresolved": total - resolved,
            "recent_1h": len(recent),
            "failure_count": self._failure_count,
            "failsafe_active": self._failsafe,
            "checkpoints": len(self.rollback.list_checkpoints()),
        }

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def _log_failure(self, failure: dict) -> None:
        log = json.loads(self.failure_log.read_text(encoding="utf-8"))
        log.append(failure)
        self.failure_log.write_text(json.dumps(log[-500:], indent=2), encoding="utf-8")

    def _update_log(self, failure: dict) -> None:
        try:
            log = json.loads(self.failure_log.read_text(encoding="utf-8"))
            for entry in reversed(log):
                if entry.get("timestamp") == failure.get("timestamp"):
                    entry["resolved"] = failure.get("resolved", False)
                    break
            self.failure_log.write_text(json.dumps(log[-500:], indent=2), encoding="utf-8")
        except Exception:
            return

