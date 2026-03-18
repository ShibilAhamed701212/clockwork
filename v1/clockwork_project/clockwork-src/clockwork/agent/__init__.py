"""
clockwork/agent/__init__.py
----------------------------
Agent Runtime subsystem.

Coordinates multiple AI agents working on the same repository safely.
Agents never modify the repository directly — they propose changes
which Clockwork validates before applying.

Public API::

    from clockwork.agent import AgentRuntime
    from clockwork.agent.models import Agent, Task, Capability

    rt = AgentRuntime(repo_root=Path("."))
    rt.initialise()

    rt.register_agent(Agent("claude_code", ["coding", "testing"], priority=1))
    task = rt.add_task("Implement login API", capability="coding")
    result = rt.run_task(task.task_id)

CLI commands added:
    clockwork agent list
    clockwork agent register <name>
    clockwork agent remove <name>
    clockwork agent status

    clockwork task add <description>
    clockwork task list
    clockwork task run <task_id>
    clockwork task fail <task_id>
    clockwork task retry <task_id>
    clockwork task locks
"""

from clockwork.agent.runtime import AgentRuntime
from clockwork.agent.models import Agent, Task, Capability, TaskStatus, ValidationResult
from clockwork.agent.registry import AgentRegistry
from clockwork.agent.lock_manager import LockManager, FileLockError

__all__ = [
    "AgentRuntime",
    "Agent",
    "Task",
    "Capability",
    "TaskStatus",
    "ValidationResult",
    "AgentRegistry",
    "LockManager",
    "FileLockError",
]

