from __future__ import annotations

from dataclasses import dataclass, field
import time


@dataclass
class ExecutionResult:
    success: bool
    output: object
    explanation: dict = field(default_factory=dict)
    error: str = ""
    violation: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": str(self.output)[:500],
            "explanation": self.explanation,
            "error": self.error,
            "violation": self.violation,
            "timestamp": self.timestamp,
        }


class SandboxExecutor:
    """Safe no-op executor used by compatibility layer."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self._log: list[dict] = []

    def execute(self, task: dict, agent_name: str = "general_agent") -> ExecutionResult:
        action = task.get("action", {})
        action_type = action.get("type", "unknown")
        target = action.get("target", "")
        output = f"[compat-exec] {action_type} -> {target}"
        result = ExecutionResult(success=True, output=output, explanation={"type": action_type, "target": target})
        self._record(task, result, agent_name)
        return result

    def _record(self, task: dict, result: ExecutionResult, agent: str) -> None:
        self._log.append({"task": task.get("name", ""), "agent": agent, "success": result.success, "violation": result.violation, "ts": result.timestamp})

    def log(self) -> list[dict]:
        return list(self._log)

    def violation_count(self) -> int:
        return sum(1 for entry in self._log if entry.get("violation"))

