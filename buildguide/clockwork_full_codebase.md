# Clockwork Full Codebase Export

## Directory Tree
```text
clockwork/
├── __init__.py
├── agent
│   ├── __init__.py
│   ├── lock_manager.py
│   ├── models.py
│   ├── registry.py
│   ├── router.py
│   └── runtime.py
├── brain
│   ├── __init__.py
│   ├── base.py
│   ├── brain_manager.py
│   ├── external_brain.py
│   ├── mini_brain.py
│   ├── minibrain.py
│   └── ollama_brain.py
├── cli
│   ├── __init__.py
│   ├── app.py
│   ├── commands
│   │   ├── __init__.py
│   │   ├── agent.py
│   │   ├── graph.py
│   │   ├── handoff.py
│   │   ├── index.py
│   │   ├── init.py
│   │   ├── registry.py
│   │   ├── scan.py
│   │   ├── security.py
│   │   ├── update.py
│   │   └── verify.py
│   ├── main.py
│   └── output.py
├── context
│   ├── __init__.py
│   ├── engine.py
│   ├── initializer.py
│   ├── models.py
│   └── schema.py
├── graph
│   ├── __init__.py
│   ├── builder.py
│   ├── graph_engine.py
│   ├── models.py
│   ├── queries.py
│   └── storage.py
├── handoff
│   ├── __init__.py
│   ├── aggregator.py
│   ├── brief_generator.py
│   ├── engine.py
│   ├── logger.py
│   ├── models.py
│   └── validator.py
├── index
│   ├── __init__.py
│   ├── incremental_scanner.py
│   ├── index_engine.py
│   ├── models.py
│   ├── storage.py
│   └── watcher.py
├── packaging
│   ├── __init__.py
│   ├── checksum.py
│   ├── cli_commands.py
│   ├── loader.py
│   ├── models.py
│   ├── packaging_engine.py
│   └── packer.py
├── registry
│   ├── __init__.py
│   ├── cache.py
│   ├── models.py
│   └── registry_engine.py
├── rules
│   ├── __init__.py
│   ├── default_rules.yaml
│   ├── engine.py
│   ├── evaluators.py
│   ├── loader.py
│   ├── models.py
│   └── rule_engine.py
├── scanner
│   ├── __init__.py
│   ├── filters.py
│   ├── frameworks.py
│   ├── language.py
│   ├── models.py
│   ├── repository_scanner.py
│   ├── scanner.py
│   └── symbols.py
└── security
    ├── __init__.py
    ├── file_guard.py
    ├── logger.py
    ├── models.py
    ├── scanner.py
    └── security_engine.py
```

---

## Source Code

### File: `clockwork/__init__.py`

```python

```

### File: `clockwork/agent/__init__.py`

```python
﻿"""
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


```

### File: `clockwork/agent/lock_manager.py`

```python
﻿"""
clockwork/agent/lock_manager.py
--------------------------------
File lock manager for the Agent Runtime (spec §9).

Prevents multiple agents from modifying the same file simultaneously.

Lock files are stored in:
    .clockwork/locks/<encoded_path>.lock

Each lock file contains JSON with the holding agent and timestamp.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional


class FileLockError(Exception):
    """Raised when a lock cannot be acquired."""


class LockManager:
    """
    Manages file locks inside .clockwork/locks/.

    Usage::

        lm = LockManager(clockwork_dir)
        lm.acquire("backend/auth.py", agent_name="claude_code")
        # ... do work ...
        lm.release("backend/auth.py", agent_name="claude_code")

    Or as a context manager::

        with lm.locked("backend/auth.py", "claude_code"):
            # exclusive access guaranteed
    """

    LOCK_TTL_SECONDS = 300   # stale locks older than 5 min are auto-released

    def __init__(self, clockwork_dir: Path) -> None:
        self.locks_dir = clockwork_dir / "locks"

    def _lock_path(self, file_path: str) -> Path:
        """Convert a repo-relative file path to its .lock file path."""
        safe_name = file_path.replace("/", "_").replace("\\", "_") + ".lock"
        return self.locks_dir / safe_name

    # ── acquire / release ──────────────────────────────────────────────────

    def acquire(self, file_path: str, agent_name: str) -> None:
        """
        Acquire a lock for *file_path*.

        Raises FileLockError if the file is already locked by another agent.
        Stale locks (older than LOCK_TTL_SECONDS) are silently cleared.
        """
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        lp = self._lock_path(file_path)

        if lp.exists():
            try:
                existing = json.loads(lp.read_text(encoding="utf-8"))
                holder   = existing.get("agent", "unknown")
                acquired = existing.get("acquired_at", 0)

                # same agent re-acquiring is fine
                if holder == agent_name:
                    return

                # stale lock? clear it
                if time.time() - acquired > self.LOCK_TTL_SECONDS:
                    lp.unlink(missing_ok=True)
                else:
                    raise FileLockError(
                        f"File '{file_path}' is locked by agent '{holder}'. "
                        "Try again later."
                    )
            except (json.JSONDecodeError, OSError):
                lp.unlink(missing_ok=True)

        lp.write_text(
            json.dumps({
                "file_path":   file_path,
                "agent":       agent_name,
                "acquired_at": time.time(),
            }),
            encoding="utf-8",
        )

    def release(self, file_path: str, agent_name: str) -> bool:
        """
        Release the lock for *file_path*.

        Returns False if the lock doesn't exist or is held by another agent.
        """
        lp = self._lock_path(file_path)
        if not lp.exists():
            return False

        try:
            existing = json.loads(lp.read_text(encoding="utf-8"))
            if existing.get("agent") != agent_name:
                return False
        except Exception:
            pass

        lp.unlink(missing_ok=True)
        return True

    def release_all(self, agent_name: str) -> int:
        """Release all locks held by *agent_name*. Returns count released."""
        released = 0
        if not self.locks_dir.exists():
            return 0
        for lp in self.locks_dir.glob("*.lock"):
            try:
                d = json.loads(lp.read_text(encoding="utf-8"))
                if d.get("agent") == agent_name:
                    lp.unlink(missing_ok=True)
                    released += 1
            except Exception:
                pass
        return released

    def is_locked(self, file_path: str) -> bool:
        """Return True if *file_path* is currently locked."""
        lp = self._lock_path(file_path)
        if not lp.exists():
            return False
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
            acquired = d.get("acquired_at", 0)
            if time.time() - acquired > self.LOCK_TTL_SECONDS:
                lp.unlink(missing_ok=True)
                return False
            return True
        except Exception:
            return False

    def lock_holder(self, file_path: str) -> Optional[str]:
        """Return the name of the agent holding the lock, or None."""
        lp = self._lock_path(file_path)
        if not lp.exists():
            return None
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
            return d.get("agent")
        except Exception:
            return None

    def list_locks(self) -> list[dict]:
        """Return all active locks as a list of dicts."""
        if not self.locks_dir.exists():
            return []
        locks = []
        now = time.time()
        for lp in self.locks_dir.glob("*.lock"):
            try:
                d = json.loads(lp.read_text(encoding="utf-8"))
                if now - d.get("acquired_at", 0) <= self.LOCK_TTL_SECONDS:
                    locks.append(d)
                else:
                    lp.unlink(missing_ok=True)   # clean stale lock
            except Exception:
                pass
        return locks

    # ── context manager ────────────────────────────────────────────────────

    class _Lock:
        def __init__(self, manager: "LockManager", file_path: str, agent: str):
            self._m = manager
            self._fp = file_path
            self._agent = agent

        def __enter__(self) -> "_Lock":
            self._m.acquire(self._fp, self._agent)
            return self

        def __exit__(self, *_) -> None:
            self._m.release(self._fp, self._agent)

    def locked(self, file_path: str, agent_name: str) -> "_Lock":
        """Return a context manager that acquires and auto-releases the lock."""
        return self._Lock(self, file_path, agent_name)


```

### File: `clockwork/agent/models.py`

```python
﻿"""
clockwork/agent/models.py
--------------------------
Data models for the Agent Runtime subsystem.

Covers spec §3-§8: Agent definition, capabilities, task queue,
task routing, validation pipeline.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Capability constants ───────────────────────────────────────────────────

class Capability:
    CODING               = "coding"
    TESTING              = "testing"
    DEBUGGING            = "debugging"
    ARCHITECTURE         = "architecture_analysis"
    DOCUMENTATION        = "documentation"
    SECURITY             = "security"
    REFACTORING          = "refactoring"

    ALL = [CODING, TESTING, DEBUGGING, ARCHITECTURE, DOCUMENTATION, SECURITY, REFACTORING]


# ── Task status constants ──────────────────────────────────────────────────

class TaskStatus:
    PENDING    = "pending"
    ASSIGNED   = "assigned"
    RUNNING    = "running"
    COMPLETED  = "completed"
    FAILED     = "failed"
    REJECTED   = "rejected"   # failed validation pipeline

    TERMINAL = {COMPLETED, FAILED, REJECTED}


# ── Agent model ────────────────────────────────────────────────────────────

@dataclass
class Agent:
    """
    Represents a registered AI agent (spec §3-§4).

    An agent declares its capabilities and priority so the
    task router can dispatch the best-fit agent for each task.
    """

    name:         str
    capabilities: list[str]       = field(default_factory=list)
    priority:     int             = 10          # lower = higher priority
    description:  str             = ""
    registered_at: float          = field(default_factory=time.time)

    def can_handle(self, capability: str) -> bool:
        """Return True if this agent declares the given capability."""
        return capability in self.capabilities

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":          self.name,
            "capabilities":  self.capabilities,
            "priority":      self.priority,
            "description":   self.description,
            "registered_at": self.registered_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Agent":
        return cls(
            name=d["name"],
            capabilities=d.get("capabilities", []),
            priority=d.get("priority", 10),
            description=d.get("description", ""),
            registered_at=d.get("registered_at", time.time()),
        )


# ── Task model ─────────────────────────────────────────────────────────────

@dataclass
class Task:
    """
    A single unit of work in the task queue (spec §6).

    Tracks lifecycle from pending → assigned → running → completed/failed.
    """

    task_id:             str
    description:         str
    required_capability: str        = Capability.CODING
    status:              str        = TaskStatus.PENDING
    assigned_agent:      str        = ""
    created_at:          float      = field(default_factory=time.time)
    updated_at:          float      = field(default_factory=time.time)
    completed_at:        float      = 0.0
    result:              str        = ""         # outcome message
    proposed_changes:    list[str]  = field(default_factory=list)
    validation_errors:   list[str]  = field(default_factory=list)
    retry_count:         int        = 0

    @classmethod
    def new(cls, description: str, capability: str = Capability.CODING) -> "Task":
        return cls(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            description=description,
            required_capability=capability,
        )

    def assign(self, agent_name: str) -> None:
        self.assigned_agent = agent_name
        self.status         = TaskStatus.ASSIGNED
        self.updated_at     = time.time()

    def start(self) -> None:
        self.status     = TaskStatus.RUNNING
        self.updated_at = time.time()

    def complete(self, result: str = "") -> None:
        self.status       = TaskStatus.COMPLETED
        self.result       = result
        self.completed_at = time.time()
        self.updated_at   = time.time()

    def fail(self, reason: str = "") -> None:
        self.status     = TaskStatus.FAILED
        self.result     = reason
        self.updated_at = time.time()

    def reject(self, errors: list[str]) -> None:
        self.status            = TaskStatus.REJECTED
        self.validation_errors = errors
        self.result            = "Rejected by validation pipeline"
        self.updated_at        = time.time()

    def is_terminal(self) -> bool:
        return self.status in TaskStatus.TERMINAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id":             self.task_id,
            "description":         self.description,
            "required_capability": self.required_capability,
            "status":              self.status,
            "assigned_agent":      self.assigned_agent,
            "created_at":          self.created_at,
            "updated_at":          self.updated_at,
            "completed_at":        self.completed_at,
            "result":              self.result,
            "proposed_changes":    self.proposed_changes,
            "validation_errors":   self.validation_errors,
            "retry_count":         self.retry_count,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Task":
        t = cls(
            task_id=d["task_id"],
            description=d["description"],
            required_capability=d.get("required_capability", Capability.CODING),
            status=d.get("status", TaskStatus.PENDING),
            assigned_agent=d.get("assigned_agent", ""),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            completed_at=d.get("completed_at", 0.0),
            result=d.get("result", ""),
            proposed_changes=d.get("proposed_changes", []),
            validation_errors=d.get("validation_errors", []),
            retry_count=d.get("retry_count", 0),
        )
        return t


# ── Agent log entry ────────────────────────────────────────────────────────

@dataclass
class AgentLogEntry:
    """One record in .clockwork/agent_log.json (spec §11)."""

    timestamp:  str
    agent:      str
    task_id:    str
    task_desc:  str
    status:     str
    message:    str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent":     self.agent,
            "task_id":   self.task_id,
            "task":      self.task_desc,
            "status":    self.status,
            "message":   self.message,
        }


# ── Validation result ──────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of the validation pipeline (spec §10)."""

    passed:   bool
    errors:   list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":   self.passed,
            "errors":   self.errors,
            "warnings": self.warnings,
        }


```

### File: `clockwork/agent/registry.py`

```python
﻿"""
clockwork/agent/registry.py
----------------------------
Persistent storage for agents and tasks.

Manages:
  .clockwork/agents.json  — registered agents  (spec §4)
  .clockwork/tasks.json   — task queue          (spec §6)
  .clockwork/agent_log.json — action log        (spec §11)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import Agent, AgentLogEntry, Task, TaskStatus


class AgentRegistry:
    """
    Reads and writes the agent registry and task queue.

    All operations are file-based so multiple processes can share
    the same .clockwork directory safely (last-write-wins for now;
    distributed locking is a future enhancement).
    """

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir  = clockwork_dir
        self.agents_path    = clockwork_dir / "agents.json"
        self.tasks_path     = clockwork_dir / "tasks.json"
        self.log_path       = clockwork_dir / "agent_log.json"

    # ── initialise ─────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Create empty registry files if they don't exist."""
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        if not self.agents_path.exists():
            self._write_agents([])
        if not self.tasks_path.exists():
            self._write_tasks([])
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")

    # ── agent CRUD ─────────────────────────────────────────────────────────

    def list_agents(self) -> list[Agent]:
        """Return all registered agents."""
        return self._read_agents()

    def get_agent(self, name: str) -> Optional[Agent]:
        """Return agent by name, or None."""
        for a in self._read_agents():
            if a.name == name:
                return a
        return None

    def register_agent(self, agent: Agent) -> bool:
        """
        Register a new agent.  Returns False if name already exists.
        """
        agents = self._read_agents()
        if any(a.name == agent.name for a in agents):
            return False
        agents.append(agent)
        self._write_agents(agents)
        return True

    def update_agent(self, agent: Agent) -> bool:
        """Update an existing agent. Returns False if not found."""
        agents = self._read_agents()
        for i, a in enumerate(agents):
            if a.name == agent.name:
                agents[i] = agent
                self._write_agents(agents)
                return True
        return False

    def remove_agent(self, name: str) -> bool:
        """Remove an agent by name. Returns False if not found."""
        agents = self._read_agents()
        new    = [a for a in agents if a.name != name]
        if len(new) == len(agents):
            return False
        self._write_agents(new)
        return True

    def agents_for_capability(self, capability: str) -> list[Agent]:
        """
        Return agents that can handle the given capability,
        sorted by priority ascending (lower = higher priority).
        """
        return sorted(
            [a for a in self._read_agents() if a.can_handle(capability)],
            key=lambda a: a.priority,
        )

    # ── task CRUD ──────────────────────────────────────────────────────────

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        """Return all tasks, optionally filtered by status."""
        tasks = self._read_tasks()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def get_task(self, task_id: str) -> Optional[Task]:
        for t in self._read_tasks():
            if t.task_id == task_id:
                return t
        return None

    def add_task(self, task: Task) -> Task:
        """Append a task to the queue and return it."""
        tasks = self._read_tasks()
        tasks.append(task)
        self._write_tasks(tasks)
        return task

    def update_task(self, task: Task) -> bool:
        """Persist a modified task. Returns False if not found."""
        tasks = self._read_tasks()
        for i, t in enumerate(tasks):
            if t.task_id == task.task_id:
                tasks[i] = task
                self._write_tasks(tasks)
                return True
        return False

    def pending_tasks(self) -> list[Task]:
        return self.list_tasks(TaskStatus.PENDING)

    def active_tasks(self) -> list[Task]:
        return [
            t for t in self._read_tasks()
            if t.status in (TaskStatus.ASSIGNED, TaskStatus.RUNNING)
        ]

    def stats(self) -> dict[str, int]:
        """Return per-status task counts."""
        tasks = self._read_tasks()
        counts: dict[str, int] = {}
        for t in tasks:
            counts[t.status] = counts.get(t.status, 0) + 1
        return counts

    # ── agent log ──────────────────────────────────────────────────────────

    def log(
        self,
        agent: str,
        task: Task,
        status: str,
        message: str = "",
    ) -> None:
        """Append one entry to agent_log.json."""
        try:
            entries = json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            entries = []

        entry = AgentLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            task_id=task.task_id,
            task_desc=task.description,
            status=status,
            message=message,
        )
        entries.append(entry.to_dict())

        self.log_path.write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )

    def read_log(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    # ── private I/O ────────────────────────────────────────────────────────

    def _read_agents(self) -> list[Agent]:
        if not self.agents_path.exists():
            return []
        try:
            data = json.loads(self.agents_path.read_text(encoding="utf-8"))
            raw  = data if isinstance(data, list) else data.get("agents", [])
            return [Agent.from_dict(a) for a in raw]
        except Exception:
            return []

    def _write_agents(self, agents: list[Agent]) -> None:
        self.agents_path.write_text(
            json.dumps({"agents": [a.to_dict() for a in agents]}, indent=2),
            encoding="utf-8",
        )

    def _read_tasks(self) -> list[Task]:
        if not self.tasks_path.exists():
            return []
        try:
            data = json.loads(self.tasks_path.read_text(encoding="utf-8"))
            raw  = data if isinstance(data, list) else data.get("tasks", [])
            return [Task.from_dict(t) for t in raw]
        except Exception:
            return []

    def _write_tasks(self, tasks: list[Task]) -> None:
        self.tasks_path.write_text(
            json.dumps({"tasks": [t.to_dict() for t in tasks]}, indent=2),
            encoding="utf-8",
        )


```

### File: `clockwork/agent/router.py`

```python
﻿"""
clockwork/agent/router.py
--------------------------
Task router and validation pipeline for the Agent Runtime (spec §7, §10).

Routing algorithm (spec §7):
    1. match capability
    2. select highest priority agent
    3. dispatch task

Validation pipeline (spec §10):
    Agent Proposal
        ↓
    Rule Engine
        ↓
    Brain Analysis
        ↓
    Context Validation
        ↓
    Repository Update
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .models import Agent, Task, TaskStatus, ValidationResult
from .registry import AgentRegistry


class TaskRouter:
    """
    Routes pending tasks to the best-fit registered agent.

    Usage::

        router = TaskRouter(registry)
        agent  = router.route(task)
        if agent:
            task.assign(agent.name)
            registry.update_task(task)
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry

    def route(self, task: Task) -> Optional[Agent]:
        """
        Find the best agent for *task* based on capability + priority.

        Returns None if no suitable agent is registered.
        """
        candidates = self._registry.agents_for_capability(
            task.required_capability
        )
        if not candidates:
            return None

        # exclude agents that already have too many active tasks (>3)
        active = self._registry.active_tasks()
        busy: dict[str, int] = {}
        for t in active:
            busy[t.assigned_agent] = busy.get(t.assigned_agent, 0) + 1

        available = [a for a in candidates if busy.get(a.name, 0) < 3]
        if not available:
            # fall back to least-busy agent
            available = sorted(candidates, key=lambda a: busy.get(a.name, 0))

        return available[0]

    def dispatch(self, task: Task) -> Optional[str]:
        """
        Route and assign a task in one step.

        Returns the assigned agent name, or None if no agent available.
        """
        agent = self.route(task)
        if agent is None:
            return None
        task.assign(agent.name)
        self._registry.update_task(task)
        self._registry.log(agent.name, task, TaskStatus.ASSIGNED)
        return agent.name


class ValidationPipeline:
    """
    Runs the spec §10 validation pipeline on a task's proposed changes.

    Pipeline stages:
        1. Rule Engine validation
        2. Brain Analysis
        3. Context validation

    Each stage may add errors or warnings to the result.
    Gracefully skips stages whose subsystems are not available.
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root
        self.clockwork_dir = repo_root / ".clockwork"

    def validate(self, task: Task) -> ValidationResult:
        """
        Run all pipeline stages against the task's proposed_changes.

        Returns a ValidationResult with passed=True only when all
        stages pass with no errors.
        """
        t0     = time.perf_counter()
        errors:   list[str] = []
        warnings: list[str] = []

        # ── Stage 1: Rule Engine ───────────────────────────────────────────
        rule_errors, rule_warnings = self._run_rule_engine(task)
        errors.extend(rule_errors)
        warnings.extend(rule_warnings)

        # ── Stage 2: Brain Analysis ────────────────────────────────────────
        brain_errors, brain_warnings = self._run_brain(task)
        errors.extend(brain_errors)
        warnings.extend(brain_warnings)

        # ── Stage 3: Context Validation ────────────────────────────────────
        ctx_errors = self._run_context_validation(task)
        errors.extend(ctx_errors)

        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed > 200:
            warnings.append(
                f"Validation took {elapsed:.0f} ms (target: <200 ms)"
            )

        return ValidationResult(
            passed=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    # ── Stage implementations ──────────────────────────────────────────────

    def _run_rule_engine(self, task: Task) -> tuple[list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []
        try:
            from clockwork.rules import RuleEngine
            engine = RuleEngine(self.repo_root)
            report = engine.evaluate(list(task.proposed_changes))
            if not report.passed:
                errors.extend([str(v) for v in report.blocking_violations])
            warnings.extend([str(v) for v in report.warnings])
        except ImportError:
            warnings.append("Rule Engine not available — skipping rule checks.")
        except Exception as exc:
            warnings.append(f"Rule Engine error: {exc}")
        return errors, warnings

    def _run_brain(self, task: Task) -> tuple[list[str], list[str]]:
        errors:   list[str] = []
        warnings: list[str] = []

        # check if any proposed change would delete a file that other
        # modules depend on (uses knowledge graph if available)
        db_path = self.clockwork_dir / "knowledge_graph.db"
        if db_path.exists():
            try:
                from clockwork.graph import GraphEngine
                engine = GraphEngine(self.repo_root)
                try:
                    q = engine.query()
                    for change in task.proposed_changes:
                        if change.lower().startswith("delete "):
                            fp = change[7:].strip()
                            safe, reasons = q.is_safe_to_delete(fp)
                            if not safe:
                                errors.extend(reasons)
                finally:
                    engine.close()
            except Exception as exc:
                warnings.append(f"Brain graph check error: {exc}")
        return errors, warnings

    def _run_context_validation(self, task: Task) -> list[str]:
        errors: list[str] = []
        try:
            from clockwork.context import ContextEngine
            engine = ContextEngine(self.clockwork_dir)
            issues = engine.validate()
            if issues:
                errors.extend(issues)
        except ImportError:
            pass
        except Exception as exc:
            errors.append(f"Context validation error: {exc}")
        return errors


```

### File: `clockwork/agent/runtime.py`

```python
﻿"""
clockwork/agent/runtime.py
---------------------------
Main Agent Runtime engine (spec §2, §13, §14).

Orchestrates:
  - AgentRegistry   (agents.json + tasks.json)
  - TaskRouter      (capability matching + priority dispatch)
  - LockManager     (conflict prevention)
  - ValidationPipeline (rule + brain + context checks)
  - Monitoring metrics

Spec §2 flow:
    Agent Task
        ↓
    Clockwork Runtime
        ↓
    Rule Engine Validation
        ↓
    Brain Analysis
        ↓
    Repository Update
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .lock_manager import FileLockError, LockManager
from .models import Agent, Capability, Task, TaskStatus, ValidationResult
from .registry import AgentRegistry
from .router import TaskRouter, ValidationPipeline


class AgentRuntime:
    """
    Top-level facade for the Agent Runtime subsystem.

    Usage::

        rt = AgentRuntime(repo_root=Path("."))
        rt.initialise()

        rt.register_agent(Agent("claude_code", ["coding", "testing"], priority=1))
        task = rt.add_task("Implement login API", capability="coding")
        result = rt.run_task(task.task_id)
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root      = repo_root.resolve()
        self.clockwork_dir  = self.repo_root / ".clockwork"
        self.registry       = AgentRegistry(self.clockwork_dir)
        self.lock_manager   = LockManager(self.clockwork_dir)
        self.router         = TaskRouter(self.registry)
        self.pipeline       = ValidationPipeline(self.repo_root)

    # ── setup ──────────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Create registry files and directory structure."""
        self.registry.initialise()
        (self.clockwork_dir / "locks").mkdir(parents=True, exist_ok=True)

    # ── agent management ───────────────────────────────────────────────────

    def register_agent(self, agent: Agent) -> bool:
        """Register a new agent. Returns False if name already taken."""
        return self.registry.register_agent(agent)

    def list_agents(self) -> list[Agent]:
        return self.registry.list_agents()

    def get_agent(self, name: str) -> Optional[Agent]:
        return self.registry.get_agent(name)

    def remove_agent(self, name: str) -> bool:
        return self.registry.remove_agent(name)

    # ── task management ────────────────────────────────────────────────────

    def add_task(
        self,
        description: str,
        capability: str = Capability.CODING,
    ) -> Task:
        """
        Create and queue a new task.

        Automatically routes it to the best available agent.
        """
        task = Task.new(description, capability)
        self.registry.add_task(task)

        # auto-dispatch if an agent is available
        assigned = self.router.dispatch(task)
        if assigned:
            pass   # task updated in registry by dispatch()

        return task

    def list_tasks(self, status: Optional[str] = None) -> list[Task]:
        return self.registry.list_tasks(status)

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.registry.get_task(task_id)

    # ── task execution ─────────────────────────────────────────────────────

    def run_task(self, task_id: str) -> ValidationResult:
        """
        Execute the validation pipeline for a task (spec §10).

        This represents the "controlled execution environment" — agents
        propose changes, Clockwork validates them before applying.

        Returns the ValidationResult.
        """
        task = self.registry.get_task(task_id)
        if task is None:
            return ValidationResult(
                passed=False, errors=[f"Task '{task_id}' not found."]
            )

        if task.status == TaskStatus.PENDING:
            # try to route if not yet assigned
            self.router.dispatch(task)
            task = self.registry.get_task(task_id)

        agent_name = task.assigned_agent or "unassigned"

        # acquire locks on proposed files
        locked_files: list[str] = []
        try:
            for fp in task.proposed_changes:
                clean = fp.replace("modify ", "").replace("delete ", "").strip()
                if clean:
                    try:
                        self.lock_manager.acquire(clean, agent_name)
                        locked_files.append(clean)
                    except FileLockError as e:
                        task.fail(str(e))
                        self.registry.update_task(task)
                        self.registry.log(agent_name, task, TaskStatus.FAILED, str(e))
                        return ValidationResult(passed=False, errors=[str(e)])

            # mark running
            task.start()
            self.registry.update_task(task)

            # run validation pipeline
            result = self.pipeline.validate(task)

            if result.passed:
                task.complete("Validation passed — changes approved.")
                self.registry.log(agent_name, task, TaskStatus.COMPLETED)
            else:
                task.reject(result.errors)
                self.registry.log(
                    agent_name, task, TaskStatus.REJECTED,
                    "; ".join(result.errors),
                )

            self.registry.update_task(task)
            return result

        finally:
            # always release locks
            for fp in locked_files:
                self.lock_manager.release(fp, agent_name)

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """Manually mark a task as failed (spec §14)."""
        task = self.registry.get_task(task_id)
        if task is None:
            return False
        task.fail(reason)
        self.registry.update_task(task)
        self.registry.log(task.assigned_agent or "system", task, TaskStatus.FAILED, reason)
        return True

    def retry_task(self, task_id: str) -> Optional[str]:
        """
        Retry a failed task with a different agent if available (spec §14).

        Returns the newly assigned agent name, or None.
        """
        task = self.registry.get_task(task_id)
        if task is None or task.status not in (TaskStatus.FAILED, TaskStatus.REJECTED):
            return None

        task.retry_count += 1
        task.status       = TaskStatus.PENDING
        task.result       = ""
        task.validation_errors = []
        self.registry.update_task(task)

        # exclude previous agent from routing
        old_agent = task.assigned_agent
        task.assigned_agent = ""

        assigned = self.router.dispatch(task)
        if assigned == old_agent:
            # try to find a different one
            candidates = self.registry.agents_for_capability(
                task.required_capability
            )
            others = [a for a in candidates if a.name != old_agent]
            if others:
                task.assign(others[0].name)
                self.registry.update_task(task)
                assigned = others[0].name

        return assigned

    # ── monitoring (spec §13) ──────────────────────────────────────────────

    def stats(self) -> dict:
        """Return runtime metrics."""
        task_counts = self.registry.stats()
        agents      = self.registry.list_agents()
        locks       = self.lock_manager.list_locks()
        log         = self.registry.read_log()

        return {
            "agents":          len(agents),
            "tasks_by_status": task_counts,
            "total_tasks":     sum(task_counts.values()),
            "active_locks":    len(locks),
            "log_entries":     len(log),
        }


```

### File: `clockwork/brain/__init__.py`

```python
﻿# clockwork/brain/__init__.py
from .brain_manager import BrainManager
from .base import BrainInterface, BrainResult, BrainStatus

__all__ = ["BrainManager", "BrainInterface", "BrainResult", "BrainStatus"]

```

### File: `clockwork/brain/base.py`

```python
﻿"""
clockwork/brain/base.py

Base interface and data models shared by all brain reasoning engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BrainStatus(str, Enum):
    """Possible outcomes of a brain analysis."""
    VALID    = "VALID"
    WARNING  = "WARNING"
    REJECTED = "REJECTED"


class RiskLevel(str, Enum):
    """Risk classification for a change."""
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


@dataclass
class BrainResult:
    """
    Standardised result returned by every reasoning engine.

    Attributes
    ----------
    status:      VALID | WARNING | REJECTED
    confidence:  0.0 – 1.0  (higher = more certain)
    risk_level:  low | medium | high
    explanation: human-readable summary of the decision
    violations:  list of specific rule/architecture violations found
    warnings:    list of non-blocking concerns
    """
    status:      BrainStatus
    confidence:  float
    risk_level:  RiskLevel
    explanation: str
    violations:  list[str] = field(default_factory=list)
    warnings:    list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dictionary (JSON-safe)."""
        return {
            "status":      self.status.value,
            "confidence":  round(self.confidence, 4),
            "risk_level":  self.risk_level.value,
            "explanation": self.explanation,
            "violations":  self.violations,
            "warnings":    self.warnings,
        }

    @property
    def passed(self) -> bool:
        """Return True if the change is VALID or WARNING (not REJECTED)."""
        return self.status != BrainStatus.REJECTED


class BrainInterface(ABC):
    """Abstract base class every reasoning engine must implement."""

    @abstractmethod
    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        """
        Analyse a repository change and return a validation result.

        Parameters
        ----------
        context:   Contents of .clockwork/context.yaml as a dict
        repo_diff: Structured diff produced by the Repository Scanner
        rules:     List of active rule definitions from the Rule Engine
        """

```

### File: `clockwork/brain/brain_manager.py`

```python
﻿"""
clockwork/brain/brain_manager.py

BrainManager — selects the reasoning engine and runs multi-layer validation.

Engine selection (from .clockwork/config.yaml  →  brain.mode):
  minibrain  — default, always available, deterministic
  ollama     — local LLM via Ollama
  external   — OpenAI / Anthropic / custom endpoint
  auto       — tries Ollama first, falls back to MiniBrain

Multi-layer validation (spec §15):
  Layer 1 — MiniBrain  (always runs)
  Layer 2 — AI engine  (if configured and available)

All decisions are appended to .clockwork/brain_log.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel
from .minibrain import MiniBrain
from .ollama_brain import OllamaBrain

_CLOCKWORK_DIR = Path(".clockwork")


class BrainManager:
    """Orchestrates reasoning engine selection and multi-layer validation."""

    def __init__(self, clockwork_dir: Path | None = None) -> None:
        self._clockwork_dir = clockwork_dir or _CLOCKWORK_DIR
        self._config = self._load_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        """Execute multi-layer validation and return the final BrainResult."""
        mini_result = MiniBrain().analyze_change(context, repo_diff, rules)
        self._log(mini_result, engine="MiniBrain")

        # Short-circuit: deterministic rejection — skip expensive AI layer
        if mini_result.status == BrainStatus.REJECTED:
            return mini_result

        mode = self._config.get("brain", {}).get("mode", "minibrain").lower()

        if mode in ("ollama", "auto"):
            ai_result = self._run_ollama(context, repo_diff, rules)
            if ai_result:
                self._log(ai_result, engine="OllamaBrain")
                return self._merge(mini_result, ai_result)

        if mode == "external":
            ai_result = self._run_external(context, repo_diff, rules)
            if ai_result:
                self._log(ai_result, engine="ExternalBrain")
                return self._merge(mini_result, ai_result)

        return mini_result

    # ------------------------------------------------------------------
    # Engine runners
    # ------------------------------------------------------------------

    def _run_ollama(
        self, context: dict[str, Any], repo_diff: dict[str, Any], rules: list[dict[str, Any]]
    ) -> BrainResult | None:
        if not OllamaBrain.is_available():
            return None
        model = self._config.get("brain", {}).get("model", "deepseek-coder")
        return OllamaBrain(model=model).analyze_change(context, repo_diff, rules)

    def _run_external(
        self, context: dict[str, Any], repo_diff: dict[str, Any], rules: list[dict[str, Any]]
    ) -> BrainResult | None:
        brain_cfg = self._config.get("brain", {})
        if not brain_cfg.get("provider"):
            return None
        from .external_brain import ExternalBrain  # noqa: PLC0415
        return ExternalBrain(config=brain_cfg).analyze_change(context, repo_diff, rules)

    # ------------------------------------------------------------------
    # Result merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge(layer1: BrainResult, layer2: BrainResult) -> BrainResult:
        """Combine two results, favouring the more severe outcome."""
        severity = {BrainStatus.VALID: 0, BrainStatus.WARNING: 1, BrainStatus.REJECTED: 2}
        dominant, other = (layer2, layer1) if severity[layer2.status] >= severity[layer1.status] \
                           else (layer1, layer2)
        return BrainResult(
            status=dominant.status,
            confidence=round((layer1.confidence + layer2.confidence) / 2, 4),
            risk_level=dominant.risk_level,
            explanation=dominant.explanation,
            violations=list(dict.fromkeys(dominant.violations + other.violations)),
            warnings=list(dict.fromkeys(dominant.warnings   + other.warnings)),
        )

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def _load_config(self) -> dict[str, Any]:
        config_path = self._clockwork_dir / "config.yaml"
        if not config_path.exists():
            return {}
        try:
            with config_path.open("r", encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except Exception:  # noqa: BLE001
            return {}

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, result: BrainResult, engine: str) -> None:
        """Append a brain decision to .clockwork/brain_log.json."""
        log_path = self._clockwork_dir / "brain_log.json"
        entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "engine": engine,
            **result.to_dict(),
        }
        existing: list[dict[str, Any]] = []
        if log_path.exists():
            try:
                with log_path.open("r", encoding="utf-8") as fh:
                    existing = json.load(fh)
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.append(entry)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as fh:
                json.dump(existing, fh, indent=2)
        except OSError:
            pass  # Non-fatal: logging must never block validation

```

### File: `clockwork/brain/external_brain.py`

```python
﻿"""
clockwork/brain/external_brain.py

ExternalBrain — reasoning engine backed by OpenAI, Anthropic, or custom LLM API.

Configuration via .clockwork/config.yaml:
  brain:
    mode: external
    provider: openai        # openai | anthropic | custom
    model: gpt-4o
    api_key: sk-...
    endpoint: https://...   # only for 'custom'
"""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_TIMEOUT = 30

_SYSTEM_PROMPT = """\
You are Clockwork Brain, a repository intelligence verification engine.
Respond ONLY with a valid JSON object — no prose, no markdown fences.

JSON schema:
{
  "status": "VALID" | "WARNING" | "REJECTED",
  "confidence": <float 0.0-1.0>,
  "risk_level": "low" | "medium" | "high",
  "explanation": "<one paragraph>",
  "violations": ["<violation>", ...],
  "warnings":   ["<warning>",   ...]
}
"""


class ExternalBrain(BrainInterface):
    """Reasoning engine backed by an external LLM API."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.provider: str = config.get("provider", "openai").lower()
        self.model:    str = config.get("model", "gpt-4o")
        self.api_key:  str = self._resolve_api_key(config)
        self.endpoint: str = config.get("endpoint", self._default_endpoint())

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        user_prompt = self._build_prompt(context, repo_diff, rules)
        try:
            raw = self._call_api(user_prompt)
            return self._parse_response(raw)
        except Exception as exc:  # noqa: BLE001
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.15,
                risk_level=RiskLevel.MEDIUM,
                explanation=f"ExternalBrain API call failed: {exc}. Manual review required.",
                warnings=[f"API error: {exc}"],
            )

    def _build_prompt(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> str:
        return (
            f"PROJECT CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            f"REPOSITORY DIFF:\n{json.dumps({k: repo_diff.get(k,[]) for k in ('added','deleted','modified')}, indent=2)}\n\n"
            f"ACTIVE RULES:\n{json.dumps([{'id': r.get('id'), 'description': r.get('description')} for r in rules], indent=2)}\n\n"
            "Analyse the diff. Respond ONLY with the required JSON."
        )

    def _call_api(self, user_prompt: str) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(user_prompt)
        return self._call_openai_compatible(user_prompt)

    def _call_openai_compatible(self, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0,
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["choices"][0]["message"]["content"]

    def _call_anthropic(self, user_prompt: str) -> str:
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 1024,
            "system": _SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body["content"][0]["text"]

    def _parse_response(self, raw: str) -> BrainResult:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            return BrainResult(
                status=BrainStatus.WARNING, confidence=0.25, risk_level=RiskLevel.MEDIUM,
                explanation="ExternalBrain returned non-JSON. Manual review required.",
                warnings=["Could not parse external API response as JSON."],
            )
        try:
            status = BrainStatus(data.get("status", "WARNING").upper())
        except ValueError:
            status = BrainStatus.WARNING
        try:
            risk = RiskLevel(data.get("risk_level", "medium").lower())
        except ValueError:
            risk = RiskLevel.MEDIUM
        return BrainResult(
            status=status,
            confidence=float(data.get("confidence", 0.5)),
            risk_level=risk,
            explanation=data.get("explanation", "No explanation provided."),
            violations=data.get("violations", []),
            warnings=data.get("warnings", []),
        )

    def _default_endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages" if self.provider == "anthropic" \
               else "https://api.openai.com/v1/chat/completions"

    def _resolve_api_key(self, config: dict[str, Any]) -> str:
        if config.get("api_key"):
            return config["api_key"]
        env_map = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}
        return os.environ.get(env_map.get(self.provider, "EXTERNAL_BRAIN_API_KEY"), "")

```

### File: `clockwork/brain/mini_brain.py`

```python
from clockwork.brain.minibrain import MiniBrain

__all__ = ['MiniBrain']

```

### File: `clockwork/brain/minibrain.py`

```python
﻿"""
clockwork/brain/minibrain.py

MiniBrain — the default, fully-offline, deterministic reasoning engine.

Uses static analysis techniques:
  * repository diff classification
  * AST-based file inspection
  * dependency cross-checking against context
  * architecture rule matching

No external services or AI models are required.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_CORE_MODULE_PATTERNS: list[str] = [
    r"^clockwork/",
    r"__init__\.py$",
    r"pyproject\.toml$",
    r"setup\.py$",
]

_DEP_FILE_PATTERNS: list[str] = [
    "pyproject.toml",
    "requirements.txt",
    "requirements*.txt",
    "setup.cfg",
]

_FRONTEND_DIRS: list[str] = ["frontend", "ui", "web", "client", "static"]

_DB_IMPORT_SIGNATURES: list[str] = [
    "sqlalchemy", "sqlite3", "psycopg2", "pymysql", "motor", "pymongo",
]


class MiniBrain(BrainInterface):
    """Deterministic reasoning engine — no AI model required."""

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        violations: list[str] = []
        warnings:   list[str] = []

        added:         list[str]       = repo_diff.get("added", [])
        deleted:       list[str]       = repo_diff.get("deleted", [])
        modified:      list[str]       = repo_diff.get("modified", [])
        file_contents: dict[str, str]  = repo_diff.get("file_contents", {})

        violations.extend(self._detect_core_deletions(deleted))
        violations.extend(self._check_dependency_context(context, deleted, modified, file_contents))
        violations.extend(self._check_layer_violations(added + modified, file_contents))

        ctx_issues, ctx_warnings = self._check_context_consistency(context, added, deleted, modified)
        violations.extend(ctx_issues)
        warnings.extend(ctx_warnings)

        violations.extend(self._apply_rules(rules, added, deleted, modified, file_contents))
        warnings.extend(self._warn_new_modules(added))

        return self._build_result(violations, warnings)

    def _detect_core_deletions(self, deleted: list[str]) -> list[str]:
        issues: list[str] = []
        for path in deleted:
            for pattern in _CORE_MODULE_PATTERNS:
                if re.search(pattern, path):
                    issues.append(f"Core module deletion detected: {path}")
                    break
        return issues

    def _check_dependency_context(
        self,
        context:       dict[str, Any],
        deleted:       list[str],
        modified:      list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues:     list[str] = []
        frameworks: list[str] = context.get("frameworks", [])
        changed_dep_files = [
            p for p in deleted + modified
            if any(p.endswith(pat.lstrip("*")) for pat in _DEP_FILE_PATTERNS)
        ]
        for dep_file in changed_dep_files:
            content = file_contents.get(dep_file, "")
            if not content:
                continue
            for framework in frameworks:
                if framework.lower() not in content.lower():
                    issues.append(
                        f"Context declares framework '{framework}' but it is missing "
                        f"from modified dependency file '{dep_file}'."
                    )
        return issues

    def _check_layer_violations(
        self,
        changed_paths: list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues: list[str] = []
        for path in changed_paths:
            path_lower = path.lower()
            is_frontend = any(
                f"/{d}/" in path_lower or path_lower.startswith(d + "/")
                for d in _FRONTEND_DIRS
            )
            if not is_frontend or not path.endswith(".py"):
                continue
            content = file_contents.get(path, "")
            if not content:
                continue
            try:
                tree = ast.parse(content, filename=path)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = ""
                    if isinstance(node, ast.Import):
                        module = node.names[0].name if node.names else ""
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        module = node.module
                    for sig in _DB_IMPORT_SIGNATURES:
                        if sig in module.lower():
                            issues.append(
                                f"Architecture violation: frontend module '{path}' "
                                f"directly imports database library '{module}'."
                            )
        return issues

    def _check_context_consistency(
        self,
        context:  dict[str, Any],
        added:    list[str],
        deleted:  list[str],
        modified: list[str],
    ) -> tuple[list[str], list[str]]:
        issues:   list[str] = []
        warnings: list[str] = []
        modules: list[str] = context.get("modules", [])
        for module in modules:
            module_path = module.replace(".", "/")
            deleted_match = any(module_path in d for d in deleted)
            added_match   = any(module_path in a for a in added)
            if deleted_match and not added_match:
                issues.append(
                    f"Context references module '{module}' but it was deleted from the repository."
                )
        if "context.yaml" in modified or ".clockwork/context.yaml" in modified:
            warnings.append("context.yaml was modified. Verify context accuracy manually.")
        return issues, warnings

    def _apply_rules(
        self,
        rules:         list[dict[str, Any]],
        added:         list[str],
        deleted:       list[str],
        modified:      list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues:    list[str] = []
        all_paths: list[str] = added + deleted + modified
        for rule in rules:
            rule_id    = rule.get("id", "unknown")
            description = rule.get("description", "")
            pattern     = rule.get("pattern", "")
            applies_to  = rule.get("applies_to", "path")
            if not pattern:
                continue
            try:
                compiled = re.compile(pattern)
            except re.error:
                continue
            if applies_to == "path":
                for path in all_paths:
                    if compiled.search(path):
                        issues.append(f"Rule '{rule_id}' violated by path '{path}': {description}")
            elif applies_to == "content":
                for path in all_paths:
                    content = file_contents.get(path, "")
                    if content and compiled.search(content):
                        issues.append(f"Rule '{rule_id}' violated in '{path}': {description}")
        return issues

    def _warn_new_modules(self, added: list[str]) -> list[str]:
        warnings: list[str] = []
        for path in added:
            if path.endswith(".py") and "__init__" not in path:
                warnings.append(f"New module introduced: '{path}'. Verify it follows architecture guidelines.")
        return warnings

    def _build_result(self, violations: list[str], warnings: list[str]) -> BrainResult:
        if violations:
            high_keywords = ["core module deletion", "architecture violation", "context references module"]
            is_high = any(
                any(kw in v.lower() for kw in high_keywords)
                for v in violations
            )
            risk       = RiskLevel.HIGH if is_high else RiskLevel.MEDIUM
            confidence = 0.95 if is_high else 0.80
            return BrainResult(
                status=BrainStatus.REJECTED,
                confidence=confidence,
                risk_level=risk,
                explanation=f"{len(violations)} violation(s) detected. Review required.",
                violations=violations,
                warnings=warnings,
            )
        if warnings:
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.75,
                risk_level=RiskLevel.LOW,
                explanation=f"{len(warnings)} advisory warning(s). Change appears safe but review suggested.",
                warnings=warnings,
            )
        return BrainResult(
            status=BrainStatus.VALID,
            confidence=0.97,
            risk_level=RiskLevel.LOW,
            explanation="No violations detected. Change is consistent with architecture and context.",
        )

```

### File: `clockwork/brain/ollama_brain.py`

```python
﻿"""
clockwork/brain/ollama_brain.py

OllamaBrain — reasoning engine that delegates to a locally-running Ollama LLM.

Pipeline:
  Repository Diff -> Prompt Generation -> Ollama REST API -> BrainResult

Requires Ollama: https://ollama.ai
Default model  : deepseek-coder (configurable via .clockwork/config.yaml)
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_OLLAMA_API_URL          = "http://localhost:11434/api/generate"
_DEFAULT_MODEL           = "deepseek-coder"
_REQUEST_TIMEOUT_SECONDS = 30

_SYSTEM_PROMPT = """\
You are Clockwork Brain, a repository intelligence engine.
Respond ONLY with a valid JSON object — no prose, no markdown.

JSON schema:
{
  "status": "VALID" | "WARNING" | "REJECTED",
  "confidence": <float 0.0-1.0>,
  "risk_level": "low" | "medium" | "high",
  "explanation": "<one paragraph>",
  "violations": ["<violation>", ...],
  "warnings": ["<warning>", ...]
}
"""


class OllamaBrain(BrainInterface):
    """Reasoning engine powered by a locally-running Ollama model."""

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self.model = model

    @staticmethod
    def is_available() -> bool:
        """Return True if Ollama is installed and responding."""
        try:
            result = subprocess.run(
                ["ollama", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        prompt = self._build_prompt(context, repo_diff, rules)
        try:
            raw = self._call_ollama(prompt)
            return self._parse_response(raw)
        except Exception as exc:  # noqa: BLE001
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.20,
                risk_level=RiskLevel.MEDIUM,
                explanation=f"OllamaBrain failed: {exc}. Manual review recommended.",
                warnings=[f"Ollama error: {exc}"],
            )

    def _build_prompt(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> str:
        return (
            f"PROJECT CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
            f"REPOSITORY DIFF:\n{json.dumps({k: repo_diff.get(k, []) for k in ('added','deleted','modified')}, indent=2)}\n\n"
            f"ACTIVE RULES:\n{json.dumps([{'id': r.get('id'), 'description': r.get('description')} for r in rules], indent=2)}\n\n"
            "Analyse this repository modification. Respond ONLY with the required JSON."
        )

    def _call_ollama(self, prompt: str) -> str:
        payload = json.dumps(
            {"model": self.model, "prompt": prompt, "system": _SYSTEM_PROMPT, "stream": False}
        ).encode("utf-8")
        req = urllib.request.Request(
            _OLLAMA_API_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "")

    def _parse_response(self, raw: str) -> BrainResult:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            data: dict[str, Any] = json.loads(cleaned)
        except json.JSONDecodeError:
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.30,
                risk_level=RiskLevel.MEDIUM,
                explanation="OllamaBrain returned non-JSON. Manual review required.",
                warnings=["Could not parse Ollama response as JSON."],
            )
        try:
            status = BrainStatus(data.get("status", "WARNING").upper())
        except ValueError:
            status = BrainStatus.WARNING
        try:
            risk = RiskLevel(data.get("risk_level", "medium").lower())
        except ValueError:
            risk = RiskLevel.MEDIUM
        return BrainResult(
            status=status,
            confidence=float(data.get("confidence", 0.5)),
            risk_level=risk,
            explanation=data.get("explanation", "No explanation provided."),
            violations=data.get("violations", []),
            warnings=data.get("warnings", []),
        )

```

### File: `clockwork/cli/__init__.py`

```python
"""
Clockwork CLI
-------------
Primary interaction layer between developers and the Clockwork system.
Built with Typer.  Entry point: clockwork.cli.app
"""

from clockwork.cli.app import app

__all__ = ["app"]

```

### File: `clockwork/cli/app.py`

```python
﻿"""
clockwork/cli/app.py
"""
from __future__ import annotations
import typer
from clockwork.cli.commands.init import cmd_init
from clockwork.cli.commands.scan import cmd_scan
from clockwork.cli.commands.update import cmd_update
from clockwork.cli.commands.verify import cmd_verify
from clockwork.cli.commands.handoff import cmd_handoff
from clockwork.cli.commands.index import cmd_index, cmd_repair, cmd_watch
from clockwork.cli.commands.graph import graph_app
from clockwork.cli.commands.agent import agent_app, task_app
from clockwork.cli.commands.security import security_app
from clockwork.cli.commands.registry import registry_app, plugin_app
from clockwork.packaging.cli_commands import cmd_pack, cmd_load

app = typer.Typer(
    name="clockwork",
    help="Clockwork - local-first repository intelligence and agent coordination.",
    add_completion=False,
    no_args_is_help=True,
)

app.command("init",    help="Initialise Clockwork in a repository.")(cmd_init)
app.command("scan",    help="Analyse repository structure.")(cmd_scan)
app.command("update",  help="Merge scan results into context.yaml.")(cmd_update)
app.command("verify",  help="Verify repository integrity.")(cmd_verify)
app.command("handoff", help="Generate agent handoff data.")(cmd_handoff)
app.command("pack",    help="Package project intelligence.")(cmd_pack)
app.command("load",    help="Load a .clockwork package.")(cmd_load)
app.command("index",   help="Build/refresh the Live Context Index.")(cmd_index)
app.command("repair",  help="Wipe and rebuild the index + graph.")(cmd_repair)
app.command("watch",   help="Start real-time repository monitoring.")(cmd_watch)
app.add_typer(graph_app,    name="graph")
app.add_typer(agent_app,    name="agent")
app.add_typer(task_app,     name="task")
app.add_typer(security_app, name="security")
app.add_typer(registry_app, name="registry")
app.add_typer(plugin_app,   name="plugin")

def main() -> None:
    app()

if __name__ == "__main__":
    main()


```

### File: `clockwork/cli/main.py`

```python
"""Clockwork CLI � main entry point."""
import typer
from clockwork.cli import cmd_init, cmd_scan, cmd_verify, cmd_update
from clockwork.cli import cmd_handoff, cmd_pack, cmd_load, cmd_graph
from clockwork.cli.cmd_plugin import plugin_app

app = typer.Typer(name="clockwork", help="Local-first repository intelligence system.", no_args_is_help=True)
app.command("init")(cmd_init.run)
app.command("scan")(cmd_scan.run)
app.command("verify")(cmd_verify.run)
app.command("update")(cmd_update.run)
app.add_typer(cmd_handoff.app, name="handoff")
app.command("pack")(cmd_pack.run)
app.command("load")(cmd_load.run)
app.command("graph")(cmd_graph.run)
app.add_typer(plugin_app, name="plugin")

if __name__ == "__main__":
    app()

```

### File: `clockwork/cli/output.py`

```python
"""
clockwork/cli/output.py
------------------------
Shared output helpers for consistent, human-readable CLI printing.

All commands must use these helpers rather than bare print() calls so
output style stays uniform and --json mode is easy to add later.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import typer


# ── ANSI colour codes (disabled on non-TTY automatically) ──────────────────

def _supports_color() -> bool:
    return sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _supports_color():
        return f"\033[{code}m{text}\033[0m"
    return text


def green(text: str) -> str:  return _c("32", text)
def yellow(text: str) -> str: return _c("33", text)
def red(text: str) -> str:    return _c("31", text)
def cyan(text: str) -> str:   return _c("36", text)
def bold(text: str) -> str:   return _c("1",  text)
def dim(text: str) -> str:    return _c("2",  text)


# ── Standard output helpers ────────────────────────────────────────────────

def header(title: str) -> None:
    """Print a section header line."""
    typer.echo(bold(f"\n{title}"))
    typer.echo(dim("─" * len(title)))


def success(message: str) -> None:
    typer.echo(green(f"  ✓ {message}"))


def info(message: str) -> None:
    typer.echo(f"  {message}")


def warn(message: str) -> None:
    typer.echo(yellow(f"  ⚠  {message}"))


def error(message: str) -> None:
    typer.echo(red(f"\nError: {message}"), err=True)


def step(label: str, detail: str = "") -> None:
    """Print a pipeline step line."""
    line = f"  → {label}"
    if detail:
        line += f"  {dim(detail)}"
    typer.echo(line)


def json_output(data: Any) -> None:
    """Dump *data* as pretty-printed JSON to stdout."""
    typer.echo(json.dumps(data, indent=2, default=str))


def result_block(title: str, items: list[str]) -> None:
    """Print a labelled list of items."""
    typer.echo(bold(f"\n{title}:"))
    for item in items:
        typer.echo(f"    {item}")


def rule() -> None:
    typer.echo(dim("─" * 48))

```

### File: `clockwork/cli/commands/__init__.py`

```python
"""
clockwork/cli/commands/__init__.py
------------------------------------
CLI command handlers — one module per command.
"""

```

### File: `clockwork/cli/commands/agent.py`

```python
﻿"""
clockwork/cli/commands/agent.py
---------------------------------
CLI commands for the Agent Runtime subsystem.

Spec §12 commands:
    clockwork agent list
    clockwork agent register
    clockwork agent remove
    clockwork agent status

    clockwork task add <description>
    clockwork task list
    clockwork task run <task_id>
    clockwork task fail <task_id>
    clockwork task retry <task_id>
    clockwork task locks
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── Typer sub-apps ─────────────────────────────────────────────────────────

agent_app = typer.Typer(
    name="agent",
    help="Manage registered AI agents.",
    no_args_is_help=True,
)

task_app = typer.Typer(
    name="task",
    help="Manage the agent task queue.",
    no_args_is_help=True,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _runtime(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw   = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.agent import AgentRuntime
    rt = AgentRuntime(root)
    rt.initialise()
    return rt


# ══════════════════════════════════════════════════════════════════════════
# clockwork agent …
# ══════════════════════════════════════════════════════════════════════════

@agent_app.command("list")
def agent_list(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """List all registered agents."""
    rt     = _runtime(repo_root)
    agents = rt.list_agents()

    if as_json:
        json_output([a.to_dict() for a in agents])
        return

    header("Registered Agents")
    if not agents:
        warn("No agents registered. Run:  clockwork agent register <name>")
        return

    for a in sorted(agents, key=lambda x: x.priority):
        caps = ", ".join(a.capabilities) or "(none)"
        info(f"  {a.name:<20} priority={a.priority}  caps=[{caps}]")
        if a.description:
            info(f"    {a.description}")


@agent_app.command("register")
def agent_register(
    name:         str            = typer.Argument(..., help="Unique agent name."),
    capabilities: Optional[str] = typer.Option(
        None, "--caps", "-c",
        help="Comma-separated capabilities (e.g. coding,testing).",
    ),
    priority:     int            = typer.Option(10, "--priority", "-p"),
    description:  str            = typer.Option("", "--desc", "-d"),
    repo_root:    Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Register a new agent."""
    from clockwork.agent.models import Agent

    caps = [c.strip() for c in (capabilities or "coding").split(",") if c.strip()]
    agent = Agent(name=name, capabilities=caps, priority=priority, description=description)

    rt = _runtime(repo_root)
    if rt.register_agent(agent):
        success(f"Agent '{name}' registered.")
        info(f"  Capabilities : {', '.join(caps)}")
        info(f"  Priority     : {priority}")
    else:
        warn(f"Agent '{name}' already exists.")


@agent_app.command("remove")
def agent_remove(
    name:      str            = typer.Argument(..., help="Agent name to remove."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Remove a registered agent."""
    rt = _runtime(repo_root)
    if rt.remove_agent(name):
        success(f"Agent '{name}' removed.")
    else:
        warn(f"Agent '{name}' not found.")


@agent_app.command("status")
def agent_status(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show agent runtime statistics."""
    rt    = _runtime(repo_root)
    stats = rt.stats()

    if as_json:
        json_output(stats)
        return

    header("Agent Runtime Status")
    info(f"  Registered agents : {stats['agents']}")
    info(f"  Total tasks       : {stats['total_tasks']}")
    info(f"  Active locks      : {stats['active_locks']}")
    info(f"  Log entries       : {stats['log_entries']}")
    rule()
    info("Tasks by status:")
    for status, count in sorted(stats["tasks_by_status"].items()):
        info(f"  {status:<12} : {count}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork task …
# ══════════════════════════════════════════════════════════════════════════

@task_app.command("add")
def task_add(
    description: str            = typer.Argument(..., help="Task description."),
    capability:  str            = typer.Option("coding", "--cap", "-c",
                                    help="Required capability."),
    repo_root:   Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:     bool           = typer.Option(False, "--json"),
) -> None:
    """Add a new task to the queue."""
    rt   = _runtime(repo_root)
    task = rt.add_task(description, capability)

    if as_json:
        json_output(task.to_dict())
        return

    success(f"Task added: {task.task_id}")
    info(f"  Description  : {task.description}")
    info(f"  Capability   : {task.required_capability}")
    info(f"  Status       : {task.status}")
    if task.assigned_agent:
        info(f"  Assigned to  : {task.assigned_agent}")
    else:
        warn("  No agent available — register one with: clockwork agent register")


@task_app.command("list")
def task_list(
    status:    Optional[str]  = typer.Option(None, "--status", "-s",
                                    help="Filter by status (pending/assigned/completed/failed)."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """List tasks in the queue."""
    rt    = _runtime(repo_root)
    tasks = rt.list_tasks(status)

    if as_json:
        json_output([t.to_dict() for t in tasks])
        return

    header("Task Queue" + (f" [{status}]" if status else ""))
    if not tasks:
        info("No tasks found.")
        return

    for t in tasks:
        agent = f" → {t.assigned_agent}" if t.assigned_agent else ""
        info(f"  [{t.status:<10}] {t.task_id}  {t.description[:50]}{agent}")
        if t.validation_errors:
            for e in t.validation_errors:
                warn(f"    ! {e}")


@task_app.command("run")
def task_run(
    task_id:   str            = typer.Argument(..., help="Task ID to run."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Run the validation pipeline for a task."""
    rt     = _runtime(repo_root)
    step(f"Running validation pipeline for {task_id}...")
    result = rt.run_task(task_id)

    if as_json:
        json_output(result.to_dict())
        return

    rule()
    if result.passed:
        success("Validation passed — changes approved.")
    else:
        error("Validation failed — changes rejected.")
        for e in result.errors:
            info(f"  ✗ {e}")

    if result.warnings:
        for w in result.warnings:
            warn(f"  ! {w}")


@task_app.command("fail")
def task_fail(
    task_id:   str            = typer.Argument(..., help="Task ID to mark failed."),
    reason:    str            = typer.Option("", "--reason", "-r"),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Mark a task as failed."""
    rt = _runtime(repo_root)
    if rt.fail_task(task_id, reason):
        warn(f"Task {task_id} marked as failed.")
    else:
        error(f"Task '{task_id}' not found.")


@task_app.command("retry")
def task_retry(
    task_id:   str            = typer.Argument(..., help="Task ID to retry."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Retry a failed task with a different agent."""
    rt       = _runtime(repo_root)
    assigned = rt.retry_task(task_id)
    if assigned:
        success(f"Task {task_id} retried — assigned to '{assigned}'.")
    else:
        warn(f"Could not retry task '{task_id}' (not found or not in failed state).")


@task_app.command("locks")
def task_locks(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """List all active file locks."""
    rt    = _runtime(repo_root)
    locks = rt.lock_manager.list_locks()

    if as_json:
        json_output(locks)
        return

    header("Active File Locks")
    if not locks:
        info("No active locks.")
        return
    for lk in locks:
        info(f"  {lk.get('file_path'):<40} locked by {lk.get('agent')}")


```

### File: `clockwork/cli/commands/graph.py`

```python
﻿"""
clockwork/cli/commands/graph.py
---------------------------------
`clockwork graph` — generate the repository knowledge graph.

Writes a full SQLite knowledge graph to .clockwork/knowledge_graph.db.

Commands exposed:
    clockwork graph          — build the full graph
    clockwork graph query    — run a query against an existing graph
    clockwork graph stats    — show node / edge counts
    clockwork graph export   — dump graph to JSON
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── Typer sub-app ──────────────────────────────────────────────────────────

graph_app = typer.Typer(
    name="graph",
    help="Build and query the repository knowledge graph.",
    no_args_is_help=False,
    invoke_without_command=True,
)


# ── Default command: build ─────────────────────────────────────────────────

@graph_app.callback(invoke_without_command=True)
def cmd_graph(
    ctx: typer.Context,
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Generate a repository knowledge graph from the current repo_map.

    Output: .clockwork/knowledge_graph.db  (SQLite)
    """
    if ctx.invoked_subcommand is not None:
        return

    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Graph")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    repo_map_path = cw_dir / "repo_map.json"
    if not repo_map_path.exists():
        error("repo_map.json not found.\nRun:  clockwork scan")
        raise typer.Exit(code=1)

    try:
        repo_map: dict = json.loads(repo_map_path.read_text(encoding="utf-8"))
    except Exception as exc:
        error(f"Cannot read repo_map.json: {exc}")
        raise typer.Exit(code=1)

    db_path = cw_dir / "knowledge_graph.db"

    if not as_json:
        step("Building knowledge graph...")

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        stats  = engine.build(repo_map)
        engine.close()
    except Exception as exc:
        error(f"Graph build failed: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats.to_dict())
        return

    rule()
    success(f"Knowledge graph written to .clockwork/knowledge_graph.db")
    info(f"  Nodes (total)  : {stats.node_count}")
    info(f"  Edges (total)  : {stats.edge_count}")
    info(f"  Files          : {stats.file_count}")
    info(f"  Layers         : {stats.layer_count}")
    info(f"  Services       : {stats.service_count}")
    info(f"  Languages      : {stats.language_count}")
    info(f"  Elapsed        : {stats.elapsed_ms:.0f} ms")
    info("\nNext step: run  clockwork graph stats")


# ── Sub-command: stats ─────────────────────────────────────────────────────

@graph_app.command("stats")
def cmd_graph_stats(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Show node and edge statistics for the knowledge graph."""
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        stats_dict = engine.query().stats()
        engine.close()
    except Exception as exc:
        error(f"Cannot read graph: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats_dict)
        return

    header("Clockwork Graph Stats")
    info(f"  Total nodes : {stats_dict['total_nodes']}")
    info(f"  Total edges : {stats_dict['total_edges']}")
    rule()
    info("Nodes by kind:")
    for kind, cnt in sorted(stats_dict["nodes_by_kind"].items()):
        info(f"  {kind:<14}: {cnt}")
    rule()
    info("Files by layer:")
    for layer, cnt in sorted(stats_dict["layers"].items()):
        info(f"  {layer:<14}: {cnt}")
    rule()
    info("Files by language:")
    for lang, cnt in sorted(stats_dict["languages"].items(), key=lambda x: -x[1]):
        info(f"  {lang:<14}: {cnt}")


# ── Sub-command: query ─────────────────────────────────────────────────────

@graph_app.command("query")
def cmd_graph_query(
    question: str = typer.Argument(..., help=(
        "Query to run. Examples:\n"
        "  depends-on <file_path>\n"
        "  dependencies-of <file_path>\n"
        "  layer <layer_name>\n"
        "  imports <module_name>\n"
        "  safe-to-delete <file_path>"
    )),
    target: str = typer.Argument("", help="Target file/module/layer for the query."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Query the knowledge graph."""
    root    = (repo_root or Path.cwd()).resolve()
    cw_dir  = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    try:
        from clockwork.graph import GraphEngine
        engine = GraphEngine(root)
        q      = engine.query()
    except Exception as exc:
        error(f"Cannot open graph: {exc}")
        raise typer.Exit(code=1)

    try:
        result: object = None
        cmd = question.lower().replace("-", "_")

        if cmd == "depends_on" and target:
            nodes = q.who_depends_on(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files that depend on: {target}")
                _print_nodes(nodes)

        elif cmd == "dependencies_of" and target:
            nodes = q.dependencies_of(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Dependencies of: {target}")
                _print_nodes(nodes)

        elif cmd == "layer" and target:
            nodes = q.files_in_layer(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files in layer: {target}")
                _print_nodes(nodes)

        elif cmd == "imports" and target:
            nodes = q.files_importing(target)
            result = [n.to_dict() for n in nodes]
            if not as_json:
                header(f"Files importing: {target}")
                _print_nodes(nodes)

        elif cmd == "safe_to_delete" and target:
            safe, reasons = q.is_safe_to_delete(target)
            result = {"safe": safe, "reasons": reasons}
            if not as_json:
                header(f"Safe to delete: {target}")
                if safe:
                    success("Yes — no other files depend on this file.")
                else:
                    warn(f"No — {len(reasons)} file(s) depend on it:")
                    for r in reasons:
                        info(f"  • {r}")

        else:
            error(f"Unknown query '{question}'. Run 'clockwork graph query --help'.")
            raise typer.Exit(code=1)

        if as_json and result is not None:
            json_output(result)

    finally:
        engine.close()


# ── Sub-command: export ────────────────────────────────────────────────────

@graph_app.command("export")
def cmd_graph_export(
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output JSON file path (default: .clockwork/graph_export.json).",
    ),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Export the knowledge graph to JSON."""
    root    = (repo_root or Path.cwd()).resolve()
    cw_dir  = root / ".clockwork"
    db_path = cw_dir / "knowledge_graph.db"

    if not db_path.exists():
        error("knowledge_graph.db not found.\nRun:  clockwork graph")
        raise typer.Exit(code=1)

    out_path = output or (cw_dir / "graph_export.json")

    try:
        from clockwork.graph import GraphEngine
        engine     = GraphEngine(root)
        graph_data = engine.query().export()
        engine.close()
    except Exception as exc:
        error(f"Export failed: {exc}")
        raise typer.Exit(code=1)

    out_path.write_text(json.dumps(graph_data, indent=2), encoding="utf-8")
    success(f"Graph exported to {out_path}")
    info(f"  Nodes : {len(graph_data['nodes'])}")
    info(f"  Edges : {len(graph_data['edges'])}")


# ── helpers ────────────────────────────────────────────────────────────────

def _print_nodes(nodes: list) -> None:
    if not nodes:
        warn("No results found.")
        return
    for n in nodes:
        layer = f" [{n.layer}]" if n.layer else ""
        lang  = f" ({n.language})" if n.language else ""
        info(f"  • {n.file_path or n.label}{lang}{layer}")


# ── legacy standalone function (keeps test_cli.py working) ────────────────

def _build_graph(repo_map: dict, db_path: Path) -> tuple[int, int]:
    """
    Thin wrapper kept for backward-compatibility with test_cli.py.
    Builds the graph and returns (node_count, edge_count).
    """
    from clockwork.graph.storage import GraphStorage
    from clockwork.graph.builder import GraphBuilder

    storage = GraphStorage(db_path)
    storage.open()
    storage.initialise(drop_existing=True)
    builder = GraphBuilder(storage)
    stats   = builder.build(repo_map)
    storage.close()
    return stats.node_count, stats.edge_count


```

### File: `clockwork/cli/commands/handoff.py`

```python
"""
clockwork/cli/commands/handoff.py
-----------------------------------
`clockwork handoff` — generate agent handoff data.

Produces:
  .clockwork/handoff/handoff.json
  .clockwork/handoff/next_agent_brief.md
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import header, success, info, error, step, rule


def cmd_handoff(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    note: Optional[str] = typer.Option(
        None, "--note", "-n",
        help="Optional human note to include in the handoff brief.",
    ),
) -> None:
    """
    Generate agent handoff data from current project context.

    Writes handoff.json and next_agent_brief.md into .clockwork/handoff/.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Handoff")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        error("context.yaml not found.\nRun:  clockwork init && clockwork scan && clockwork update")
        raise typer.Exit(code=1)

    try:
        context: dict = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        error(f"Cannot read context.yaml: {exc}")
        raise typer.Exit(code=1)

    handoff_dir = cw_dir / "handoff"
    handoff_dir.mkdir(exist_ok=True)

    step("Building handoff payload...")
    handoff = _build_handoff(context, note=note)

    step("Writing handoff.json...")
    handoff_json_path = handoff_dir / "handoff.json"
    handoff_json_path.write_text(
        json.dumps(handoff, indent=2, default=str),
        encoding="utf-8",
    )

    step("Writing next_agent_brief.md...")
    brief_path = handoff_dir / "next_agent_brief.md"
    brief_path.write_text(_build_brief(handoff), encoding="utf-8")

    # Record in agent history
    _append_agent_history(cw_dir, handoff)

    rule()
    success("Handoff data generated")
    info(f"  JSON  : .clockwork/handoff/handoff.json")
    info(f"  Brief : .clockwork/handoff/next_agent_brief.md")


def _build_handoff(context: dict, note: Optional[str]) -> dict:
    """Construct the handoff payload from project context."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_name": context.get("project_name", "unknown"),
        "clockwork_version": context.get("clockwork_version", "0.1"),
        "architecture_summary": context.get("architecture_overview", ""),
        "primary_language": context.get("primary_language", ""),
        "frameworks": context.get("frameworks", []),
        "entry_points": context.get("entry_points", []),
        "current_tasks": context.get("current_tasks", []),
        "recent_changes": context.get("recent_changes", []),
        "total_files": context.get("total_files", 0),
        "languages": context.get("languages", {}),
        "handoff_note": note or "",
        "next_steps": context.get("current_tasks", []),
    }


def _build_brief(handoff: dict) -> str:
    """Render a Markdown handoff brief for the next agent."""
    tasks = handoff.get("current_tasks") or ["(none recorded)"]
    frameworks = handoff.get("frameworks") or ["(none detected)"]
    entry_points = handoff.get("entry_points") or ["(none detected)"]

    task_list = "\n".join(f"- {t}" for t in tasks)
    fw_list = "\n".join(f"- {f}" for f in frameworks)
    ep_list = "\n".join(f"- {e}" for e in entry_points)
    note_section = (
        f"\n## Handoff Note\n\n{handoff['handoff_note']}\n"
        if handoff.get("handoff_note")
        else ""
    )

    return f"""# Clockwork Agent Handoff Brief

**Project:** {handoff['project_name']}
**Generated:** {handoff['generated_at']}
**Clockwork Version:** {handoff['clockwork_version']}

---

## Architecture Summary

{handoff.get('architecture_summary') or '(not yet recorded — update context.yaml)'}

---

## Technical Stack

**Primary Language:** {handoff['primary_language'] or '(unknown)'}

**Frameworks:**
{fw_list}

**Entry Points:**
{ep_list}

---

## Current Tasks

{task_list}

---

## Recent Changes

{chr(10).join(f'- {c}' for c in handoff.get('recent_changes') or ['(none recorded)'])}

---
{note_section}
## Instructions for Next Agent

1. Read `.clockwork/context.yaml` for full project context.
2. Read `.clockwork/rules.md` before making any changes.
3. Run `clockwork verify` before committing.
4. Run `clockwork update` after significant changes.
5. Run `clockwork handoff` when passing work to another agent.
"""


def _append_agent_history(cw_dir: Path, handoff: dict) -> None:
    """Append a summary entry to agent_history.json."""
    history_path = cw_dir / "agent_history.json"
    try:
        history: list = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = []

    history.append({
        "event": "handoff_generated",
        "timestamp": handoff["generated_at"],
        "project": handoff["project_name"],
        "tasks": handoff["current_tasks"],
    })

    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

```

### File: `clockwork/cli/commands/index.py`

```python
﻿"""
clockwork/cli/commands/index.py
---------------------------------
CLI commands for the Live Context Index subsystem.

Commands:
    clockwork watch   — start real-time filesystem monitoring
    clockwork index   — build / refresh the index
    clockwork repair  — wipe and rebuild the index from scratch
"""

from __future__ import annotations

import signal
import sys
import time
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── clockwork index ────────────────────────────────────────────────────────

def cmd_index(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """
    Build or refresh the Live Context Index.

    Scans the repository and writes metadata to .clockwork/index.db.
    Skips files whose content has not changed.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Index")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    if not as_json:
        step("Building Live Context Index...")

    try:
        from clockwork.index import LiveContextIndex
        engine = LiveContextIndex(root)
        stats  = engine.build()
    except Exception as exc:
        error(f"Index build failed: {exc}")
        raise typer.Exit(code=1)

    if as_json:
        json_output(stats.to_dict())
        return

    rule()
    success("Live Context Index written to .clockwork/index.db")
    info(f"  Total files   : {stats.total_files}")
    info(f"  Indexed       : {stats.indexed_files}")
    info(f"  Skipped (unchanged) : {stats.skipped_files}")
    info(f"  Elapsed       : {stats.elapsed_ms:.0f} ms")
    info("\nNext step: run  clockwork watch")


# ── clockwork repair ───────────────────────────────────────────────────────

def cmd_repair(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """
    Wipe and rebuild the Live Context Index from scratch.

    Use this if the index becomes corrupted or out of sync.
    Also rebuilds the Knowledge Graph.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Repair")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    if not as_json:
        step("Wiping index.db and rebuilding...")

    try:
        from clockwork.index import LiveContextIndex
        engine = LiveContextIndex(root)
        stats  = engine.repair()
    except Exception as exc:
        error(f"Repair failed: {exc}")
        raise typer.Exit(code=1)

    # also rebuild the knowledge graph if repo_map exists
    graph_rebuilt = False
    if (cw_dir / "repo_map.json").exists():
        if not as_json:
            step("Rebuilding Knowledge Graph...")
        try:
            from clockwork.graph import GraphEngine
            ge = GraphEngine(root)
            ge.build()
            ge.close()
            graph_rebuilt = True
        except Exception as exc:
            warn(f"Graph rebuild skipped: {exc}")

    if as_json:
        result = stats.to_dict()
        result["graph_rebuilt"] = graph_rebuilt
        json_output(result)
        return

    rule()
    success("Repair complete.")
    info(f"  Files indexed  : {stats.indexed_files}")
    info(f"  Elapsed        : {stats.elapsed_ms:.0f} ms")
    if graph_rebuilt:
        info("  Knowledge Graph: rebuilt")
    else:
        info("  Knowledge Graph: skipped (run clockwork graph)")


# ── clockwork watch ────────────────────────────────────────────────────────

def cmd_watch(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Repository root (defaults to current directory).",
    ),
    debounce: float = typer.Option(
        0.2, "--debounce", "-d",
        help="Debounce window in seconds (default: 0.2).",
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v",
        help="Print each file change event.",
    ),
) -> None:
    """
    Start real-time repository monitoring.

    Watches for file changes and updates the Live Context Index,
    Knowledge Graph, and Context Engine automatically.

    Press Ctrl+C to stop.
    """
    root   = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Watch")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    # ensure index.db exists before watching
    if not (cw_dir / "index.db").exists():
        step("Building initial index...")
        try:
            from clockwork.index import LiveContextIndex
            engine = LiveContextIndex(root)
            stats  = engine.build()
            info(f"  Initial index: {stats.indexed_files} files in {stats.elapsed_ms:.0f} ms")
        except Exception as exc:
            warn(f"Initial index build failed: {exc}")

    try:
        from clockwork.index import LiveContextIndex
        from clockwork.index.models import ChangeEvent

        change_count = [0]

        def on_change(event: ChangeEvent) -> None:
            change_count[0] += 1
            if verbose:
                info(f"  [{event.event_type}] {event.file_path}")

        engine = LiveContextIndex(root)
        has_watchdog = engine.watch(debounce_s=debounce)

        if has_watchdog:
            success(f"Watching {root}")
            info(f"  Debounce     : {debounce * 1000:.0f} ms")
            info("  Press Ctrl+C to stop.\n")
        else:
            warn("watchdog not installed — real-time watching unavailable.")
            info("Install it with:  pip install watchdog")
            info("Then re-run:      clockwork watch")
            engine.stop()
            raise typer.Exit(code=1)

        # handle Ctrl+C gracefully
        def _shutdown(*_: object) -> None:
            info(f"\nStopping... ({change_count[0]} changes processed)")
            engine.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _shutdown)

        # keep alive
        while True:
            time.sleep(1)

    except ImportError as exc:
        error(f"Import error: {exc}")
        raise typer.Exit(code=1)


```

### File: `clockwork/cli/commands/init.py`

```python
"""
clockwork/cli/commands/init.py
--------------------------------
`clockwork init` — initialise Clockwork inside a repository.

Responsibilities (spec §4):
  • create .clockwork/ directory
  • write context.yaml   (project context template)
  • write rules.md       (rule definitions template)
  • write config.yaml    (runtime configuration)
  • write tasks.json     (empty task list)
  • write skills.json    (empty skill registry)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule
)

# ── Default file contents ──────────────────────────────────────────────────

_CONTEXT_YAML = """\
# Clockwork Project Context
# -------------------------
# Maintained by: clockwork update
# Do not edit manually unless you know what you are doing.

clockwork_version: "0.1"
memory_schema_version: 1
project_name: "{project_name}"
created_at: "{created_at}"

summary: ""
architecture_overview: ""
primary_language: ""
frameworks: []
entry_points: []

current_tasks: []
recent_changes: []
"""

_RULES_MD = """\
# Clockwork Rule Definitions
# ---------------------------
# Add project-specific rules below.
# Rules are evaluated by the Rule Engine during `clockwork verify`.

## Architecture Rules

- Do not bypass the API layer.
- Do not modify database schema without a migration script.
- Do not remove core modules without explicit approval.

## File Protection Rules

- .clockwork/ must not be deleted.
- pyproject.toml must not be modified by automated agents without review.

## Naming Rules

- Python modules must use snake_case.
- Classes must use PascalCase.
"""

_CONFIG_YAML = """\
# Clockwork Runtime Configuration
# ---------------------------------

brain:
  mode: minibrain

scanner:
  ignore_dirs:
    - .git
    - __pycache__
    - node_modules
    - .venv
    - dist
    - build
  ignore_extensions:
    - .pyc
    - .pyo

packaging:
  auto_snapshot: false

logging:
  level: info
"""

_TASKS_JSON = json.dumps([], indent=2)
_SKILLS_JSON = json.dumps([], indent=2)
_AGENT_HISTORY_JSON = json.dumps([], indent=2)


# ── Command ────────────────────────────────────────────────────────────────

def cmd_init(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Re-initialise even if .clockwork/ already exists.",
    ),
) -> None:
    """
    Initialise Clockwork inside a repository.

    Creates the .clockwork/ directory and all required template files.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Init")

    if cw_dir.exists() and not force:
        warn("Clockwork is already initialised in this repository.")
        info("Use --force to re-initialise.")
        raise typer.Exit(code=0)

    try:
        _create_clockwork_dir(cw_dir, project_name=root.name)
    except OSError as exc:
        error(str(exc))
        raise typer.Exit(code=1)

    rule()
    success(f"Clockwork initialised in {root}")
    info(f"Directory: {cw_dir}")
    info("Next step: run  clockwork scan")


def _create_clockwork_dir(cw_dir: Path, project_name: str) -> None:
    """Create .clockwork/ and write all template files."""
    created_at = datetime.now(timezone.utc).isoformat()

    files: dict[str, str] = {
        "context.yaml": _CONTEXT_YAML.format(
            project_name=project_name,
            created_at=created_at,
        ),
        "rules.md": _RULES_MD,
        "config.yaml": _CONFIG_YAML,
        "tasks.json": _TASKS_JSON,
        "skills.json": _SKILLS_JSON,
        "agent_history.json": _AGENT_HISTORY_JSON,
    }

    # Sub-directories
    for sub in ("handoff", "packages", "plugins", "logs"):
        (cw_dir / sub).mkdir(parents=True, exist_ok=True)
        step(f"Created  .clockwork/{sub}/")

    for filename, content in files.items():
        dest = cw_dir / filename
        dest.write_text(content, encoding="utf-8")
        step(f"Created  .clockwork/{filename}")

```

### File: `clockwork/cli/commands/registry.py`

```python
﻿"""
clockwork/cli/commands/registry.py
------------------------------------
CLI commands for the Registry & Ecosystem subsystem (spec §14).

Commands:
    clockwork registry search [query]
    clockwork registry info <name>
    clockwork registry refresh
    clockwork registry status

    clockwork plugin install <name>
    clockwork plugin list
    clockwork plugin update <name>
    clockwork plugin remove <name>
    clockwork plugin publish <path>
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

# ── Typer sub-apps ─────────────────────────────────────────────────────────

registry_app = typer.Typer(
    name="registry",
    help="Search and manage the Clockwork plugin registry.",
    no_args_is_help=True,
)

plugin_app = typer.Typer(
    name="plugin",
    help="Install, update, and manage plugins.",
    no_args_is_help=True,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _engine(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw   = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.registry import RegistryEngine
    return RegistryEngine(root)


def _print_entry(e) -> None:
    trusted = " [trusted]" if e.trusted else ""
    info(f"  {e.name:<28} v{e.version:<8} {e.artifact_type}{trusted}")
    if e.description:
        info(f"    {e.description}")
    if e.tags:
        info(f"    tags: {', '.join(e.tags)}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork registry …
# ══════════════════════════════════════════════════════════════════════════

@registry_app.command("search")
def registry_search(
    query:         str            = typer.Argument("", help="Search term (empty = list all)."),
    artifact_type: str            = typer.Option("", "--type", "-t",
                                       help="Filter by type: plugin, brain, package."),
    repo_root:     Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:       bool           = typer.Option(False, "--json"),
) -> None:
    """Search the registry for plugins, brains, and packages."""
    reg     = _engine(repo_root)
    results = reg.search(query, artifact_type)

    if as_json:
        json_output([e.to_dict() for e in results])
        return

    header(f"Registry Search: '{query}'" if query else "Registry — All Entries")
    if not results:
        warn("No entries found. Try a different search term.")
        return

    info(f"  {len(results)} result(s):\n")
    for e in sorted(results, key=lambda x: (x.artifact_type, x.name)):
        _print_entry(e)
        rule()


@registry_app.command("info")
def registry_info(
    name:      str            = typer.Argument(..., help="Plugin or artifact name."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show detailed info about a registry entry."""
    reg   = _engine(repo_root)
    entry = reg.get(name)

    if entry is None:
        error(f"'{name}' not found in registry.")
        raise typer.Exit(code=1)

    if as_json:
        json_output(entry.to_dict())
        return

    header(f"Registry: {entry.name}")
    info(f"  Name        : {entry.name}")
    info(f"  Version     : {entry.version}")
    info(f"  Type        : {entry.artifact_type}")
    info(f"  Author      : {entry.author or '(unknown)'}")
    info(f"  Description : {entry.description or '(none)'}")
    info(f"  Requires    : clockwork {entry.requires_clockwork}")
    info(f"  Permissions : {', '.join(entry.permissions) or '(none)'}")
    info(f"  Tags        : {', '.join(entry.tags) or '(none)'}")
    info(f"  Trusted     : {'yes' if entry.trusted else 'no'}")
    if entry.checksum:
        info(f"  Checksum    : {entry.checksum[:16]}...")


@registry_app.command("refresh")
def registry_refresh(
    url:       str            = typer.Option("", "--url", "-u",
                                    help="Registry server URL."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Refresh the local registry cache from the remote server."""
    reg  = _engine(repo_root)
    step("Refreshing registry cache...")
    ok, msg = reg.refresh(url)
    if ok:
        success(msg)
    else:
        warn(msg)


@registry_app.command("status")
def registry_status(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show registry cache status."""
    reg  = _engine(repo_root)
    data = reg.cache_info()

    if as_json:
        json_output(data)
        return

    header("Registry Status")
    info(f"  Cached entries   : {data['entries']}")
    info(f"  Installed plugins: {data['installed']}")
    info(f"  Registry URL     : {data['registry_url'] or '(not set)'}")
    stale = "yes — run: clockwork registry refresh" if data["is_stale"] else "no"
    info(f"  Cache stale      : {stale}")


# ══════════════════════════════════════════════════════════════════════════
# clockwork plugin …
# ══════════════════════════════════════════════════════════════════════════

@plugin_app.command("install")
def plugin_install(
    name:      str            = typer.Argument(..., help="Plugin name to install."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Install a plugin from the registry."""
    reg = _engine(repo_root)
    step(f"Installing '{name}'...")
    ok, msg = reg.install(name)
    if ok:
        success(msg)
        info("  Run:  clockwork plugin list  to see installed plugins.")
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("list")
def plugin_list(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """List installed plugins."""
    reg       = _engine(repo_root)
    installed = reg.list_installed()

    if as_json:
        json_output([p.to_dict() for p in installed])
        return

    header("Installed Plugins")
    if not installed:
        info("No plugins installed.")
        info("  Discover plugins:  clockwork registry search")
        info("  Install a plugin:  clockwork plugin install <name>")
        return

    for p in installed:
        status = "enabled" if p.enabled else "disabled"
        info(f"  {p.name:<28} v{p.version:<8} [{status}]")
        info(f"    {p.install_path}")


@plugin_app.command("update")
def plugin_update(
    name:      str            = typer.Argument(..., help="Plugin name to update."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Update an installed plugin to its latest version."""
    reg = _engine(repo_root)
    step(f"Updating '{name}'...")
    ok, msg = reg.update(name)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("remove")
def plugin_remove(
    name:      str            = typer.Argument(..., help="Plugin name to remove."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Remove an installed plugin."""
    reg = _engine(repo_root)
    ok, msg = reg.remove(name)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)


@plugin_app.command("publish")
def plugin_publish(
    plugin_path: Path          = typer.Argument(
                                     Path("."),
                                     help="Path to plugin directory (default: current dir)."),
    repo_root:   Optional[Path] = typer.Option(None, "--repo", "-r"),
) -> None:
    """Publish a plugin to the registry."""
    reg = _engine(repo_root)
    step(f"Publishing '{plugin_path.name}'...")
    ok, msg = reg.publish(plugin_path)
    if ok:
        success(msg)
    else:
        error(msg)
        raise typer.Exit(code=1)


```

### File: `clockwork/cli/commands/scan.py`

```python
﻿"""
clockwork/cli/commands/scan.py
--------------------------------
`clockwork scan` — analyse repository structure and write repo_map.json.

The scanner walks the repository tree, detects languages, counts files,
identifies entry points, and stores results in .clockwork/repo_map.json.

When the full Repository Scanner subsystem (clockwork/scanner/) is
implemented it will be called here.  Until then this module provides a
self-contained implementation that satisfies the spec and produces a
well-structured repo_map.json.
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, result_block, rule, json_output,
)

# ── Language detection by extension ───────────────────────────────────────

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py":    "Python",
    ".js":    "JavaScript",
    ".ts":    "TypeScript",
    ".jsx":   "JavaScript",
    ".tsx":   "TypeScript",
    ".go":    "Go",
    ".rs":    "Rust",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".cs":    "C#",
    ".cpp":   "C++",
    ".c":     "C",
    ".h":     "C/C++ Header",
    ".html":  "HTML",
    ".css":   "CSS",
    ".scss":  "SCSS",
    ".yaml":  "YAML",
    ".yml":   "YAML",
    ".json":  "JSON",
    ".md":    "Markdown",
    ".sh":    "Shell",
    ".bash":  "Shell",
    ".sql":   "SQL",
    ".tf":    "Terraform",
    ".toml":  "TOML",
    ".xml":   "XML",
    ".dart":  "Dart",
    ".swift": "Swift",
}

SENSITIVE_FILES: set[str] = {
    ".env", ".env.local", ".env.production",
    "credentials.json", "secrets.json", "secret.json",
    ".netrc", "id_rsa", "id_ed25519",
}

DEFAULT_IGNORE_DIRS: set[str] = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
    "eggs",
}

# Directories whose names end with this suffix are also ignored
_IGNORE_DIR_SUFFIXES: tuple[str, ...] = (".egg-info",)


# ── Command ────────────────────────────────────────────────────────────────

def cmd_scan(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Analyse repository structure and write .clockwork/repo_map.json.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Scan")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    # Load config for ignore rules (used by fallback scanner)
    ignore_dirs = _load_ignore_dirs(cw_dir)

    start = time.perf_counter()

    if not as_json:
        step("Walking repository tree...")

    # Prefer the full RepositoryScanner subsystem; fall back to inline scanner
    try:
        from clockwork.scanner import RepositoryScanner
        scanner = RepositoryScanner(repo_root=root)
        result = scanner.scan()
        output_path = result.save(cw_dir)
        repo_map = result.to_dict()
    except Exception as _scan_exc:
        if not as_json:
            try:
                warn(f"Full scanner unavailable ({type(_scan_exc).__name__}: {_scan_exc}), falling back to built-in scanner.")
            except UnicodeEncodeError:
                warn(f"Full scanner unavailable ({type(_scan_exc).__name__}), falling back.")
        repo_map = _scan_repository(root, ignore_dirs)
        output_path = cw_dir / "repo_map.json"
        output_path.write_text(
            json.dumps(repo_map, indent=2, default=str),
            encoding="utf-8",
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    if as_json:
        json_output(repo_map)
        return

    # Human-readable summary
    languages = repo_map.get("languages", {})
    total_files = repo_map.get("total_files", 0)

    rule()
    success(f"Scan complete in {elapsed_ms:.0f} ms")
    info(f"Total files scanned : {total_files}")
    info(f"Output              : .clockwork/repo_map.json")

    if languages:
        result_block(
            "Detected languages",
            [f"{lang}  ({count} files)" for lang, count in
             sorted(languages.items(), key=lambda x: -x[1])]
        )

    if repo_map.get("entry_points"):
        result_block("Entry points", repo_map["entry_points"])

    info("\nNext step: run  clockwork update")


# ── Scanner implementation ─────────────────────────────────────────────────

def _load_ignore_dirs(cw_dir: Path) -> set[str]:
    """Load ignore_dirs from config.yaml, falling back to defaults."""
    config_path = cw_dir / "config.yaml"
    try:
        if config_path.exists():
            cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            dirs = cfg.get("scanner", {}).get("ignore_dirs", [])
            return DEFAULT_IGNORE_DIRS | set(dirs)
    except Exception:
        pass
    return DEFAULT_IGNORE_DIRS


def _scan_repository(root: Path, ignore_dirs: set[str]) -> dict:
    """
    Walk *root*, collect file metadata, detect languages, find entry points.
    Returns a repo_map dict ready for JSON serialisation.
    """
    language_counts: dict[str, int] = defaultdict(int)
    all_files: list[dict] = []
    entry_points: list[str] = []
    dir_tree: dict[str, list[str]] = defaultdict(list)

    for path in sorted(root.rglob("*")):
        # Skip ignored directories (exact match or suffix match)
        if any(part in ignore_dirs for part in path.parts):
            continue
        if any(part.endswith(_IGNORE_DIR_SUFFIXES) for part in path.parts):
            continue

        # Skip sensitive filenames
        if path.name.lower() in SENSITIVE_FILES:
            continue

        if not path.is_file():
            continue

        rel = str(path.relative_to(root))
        ext = path.suffix.lower()
        language = EXTENSION_LANGUAGE_MAP.get(ext, "Other")

        if language != "Other":
            language_counts[language] += 1

        try:
            size_bytes = path.stat().st_size
        except OSError:
            size_bytes = 0

        file_entry: dict = {
            "path": rel,
            "extension": ext,
            "language": language,
            "size_bytes": size_bytes,
        }
        all_files.append(file_entry)

        # Track per-directory members
        dir_tree[str(path.parent.relative_to(root))].append(path.name)

        # Detect common entry points
        if _is_entry_point(path, root):
            entry_points.append(rel)

    return {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "total_files": len(all_files),
        "languages": dict(sorted(language_counts.items(), key=lambda x: -x[1])),
        "entry_points": entry_points,
        "files": all_files,
        "directory_tree": {k: v for k, v in sorted(dir_tree.items())},
    }


def _is_entry_point(path: Path, root: Path) -> bool:
    """Heuristic detection of repository entry points."""
    name = path.name.lower()
    entry_point_names = {
        "main.py", "app.py", "server.py", "run.py", "manage.py",
        "index.js", "index.ts", "main.js", "main.ts",
        "main.go", "main.rs", "main.java",
        "pyproject.toml", "package.json", "go.mod", "cargo.toml",
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile",
    }
    return name in entry_point_names

```

### File: `clockwork/cli/commands/security.py`

```python
﻿"""
clockwork/cli/commands/security.py
------------------------------------
CLI commands for the Security subsystem (spec §14).

Commands:
    clockwork security scan    — scan repo for security issues
    clockwork security audit   — full security audit report
    clockwork security log     — show recent security events
    clockwork security verify  — verify a plugin before installing
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from clockwork.cli.output import header, success, info, warn, error, step, rule, json_output

security_app = typer.Typer(
    name="security",
    help="Security scanning and auditing tools.",
    no_args_is_help=True,
)


def _engine(repo_root: Optional[Path]):
    root = (repo_root or Path.cwd()).resolve()
    cw   = root / ".clockwork"
    if not cw.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)
    from clockwork.security import SecurityEngine
    return SecurityEngine(root)


# ── clockwork security scan ────────────────────────────────────────────────

@security_app.command("scan")
def security_scan(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Scan the repository for security issues."""
    eng = _engine(repo_root)

    if not as_json:
        header("Clockwork Security Scan")
        step("Scanning repository...")

    result = eng.scan()

    if as_json:
        json_output(result.to_dict())
        return

    rule()
    if result.passed:
        success(f"Scan passed — risk level: {result.risk_level.upper()}")
    else:
        error(f"Scan found issues — risk level: {result.risk_level.upper()}")

    info(f"  Elapsed : {result.elapsed_ms:.0f} ms")

    if result.sensitive_files_found:
        rule()
        warn(f"Sensitive files found ({len(result.sensitive_files_found)}):")
        for f in result.sensitive_files_found:
            warn(f"  ! {f}")

    if result.issues:
        rule()
        error(f"Issues ({len(result.issues)}):")
        for iss in result.issues:
            info(f"  ✗ {iss}")

    if result.warnings:
        rule()
        warn(f"Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            info(f"  ! {w}")

    if not result.protected_files_ok:
        rule()
        warn("Some protected files are missing or unreadable.")
        info("  Run:  clockwork repair")


# ── clockwork security audit ───────────────────────────────────────────────

@security_app.command("audit")
def security_audit(
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Run a full security audit (scan + plugins + agents + log review)."""
    eng = _engine(repo_root)

    if not as_json:
        header("Clockwork Security Audit")
        step("Running full audit...")

    report = eng.audit()

    if as_json:
        json_output(report)
        return

    rule()
    risk = report.get("risk_level", "unknown").upper()
    total = report.get("total_issues", 0)

    if total == 0:
        success(f"Audit passed — risk level: {risk}")
    else:
        error(f"Audit found {total} issue(s) — risk level: {risk}")

    scan = report.get("scan", {})
    info(f"  Scan issues   : {len(scan.get('issues', []))}")
    info(f"  Plugin issues : {len(report.get('plugin_issues', []))}")
    info(f"  Agent issues  : {len(report.get('agent_issues', []))}")
    info(f"  Log events    : {len(report.get('recent_events', []))}")

    for section, key in [("Plugin issues", "plugin_issues"), ("Agent issues", "agent_issues")]:
        items = report.get(key, [])
        if items:
            rule()
            warn(f"{section}:")
            for item in items:
                info(f"  ! {item}")


# ── clockwork security log ─────────────────────────────────────────────────

@security_app.command("log")
def security_log(
    n:         int            = typer.Option(20, "--last", "-n",
                                    help="Number of recent events to show."),
    repo_root: Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:   bool           = typer.Option(False, "--json"),
) -> None:
    """Show recent security log events."""
    eng     = _engine(repo_root)
    entries = eng.logger.recent(n)

    if as_json:
        json_output(entries)
        return

    header(f"Security Log (last {n})")
    if not entries:
        info("No security events recorded.")
        return

    for e in entries:
        risk  = e.get("risk_level", "").upper()
        event = e.get("event", "")
        ts    = e.get("timestamp", "")[:19].replace("T", " ")
        fp    = e.get("file", "")
        detail = e.get("detail", "")
        line  = f"  [{ts}] [{risk:<8}] {event}"
        if fp:
            line += f"  {fp}"
        if detail and detail != f"Access to restricted path blocked: {fp}":
            line += f"\n    {detail}"
        info(line)


# ── clockwork security verify ──────────────────────────────────────────────

@security_app.command("verify")
def security_verify(
    plugin_path: Path          = typer.Argument(...,
                                    help="Path to the plugin directory to verify."),
    repo_root:   Optional[Path] = typer.Option(None, "--repo", "-r"),
    as_json:     bool           = typer.Option(False, "--json"),
) -> None:
    """Verify a plugin before installing it."""
    eng = _engine(repo_root)

    if not as_json:
        header(f"Plugin Verification: {plugin_path.name}")

    ok, issues = eng.verify_plugin(plugin_path)

    if as_json:
        json_output({"ok": ok, "issues": issues})
        return

    rule()
    if ok:
        success("Plugin verification passed.")
    else:
        error("Plugin verification failed.")
        for iss in issues:
            info(f"  ✗ {iss}")


```

### File: `clockwork/cli/commands/update.py`

```python
﻿"""
clockwork/cli/commands/update.py
----------------------------------
`clockwork update` — merge scanner results into context.yaml.

Reads .clockwork/repo_map.json and updates the fields inside
.clockwork/context.yaml that can be derived automatically:

  • primary_language
  • frameworks   (detected from dependency manifests)
  • entry_points
  • recent changes timestamp
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule,
)

# ── Framework fingerprints ─────────────────────────────────────────────────

# Maps a filename to the frameworks it implies when present in the repo root.
FRAMEWORK_FINGERPRINTS: dict[str, list[str]] = {
    "pyproject.toml": [],      # read dynamically
    "requirements.txt": [],    # read dynamically
    "package.json": [],        # read dynamically
    "go.mod": ["Go Modules"],
    "cargo.toml": ["Rust / Cargo"],
    "pom.xml": ["Maven / Java"],
    "build.gradle": ["Gradle / JVM"],
    "dockerfile": ["Docker"],
    "docker-compose.yml": ["Docker Compose"],
    "docker-compose.yaml": ["Docker Compose"],
    ".github": ["GitHub Actions"],
}

PYTHON_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "fastapi": "FastAPI", "flask": "Flask", "django": "Django",
    "typer": "Typer", "click": "Click", "starlette": "Starlette",
    "sqlalchemy": "SQLAlchemy", "pydantic": "Pydantic",
    "pytest": "pytest", "celery": "Celery",
}

JS_FRAMEWORK_KEYWORDS: dict[str, str] = {
    "react": "React", "vue": "Vue", "angular": "Angular",
    "next": "Next.js", "nuxt": "Nuxt", "express": "Express",
    "fastify": "Fastify", "svelte": "Svelte",
}


# ── Command ────────────────────────────────────────────────────────────────

def cmd_update(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
) -> None:
    """
    Merge scanner results into .clockwork/context.yaml.

    Run after `clockwork scan` to keep project context current.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    header("Clockwork Update")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    repo_map_path = cw_dir / "repo_map.json"
    if not repo_map_path.exists():
        error("repo_map.json not found.\nRun:  clockwork scan")
        raise typer.Exit(code=1)

    context_path = cw_dir / "context.yaml"
    if not context_path.exists():
        error("context.yaml not found.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    try:
        repo_map: dict = json.loads(repo_map_path.read_text(encoding="utf-8"))
        context: dict = yaml.safe_load(context_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        error(f"Failed to read project files: {exc}")
        raise typer.Exit(code=1)

    step("Deriving primary language...")
    primary_language = _derive_primary_language(repo_map)

    step("Detecting frameworks...")
    frameworks = _detect_frameworks(root, repo_map)

    step("Collecting entry points...")
    entry_points = repo_map.get("entry_points", [])

    # Prefer ContextEngine + ScanResult for merge; fall back to raw dict merge
    try:
        from clockwork.context import ContextEngine
        from clockwork.scanner.models import ScanResult
        scan_result = ScanResult.load(cw_dir)
        engine = ContextEngine(cw_dir)
        context_obj = engine.merge_scan(scan_result)
        engine.save(context_obj)
        primary_language = context_obj.primary_language
        frameworks = list(context_obj.frameworks)
        entry_points = list(context_obj.entry_points)
    except Exception:
        # Fallback: manual raw-dict merge
        context["primary_language"] = primary_language
        context["frameworks"] = sorted(set(frameworks))
        context["entry_points"] = entry_points
        context["last_updated"] = datetime.now(timezone.utc).isoformat()
        context["total_files"] = repo_map.get("total_files", 0)
        context["languages"] = repo_map.get("languages", {})
        try:
            context_path.write_text(
                yaml.dump(context, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except OSError as exc:
            error(f"Failed to write context.yaml: {exc}")
            raise typer.Exit(code=1)

    rule()
    success("context.yaml updated")
    info(f"  Primary language : {primary_language or '(unknown)'}")
    info(f"  Frameworks       : {', '.join(frameworks) or '(none detected)'}")
    info(f"  Entry points     : {len(entry_points)}")
    info("\nNext step: run  clockwork verify")


# ── Derivation helpers ─────────────────────────────────────────────────────

def _derive_primary_language(repo_map: dict) -> str:
    """Return the language with the most files, or empty string."""
    languages = repo_map.get("languages", {})
    if not languages:
        return ""
    # Support both dict {lang: count} and legacy list [lang, ...]
    if isinstance(languages, list):
        return languages[0] if languages else ""
    return max(languages, key=lambda k: languages[k])


def _detect_frameworks(root: Path, repo_map: dict) -> list[str]:
    """Heuristically detect frameworks used in the repository."""
    detected: list[str] = []
    files_in_root = {
        p["path"].lower().replace("\\", "/")
        for p in repo_map.get("files", [])
        if "/" not in p["path"].replace("\\", "/")   # only root-level files
    }

    # Static fingerprints
    for filename, frameworks in FRAMEWORK_FINGERPRINTS.items():
        if filename in files_in_root:
            detected.extend(frameworks)

    # Python: parse requirements.txt / pyproject.toml
    if "requirements.txt" in files_in_root:
        detected.extend(_parse_requirements(root / "requirements.txt"))

    if "pyproject.toml" in files_in_root:
        detected.extend(_parse_pyproject(root / "pyproject.toml"))

    # JS: parse package.json
    if "package.json" in files_in_root:
        detected.extend(_parse_package_json(root / "package.json"))

    return list(dict.fromkeys(detected))  # deduplicate, preserve order


def _parse_requirements(path: Path) -> list[str]:
    """Scan requirements.txt for known framework names."""
    found: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            pkg = line.strip().lower().split("==")[0].split(">=")[0].split("[")[0]
            if pkg in PYTHON_FRAMEWORK_KEYWORDS:
                found.append(PYTHON_FRAMEWORK_KEYWORDS[pkg])
    except OSError:
        pass
    return found


def _parse_pyproject(path: Path) -> list[str]:
    """Scan pyproject.toml dependencies for known framework names (quoted form only)."""
    found: list[str] = []
    try:
        content = path.read_text(encoding="utf-8").lower()
        for keyword, name in PYTHON_FRAMEWORK_KEYWORDS.items():
            # Only match when the keyword appears as a dependency value (quoted)
            if f'"{keyword}' in content or f"'{keyword}" in content or f"\n{keyword}" in content:
                found.append(name)
    except OSError:
        pass
    return found


def _parse_package_json(path: Path) -> list[str]:
    """Scan package.json dependencies for known JS frameworks."""
    found: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        all_deps = {
            **data.get("dependencies", {}),
            **data.get("devDependencies", {}),
        }
        for pkg_name in all_deps:
            key = pkg_name.lstrip("@").split("/")[-1].lower()
            if key in JS_FRAMEWORK_KEYWORDS:
                found.append(JS_FRAMEWORK_KEYWORDS[key])
    except (OSError, json.JSONDecodeError):
        pass
    return found

```

### File: `clockwork/cli/commands/verify.py`

```python
"""
clockwork/cli/commands/verify.py
----------------------------------
`clockwork verify` — verify repository integrity.

Pipeline (spec §6):
    Repository Diff
    ↓
    Rule Evaluation
    ↓
    Brain Analysis   (stub — full Brain subsystem implemented separately)

Currently implements:
  • context.yaml schema validation
  • repo_map.json presence and structure check
  • rules.md presence check
  • Protected file integrity check
  • Basic rule text parsing for violations
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer
import yaml

from clockwork.cli.output import (
    header, success, info, warn, error, step, rule, result_block, json_output,
)


# ── Data structures ────────────────────────────────────────────────────────

@dataclass
class VerificationResult:
    passed: bool = True
    checks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def fail(self, reason: str) -> None:
        self.passed = False
        self.failures.append(reason)

    def ok(self, msg: str) -> None:
        self.checks.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "warnings": self.warnings,
            "failures": self.failures,
        }


# ── Command ────────────────────────────────────────────────────────────────

def cmd_verify(
    repo_root: Optional[Path] = typer.Option(
        None, "--repo", "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    as_json: bool = typer.Option(
        False, "--json",
        help="Emit machine-readable JSON output.",
    ),
) -> None:
    """
    Verify repository integrity against Clockwork rules.

    Runs the Rule Engine pipeline: diff → rule evaluation → brain analysis.
    """
    root = (repo_root or Path.cwd()).resolve()
    cw_dir = root / ".clockwork"

    if not as_json:
        header("Clockwork Verify")

    if not cw_dir.is_dir():
        error("Clockwork not initialised.\nRun:  clockwork init")
        raise typer.Exit(code=1)

    start = time.perf_counter()
    result = VerificationResult()

    # Run each check stage
    _check_required_files(cw_dir, result)
    _check_context_schema(cw_dir, result)
    _check_repo_map(cw_dir, result)
    _check_protected_directories(cw_dir, result)
    _check_rules_parseable(cw_dir, result)

    elapsed_ms = (time.perf_counter() - start) * 1000

    if as_json:
        json_output({**result.to_dict(), "elapsed_ms": round(elapsed_ms, 1)})
        raise typer.Exit(code=0 if result.passed else 1)

    # Human output
    rule()
    for msg in result.checks:
        success(msg)
    for msg in result.warnings:
        warn(msg)
    for msg in result.failures:
        typer.echo(f"  ✗ {msg}")

    rule()
    if result.passed:
        typer.echo(f"\n{'  ' + chr(10033) + ' Verification passed.'} "
                   f"({elapsed_ms:.0f} ms)")
    else:
        typer.echo(
            f"\nVerification FAILED — {len(result.failures)} issue(s) found.",
            err=True,
        )
        raise typer.Exit(code=1)


# ── Check stages ───────────────────────────────────────────────────────────

def _check_required_files(cw_dir: Path, result: VerificationResult) -> None:
    """Verify all required .clockwork files exist."""
    required = ["context.yaml", "rules.md", "config.yaml"]
    for filename in required:
        if (cw_dir / filename).exists():
            result.ok(f"Found .clockwork/{filename}")
        else:
            result.fail(f"Missing required file: .clockwork/{filename}")


def _check_context_schema(cw_dir: Path, result: VerificationResult) -> None:
    """Validate context.yaml can be parsed and has required keys."""
    ctx_path = cw_dir / "context.yaml"
    if not ctx_path.exists():
        return  # already caught above

    try:
        ctx = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        result.fail(f"context.yaml is not valid YAML: {exc}")
        return

    required_keys = ["clockwork_version", "project_name", "memory_schema_version"]
    for key in required_keys:
        if key not in ctx:
            result.warn(f"context.yaml missing recommended key: '{key}'")

    result.ok("context.yaml schema valid")


def _check_repo_map(cw_dir: Path, result: VerificationResult) -> None:
    """Validate repo_map.json is present and parseable."""
    rm_path = cw_dir / "repo_map.json"
    if not rm_path.exists():
        result.warn("repo_map.json not found — run  clockwork scan")
        return

    try:
        data = json.loads(rm_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.fail(f"repo_map.json is not valid JSON: {exc}")
        return

    total = data.get("total_files", "?")
    result.ok(f"repo_map.json valid ({total} files indexed)")


def _check_protected_directories(cw_dir: Path, result: VerificationResult) -> None:
    """Ensure critical .clockwork sub-directories exist."""
    for sub in ("handoff", "packages", "logs"):
        if (cw_dir / sub).is_dir():
            result.ok(f".clockwork/{sub}/ present")
        else:
            result.warn(f".clockwork/{sub}/ missing — re-run  clockwork init")


def _check_rules_parseable(cw_dir: Path, result: VerificationResult) -> None:
    """Ensure rules.md is non-empty and readable."""
    rules_path = cw_dir / "rules.md"
    if not rules_path.exists():
        return  # caught by required files check

    try:
        content = rules_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        result.fail(f"Cannot read rules.md: {exc}")
        return

    if not content:
        result.warn("rules.md is empty — consider adding project rules")
    else:
        rule_count = sum(1 for line in content.splitlines() if line.startswith("- "))
        result.ok(f"rules.md readable ({rule_count} rule(s) found)")

```

### File: `clockwork/context/__init__.py`

```python
"""
clockwork/context/__init__.py
-------------------------------
Context Engine subsystem.

The Context Engine is responsible for:
  • loading and validating .clockwork/context.yaml
  • merging scanner results into persistent project context
  • tracking task state and recent changes
  • providing a typed ProjectContext object to all other subsystems

Public API::

    from clockwork.context import ContextEngine, ProjectContext

    engine  = ContextEngine(clockwork_dir=Path(".clockwork"))
    context = engine.load()
    engine.merge_scan(scan_result)
    engine.save(context)
"""

from clockwork.context.models import ProjectContext, TaskEntry, ChangeEntry
from clockwork.context.engine import ContextEngine

__all__ = [
    "ContextEngine",
    "ProjectContext",
    "TaskEntry",
    "ChangeEntry",
]

```

### File: `clockwork/context/engine.py`

```python
"""
clockwork/context/engine.py
-----------------------------
ContextEngine — manages the lifecycle of .clockwork/context.yaml.

Responsibilities:
  • load()        — read and validate context.yaml into ProjectContext
  • save()        — write ProjectContext back to context.yaml
  • merge_scan()  — update auto-derived fields from a ScanResult
  • validate()    — check schema version and required fields
  • diff()        — detect what changed since last merge
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from clockwork.context.models import (
    ProjectContext,
    TaskEntry,
    ChangeEntry,
    ArchitectureNote,
    CONTEXT_SCHEMA_VERSION,
    CLOCKWORK_VERSION,
)


class ContextError(Exception):
    """Raised when the context cannot be loaded or is invalid."""


class ContextEngine:
    """
    Manages reading, writing, and updating .clockwork/context.yaml.

    Usage::

        engine  = ContextEngine(clockwork_dir=Path(".clockwork"))
        context = engine.load()

        # after a scan:
        engine.merge_scan(scan_result)

        # update a task:
        context.current_tasks[0].mark_done()
        engine.save(context)
    """

    CONTEXT_FILE = "context.yaml"

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir.resolve()
        self.context_path  = self.clockwork_dir / self.CONTEXT_FILE

    # ------------------------------------------------------------------ #
    # Load / Save
    # ------------------------------------------------------------------ #

    def load(self) -> ProjectContext:
        """
        Load and return the current ProjectContext from disk.

        Raises ContextError if the file is missing or unparseable.
        """
        if not self.context_path.exists():
            raise ContextError(
                f"context.yaml not found at {self.context_path}\n"
                "Run:  clockwork init"
            )

        try:
            raw = self.context_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError as exc:
            raise ContextError(f"context.yaml is not valid YAML: {exc}") from exc
        except OSError as exc:
            raise ContextError(f"Cannot read context.yaml: {exc}") from exc

        if not isinstance(data, dict):
            raise ContextError("context.yaml must be a YAML mapping at the top level.")

        context = ProjectContext.from_dict(data)
        return context

    def load_or_default(self, project_name: str = "") -> ProjectContext:
        """
        Load context from disk, or return a fresh default context if the
        file does not yet exist.  Does not raise on missing file.
        """
        try:
            return self.load()
        except ContextError:
            return ProjectContext(project_name=project_name or self.clockwork_dir.parent.name)

    def save(self, context: ProjectContext) -> None:
        """
        Write *context* to .clockwork/context.yaml.

        Touches `last_updated` before writing.
        """
        context._touch()
        data = context.to_dict()

        try:
            self.clockwork_dir.mkdir(parents=True, exist_ok=True)
            self.context_path.write_text(
                yaml.dump(data, default_flow_style=False, allow_unicode=True,
                          sort_keys=False),
                encoding="utf-8",
            )
        except OSError as exc:
            raise ContextError(f"Cannot write context.yaml: {exc}") from exc

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, context: Optional[ProjectContext] = None) -> list[str]:
        """
        Validate a ProjectContext (or load from disk if none given).

        Returns a list of issue strings.  Empty list = valid.
        """
        issues: list[str] = []

        try:
            ctx = context or self.load()
        except ContextError as exc:
            return [str(exc)]

        if ctx.clockwork_version != CLOCKWORK_VERSION:
            issues.append(
                f"clockwork_version mismatch: "
                f"file={ctx.clockwork_version!r}, expected={CLOCKWORK_VERSION!r}"
            )

        if ctx.memory_schema_version != CONTEXT_SCHEMA_VERSION:
            issues.append(
                f"memory_schema_version mismatch: "
                f"file={ctx.memory_schema_version}, expected={CONTEXT_SCHEMA_VERSION}"
            )

        if not ctx.project_name:
            issues.append("project_name is empty.")

        for task in ctx.current_tasks:
            if task.status not in ("pending", "in_progress", "done", "blocked"):
                issues.append(
                    f"Task '{task.id}' has unknown status: {task.status!r}"
                )

        return issues

    # ------------------------------------------------------------------ #
    # Merge with scanner output
    # ------------------------------------------------------------------ #

    def merge_scan(self, scan_result: object) -> ProjectContext:
        """
        Update auto-derived context fields from a ScanResult.

        Preserves all human-authored fields (summary, architecture_overview,
        current_tasks, architecture_notes, agent_notes).

        Returns the updated ProjectContext (also saves to disk).
        """
        # Lazy import to avoid circular dependency
        from clockwork.scanner.models import ScanResult

        if not isinstance(scan_result, ScanResult):
            raise TypeError("scan_result must be a clockwork.scanner.models.ScanResult")

        context = self.load_or_default(project_name=scan_result.project_name)

        # Capture what changed for the change log
        old_file_count  = context.total_files
        old_primary     = context.primary_language
        old_frameworks  = set(context.frameworks)

        # Overwrite scanner-derived fields
        context.primary_language = scan_result.primary_language
        context.languages        = dict(scan_result.languages)
        context.frameworks       = list(scan_result.frameworks)
        context.entry_points     = list(scan_result.entry_points)
        context.total_files      = scan_result.total_files
        context.total_lines      = scan_result.total_lines

        # Record the merge as a change event
        changes: list[str] = []
        if old_file_count != scan_result.total_files:
            delta = scan_result.total_files - old_file_count
            changes.append(
                f"File count: {old_file_count} → {scan_result.total_files} "
                f"({'+'  if delta > 0 else ''}{delta})"
            )
        if old_primary != scan_result.primary_language and scan_result.primary_language:
            changes.append(
                f"Primary language: {old_primary!r} → {scan_result.primary_language!r}"
            )
        new_frameworks = set(scan_result.frameworks) - old_frameworks
        if new_frameworks:
            changes.append(f"New frameworks detected: {', '.join(sorted(new_frameworks))}")

        if changes:
            context.record_change(ChangeEntry(
                description="Scan merge: " + "; ".join(changes),
                change_type="update",
                agent="clockwork.scanner",
            ))

        self.save(context)
        return context

    # ------------------------------------------------------------------ #
    # Diff
    # ------------------------------------------------------------------ #

    def diff(
        self, context_a: ProjectContext, context_b: ProjectContext
    ) -> dict[str, dict]:
        """
        Return a dict describing what changed between two ProjectContext
        snapshots.  Useful for verify and handoff pipelines.

        Returns::

            {
              "files": {"before": 10, "after": 12},
              "primary_language": {"before": "Python", "after": "Python"},
              ...
            }
        """
        diffs: dict[str, dict] = {}

        scalar_fields = (
            "primary_language", "total_files", "total_lines",
            "summary", "project_name",
        )
        for field in scalar_fields:
            a = getattr(context_a, field)
            b = getattr(context_b, field)
            if a != b:
                diffs[field] = {"before": a, "after": b}

        # Framework diff
        added_fw   = set(context_b.frameworks) - set(context_a.frameworks)
        removed_fw = set(context_a.frameworks) - set(context_b.frameworks)
        if added_fw or removed_fw:
            diffs["frameworks"] = {
                "added":   sorted(added_fw),
                "removed": sorted(removed_fw),
            }

        # Task diff
        ids_a = {t.id for t in context_a.current_tasks}
        ids_b = {t.id for t in context_b.current_tasks}
        added_tasks   = ids_b - ids_a
        removed_tasks = ids_a - ids_b
        if added_tasks or removed_tasks:
            diffs["tasks"] = {
                "added":   sorted(added_tasks),
                "removed": sorted(removed_tasks),
            }

        return diffs

    # ------------------------------------------------------------------ #
    # Convenience task helpers
    # ------------------------------------------------------------------ #

    def add_task(
        self,
        title: str,
        priority: str = "medium",
        notes: str = "",
        task_id: Optional[str] = None,
    ) -> TaskEntry:
        """Load context, add a task, save, and return the new TaskEntry."""
        import uuid
        context = self.load_or_default()
        task = TaskEntry(
            id=task_id or str(uuid.uuid4())[:8],
            title=title,
            priority=priority,
            notes=notes,
        )
        context.add_task(task)
        self.save(context)
        return task

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as done. Returns True if found."""
        context = self.load_or_default()
        task = context.task_by_id(task_id)
        if task is None:
            return False
        task.mark_done()
        self.save(context)
        return True

    def record_change(
        self,
        description: str,
        changed_files: Optional[list[str]] = None,
        agent: Optional[str] = None,
        change_type: str = "update",
    ) -> ChangeEntry:
        """Load context, append a change entry, save, return the entry."""
        context = self.load_or_default()
        change = ChangeEntry(
            description=description,
            changed_files=changed_files or [],
            agent=agent,
            change_type=change_type,
        )
        context.record_change(change)
        self.save(context)
        return change

```

### File: `clockwork/context/initializer.py`

```python
"""
Clockwork Context Initializer
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any
import yaml

logger = logging.getLogger(__name__)

CLOCKWORK_DIR = ".clockwork"
CONTEXT_FILE = "context.yaml"
CONTEXT_VERSION = 1

_EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".go": "go", ".rb": "ruby", ".java": "java", ".rs": "rust",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c",
}

_FRAMEWORK_HINTS = [
    ("flask", "Flask"), ("django", "Django"), ("fastapi", "FastAPI"),
    ("react", "React"), ("vue", "Vue"), ("express", "Express"),
    ("sqlalchemy", "SQLAlchemy"), ("celery", "Celery"),
    ("typer", "Typer"), ("click", "Click"),
]

class ContextInitializer:
    def __init__(self, repo_root="."): 
        self.repo_root = Path(repo_root).resolve()
        self.clockwork_dir = self.repo_root / CLOCKWORK_DIR
        self.context_path = self.clockwork_dir / CONTEXT_FILE

    def initialize(self):
        project_name = self.repo_root.name
        languages = self._detect_languages()
        frameworks = self._detect_frameworks()
        architecture = self._infer_architecture()
        skills = list(languages.keys()) + [f for f in frameworks if f not in languages]

        context = {
            "clockwork_context_version": CONTEXT_VERSION,
            "project": {"name": project_name, "type": "unknown", "version": "0.1"},
            "repository": {"architecture": architecture, "languages": languages},
            "frameworks": frameworks,
            "current_state": {
                "summary": "Initial repository scan complete.",
                "next_task": "Define first development task.",
                "blockers": [],
            },
            "skills_required": skills,
        }
        self._persist(context)
        return context

    def _detect_languages(self):
        counts = {}
        ignore_dirs = {".git", ".clockwork", "__pycache__", "node_modules", ".venv", "venv"}
        for path in self.repo_root.rglob("*"):
            if any(part in ignore_dirs for part in path.parts):
                continue
            if path.is_file() and path.suffix in _EXT_TO_LANG:
                lang = _EXT_TO_LANG[path.suffix]
                counts[lang] = counts.get(lang, 0) + 1
        if not counts:
            return {}
        total = sum(counts.values())
        return {lang: round(count / total * 100) for lang, count in sorted(counts.items(), key=lambda x: -x[1])}

    def _detect_frameworks(self):
        dep_text = self._read_dependency_files()
        found, seen = [], set()
        for fragment, label in _FRAMEWORK_HINTS:
            if fragment in dep_text and label not in seen:
                found.append(label)
                seen.add(label)
        return found

    def _infer_architecture(self):
        subdirs = {p.name for p in self.repo_root.iterdir() if p.is_dir()}
        if {"frontend", "backend", "api"}.intersection(subdirs): return "fullstack"
        if {"services", "microservices"}.intersection(subdirs): return "microservices"
        if {"src", "lib", "pkg"}.intersection(subdirs): return "layered"
        if (self.repo_root / "pyproject.toml").exists(): return "python_package"
        return "flat"

    def _read_dependency_files(self):
        parts = []
        for name in ["requirements.txt", "pyproject.toml", "package.json", "Pipfile", "setup.cfg"]:
            path = self.repo_root / name
            if path.exists():
                try: parts.append(path.read_text(encoding="utf-8").lower())
                except OSError: pass
        return "\n".join(parts)

    def _persist(self, context):
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.context_path.with_suffix(".yaml.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                yaml.dump(context, fh, default_flow_style=False, allow_unicode=True)
            tmp.replace(self.context_path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"Cannot write context file: {exc}") from exc


def initialize_clockwork_dir(repo_root: str = '.', force: bool = False) -> dict:
    """Convenience wrapper around ContextInitializer.initialize()."""
    return ContextInitializer(repo_root).initialize()

```

### File: `clockwork/context/models.py`

```python
"""
clockwork/context/models.py
-----------------------------
Typed data models for the Clockwork Context Engine.

ProjectContext is the central data structure that persists in
.clockwork/context.yaml and is shared across all subsystems.

Schema version history:
  1 — initial schema (v0.1)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Any
import json


CONTEXT_SCHEMA_VERSION = 1
CLOCKWORK_VERSION = "0.1"


# ── Sub-models ─────────────────────────────────────────────────────────────

@dataclass
class TaskEntry:
    """A single tracked development task."""

    id: str
    title: str
    status: str = "pending"          # pending | in_progress | done | blocked
    priority: str = "medium"         # low | medium | high | critical
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: Optional[str] = None
    assigned_to: Optional[str] = None   # agent name or "human"
    notes: str = ""

    def mark_done(self) -> None:
        self.status = "done"
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_in_progress(self, agent: Optional[str] = None) -> None:
        self.status = "in_progress"
        self.updated_at = datetime.now(timezone.utc).isoformat()
        if agent:
            self.assigned_to = agent

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TaskEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ChangeEntry:
    """A recorded repository change event."""

    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    description: str = ""
    changed_files: list[str] = field(default_factory=list)
    agent: Optional[str] = None       # which agent made the change
    change_type: str = "update"       # update | refactor | feature | fix | docs

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ChangeEntry":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ArchitectureNote:
    """A recorded architectural decision or constraint."""

    id: str
    title: str
    description: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ArchitectureNote":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Main context model ─────────────────────────────────────────────────────

@dataclass
class ProjectContext:
    """
    The complete persisted project context.

    This is the canonical project memory document stored in
    .clockwork/context.yaml and shared across all Clockwork subsystems.
    """

    # ── Identity ──────────────────────────────────────────────────────────
    clockwork_version: str = CLOCKWORK_VERSION
    memory_schema_version: int = CONTEXT_SCHEMA_VERSION
    project_name: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_updated: Optional[str] = None

    # ── Human-authored descriptions ───────────────────────────────────────
    summary: str = ""
    architecture_overview: str = ""

    # ── Scanner-derived fields (auto-updated by merge_scan) ───────────────
    primary_language: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    total_files: int = 0
    total_lines: int = 0

    # ── Tasks ─────────────────────────────────────────────────────────────
    current_tasks: list[TaskEntry] = field(default_factory=list)

    # ── Change history ────────────────────────────────────────────────────
    recent_changes: list[ChangeEntry] = field(default_factory=list)
    max_recent_changes: int = 50   # rolling window

    # ── Architecture notes ────────────────────────────────────────────────
    architecture_notes: list[ArchitectureNote] = field(default_factory=list)

    # ── Agent metadata ────────────────────────────────────────────────────
    last_agent: Optional[str] = None
    agent_notes: str = ""

    # ── Extra fields preserved from disk (forward-compatibility) ─────────
    _extra: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ #
    # Derived properties
    # ------------------------------------------------------------------ #

    @property
    def pending_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "pending"]

    @property
    def in_progress_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "in_progress"]

    @property
    def done_tasks(self) -> list[TaskEntry]:
        return [t for t in self.current_tasks if t.status == "done"]

    def task_by_id(self, task_id: str) -> Optional[TaskEntry]:
        return next((t for t in self.current_tasks if t.id == task_id), None)

    # ------------------------------------------------------------------ #
    # Mutation helpers
    # ------------------------------------------------------------------ #

    def add_task(self, task: TaskEntry) -> None:
        """Add a task; replace if id already exists."""
        self.current_tasks = [t for t in self.current_tasks if t.id != task.id]
        self.current_tasks.append(task)
        self._touch()

    def remove_task(self, task_id: str) -> bool:
        """Remove task by id. Returns True if found and removed."""
        before = len(self.current_tasks)
        self.current_tasks = [t for t in self.current_tasks if t.id != task_id]
        removed = len(self.current_tasks) < before
        if removed:
            self._touch()
        return removed

    def record_change(self, change: ChangeEntry) -> None:
        """Append a change entry, trimming the rolling window."""
        self.recent_changes.append(change)
        if len(self.recent_changes) > self.max_recent_changes:
            self.recent_changes = self.recent_changes[-self.max_recent_changes:]
        self._touch()

    def add_architecture_note(self, note: ArchitectureNote) -> None:
        self.architecture_notes = [
            n for n in self.architecture_notes if n.id != note.id
        ]
        self.architecture_notes.append(note)
        self._touch()

    def _touch(self) -> None:
        self.last_updated = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Produce a plain dict suitable for YAML / JSON serialisation."""
        d: dict[str, Any] = {
            "clockwork_version":      self.clockwork_version,
            "memory_schema_version":  self.memory_schema_version,
            "project_name":           self.project_name,
            "created_at":             self.created_at,
            "last_updated":           self.last_updated,
            "summary":                self.summary,
            "architecture_overview":  self.architecture_overview,
            "primary_language":       self.primary_language,
            "languages":              self.languages,
            "frameworks":             self.frameworks,
            "entry_points":           self.entry_points,
            "total_files":            self.total_files,
            "total_lines":            self.total_lines,
            "current_tasks":          [t.to_dict() for t in self.current_tasks],
            "recent_changes":         [c.to_dict() for c in self.recent_changes],
            "max_recent_changes":     self.max_recent_changes,
            "architecture_notes":     [n.to_dict() for n in self.architecture_notes],
            "last_agent":             self.last_agent,
            "agent_notes":            self.agent_notes,
        }
        # Re-attach any extra keys from disk for forward-compatibility
        d.update(self._extra)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ProjectContext":
        """Reconstruct from a plain dict (loaded from YAML or JSON)."""
        known_keys = {f for f in cls.__dataclass_fields__ if f != "_extra"}

        tasks = [
            TaskEntry.from_dict(t)
            for t in data.get("current_tasks", [])
            if isinstance(t, dict)
        ]
        changes = [
            ChangeEntry.from_dict(c)
            for c in data.get("recent_changes", [])
            if isinstance(c, dict)
        ]
        notes = [
            ArchitectureNote.from_dict(n)
            for n in data.get("architecture_notes", [])
            if isinstance(n, dict)
        ]

        scalar_fields = {
            k: v for k, v in data.items()
            if k in known_keys
            and k not in ("current_tasks", "recent_changes", "architecture_notes")
        }
        extra = {k: v for k, v in data.items() if k not in known_keys}

        return cls(
            **scalar_fields,
            current_tasks=tasks,
            recent_changes=changes,
            architecture_notes=notes,
            _extra=extra,
        )

```

### File: `clockwork/context/schema.py`

```python
﻿"""
Clockwork Context Schema
"""
from __future__ import annotations
from typing import Any

CONTEXT_VERSION = 1

CONTEXT_SCHEMA: dict[str, Any] = {
    "project": {
        "type": dict,
        "required": True,
        "fields": {
            "name": {"type": str, "required": True},
            "type": {"type": str, "required": False},
            "version": {"type": (str, float, int), "required": False},
        },
    },
    "repository": {
        "type": dict,
        "required": True,
        "fields": {
            "architecture": {"type": str, "required": False},
            "languages": {"type": dict, "required": False},
        },
    },
    "frameworks": {"type": list, "required": False},
    "current_state": {
        "type": dict,
        "required": True,
        "fields": {
            "summary": {"type": str, "required": False},
            "next_task": {"type": str, "required": False},
            "blockers": {"type": list, "required": False},
        },
    },
    "skills_required": {"type": list, "required": False},
    "clockwork_context_version": {"type": int, "required": False},
}

def validate_context_schema(data, schema, path=""):
    """
    Validate a context dict against the given schema.

    Note: list item types are not checked (schema only validates the container type).
    The 'languages' field accepts both dict {lang: count} and list [lang] shapes
    for backwards compatibility with the legacy RepositoryScanner.
    """
    errors = []
    for key, rules in schema.items():
        full_key = f"{path}.{key}" if path else key
        value = data.get(key)
        if rules.get("required") and value is None:
            errors.append(f"Missing required field: '{full_key}'")
            continue
        if value is None:
            continue
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Field '{full_key}' must be {expected_type}, got {type(value).__name__}.")
            continue
        if rules.get("fields") and isinstance(value, dict):
            errors.extend(validate_context_schema(value, rules["fields"], full_key))
    return errors

```

### File: `clockwork/graph/__init__.py`

```python
﻿"""
clockwork/graph/__init__.py
----------------------------
Knowledge Graph subsystem.

The Knowledge Graph builds a SQLite-backed graph model of the
repository so Clockwork (and the Brain) can answer questions like:

  - Which files depend on X?
  - Which modules belong to the backend layer?
  - Is it safe to delete this file?

Public API::

    from clockwork.graph import GraphEngine

    engine = GraphEngine(repo_root=Path("."))
    stats  = engine.build()          # builds .clockwork/knowledge_graph.db
    q      = engine.query()
    deps   = q.who_depends_on("clockwork/scanner/scanner.py")
    layers = q.layer_summary()
    engine.close()
"""

from clockwork.graph.graph_engine import GraphEngine
from clockwork.graph.models import GraphStats, GraphNode, GraphEdge, NodeType, EdgeType
from clockwork.graph.queries import GraphQueryEngine

__all__ = [
    "GraphEngine",
    "GraphQueryEngine",
    "GraphStats",
    "GraphNode",
    "GraphEdge",
    "NodeType",
    "EdgeType",
]


```

### File: `clockwork/graph/builder.py`

```python
﻿"""
clockwork/graph/builder.py
---------------------------
Builds the knowledge graph from a ScanResult / repo_map dict.

Pipeline (spec §8):
    repo_map.json
        ↓
    File nodes
        ↓
    Language / Layer / Service nodes
        ↓
    Dependency edges  (from symbol imports)
        ↓
    Structural edges  (belongs_to, part_of_layer)
        ↓
    Commit to SQLite
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .models import (
    EdgeType,
    GraphStats,
    LAYER_PATTERNS,
    NodeType,
)
from .storage import GraphStorage


class GraphBuilder:
    """
    Constructs nodes and edges from a repo_map dict and writes them
    to the provided GraphStorage instance.

    Usage::

        storage = GraphStorage(db_path)
        storage.open()
        storage.initialise(drop_existing=True)
        builder = GraphBuilder(storage)
        stats = builder.build(repo_map)
        storage.close()
    """

    def __init__(self, storage: GraphStorage) -> None:
        self._s = storage

    # ── public entry point ─────────────────────────────────────────────────

    def build(self, repo_map: dict[str, Any]) -> GraphStats:
        """
        Full build from a repo_map dict.

        Returns GraphStats with counts and elapsed time.
        """
        t0 = time.perf_counter()

        files: list[dict[str, Any]] = repo_map.get("files", [])

        # 1. Language nodes
        self._build_language_nodes(repo_map)

        # 2. Layer nodes
        layer_ids = self._build_layer_nodes()

        # 3. Service nodes (detected from directory structure)
        service_ids = self._build_service_nodes(files)

        # 4. File nodes + structural edges
        file_node_ids = self._build_file_nodes(files, layer_ids, service_ids)

        # 5. Symbol nodes (classes, functions) from file entries
        self._build_symbol_nodes(files, file_node_ids)

        # 6. Dependency edges (imports between files)
        self._build_import_edges(files, file_node_ids)

        # 7. External dependency nodes (third-party packages)
        self._build_external_dep_nodes(files, file_node_ids)

        self._s.commit()

        elapsed = (time.perf_counter() - t0) * 1000
        counts = self._s.count_nodes_by_kind()

        return GraphStats(
            node_count=self._s.count_nodes(),
            edge_count=self._s.count_edges(),
            file_count=counts.get(NodeType.FILE, 0),
            layer_count=counts.get(NodeType.LAYER, 0),
            service_count=counts.get(NodeType.SERVICE, 0),
            language_count=counts.get(NodeType.LANGUAGE, 0),
            elapsed_ms=elapsed,
        )

    # ── language nodes ─────────────────────────────────────────────────────

    def _build_language_nodes(self, repo_map: dict[str, Any]) -> None:
        """Insert one node per detected language."""
        languages: dict[str, Any] = repo_map.get("languages", {})
        if isinstance(languages, dict):
            for lang_name in languages:
                self._s.get_or_create_node(NodeType.LANGUAGE, lang_name)
        elif isinstance(languages, list):
            for lang_name in languages:
                self._s.get_or_create_node(NodeType.LANGUAGE, str(lang_name))

    # ── layer nodes ────────────────────────────────────────────────────────

    def _build_layer_nodes(self) -> dict[str, int]:
        """Insert architectural layer nodes, return {layer_name: node_id}."""
        layer_ids: dict[str, int] = {}
        for layer_name in LAYER_PATTERNS:
            nid = self._s.get_or_create_node(NodeType.LAYER, layer_name)
            layer_ids[layer_name] = nid
        return layer_ids

    # ── service nodes ──────────────────────────────────────────────────────

    def _build_service_nodes(self, files: list[dict[str, Any]]) -> dict[str, int]:
        """
        Detect service boundaries from directory structure.

        A 'service' is a top-level directory that contains source files
        and looks like a bounded context (services/, apps/, packages/, etc.).
        """
        service_roots: set[str] = set()
        service_parent_dirs = {"services", "apps", "packages", "modules", "components"}

        for f in files:
            parts = Path(f.get("path", "")).parts
            if len(parts) >= 2 and parts[0].lower() in service_parent_dirs:
                service_roots.add(f"{parts[0]}/{parts[1]}")

        service_ids: dict[str, int] = {}
        for svc in sorted(service_roots):
            nid = self._s.get_or_create_node(
                NodeType.SERVICE, svc, file_path=svc
            )
            service_ids[svc] = nid
        return service_ids

    # ── file nodes ─────────────────────────────────────────────────────────

    def _build_file_nodes(
        self,
        files: list[dict[str, Any]],
        layer_ids: dict[str, int],
        service_ids: dict[str, int],
    ) -> dict[str, int]:
        """
        Insert one node per file, plus structural edges:
        - file belongs_to language
        - file part_of_layer <layer>
        - file part_of_service <service>  (when applicable)
        """
        file_node_ids: dict[str, int] = {}

        for f in files:
            path     = f.get("path", "")
            language = f.get("language", "")
            layer    = _detect_layer(path)

            if not path:
                continue

            nid = self._s.insert_node(
                kind=NodeType.FILE,
                label=Path(path).name,
                file_path=path,
                language=language,
                layer=layer,
            )
            file_node_ids[path] = nid

            # edge → language node
            if language:
                lang_nid = self._s.get_or_create_node(NodeType.LANGUAGE, language)
                self._s.insert_edge(nid, lang_nid, EdgeType.BELONGS_TO)

            # edge → layer node
            if layer and layer in layer_ids:
                self._s.insert_edge(nid, layer_ids[layer], EdgeType.PART_OF_LAYER)

            # edge → service node
            svc_key = _detect_service(path)
            if svc_key and svc_key in service_ids:
                self._s.insert_edge(nid, service_ids[svc_key], EdgeType.PART_OF_SERVICE)

        return file_node_ids

    # ── symbol nodes ───────────────────────────────────────────────────────

    def _build_symbol_nodes(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        Insert class/function nodes for symbols detected by the scanner.
        Each symbol gets a 'contains' edge from its parent file.
        """
        for f in files:
            path    = f.get("path", "")
            symbols = f.get("symbols", [])
            file_nid = file_node_ids.get(path)
            if not file_nid or not symbols:
                continue

            for sym in symbols:
                sym_kind  = sym.get("kind", "function")
                sym_name  = sym.get("name", "")
                if not sym_name:
                    continue

                node_type = NodeType.CLASS if sym_kind == "class" else NodeType.FUNCTION
                label     = f"{sym_name} ({Path(path).name})"
                sym_nid   = self._s.insert_node(
                    kind=node_type,
                    label=label,
                    file_path=path,
                )
                self._s.insert_edge(file_nid, sym_nid, EdgeType.CONTAINS)

    # ── import edges ───────────────────────────────────────────────────────

    def _build_import_edges(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        For each file, resolve its imports list to other known files
        and create 'imports' edges.

        Strategy: try to match import strings to known file paths by
        converting dot-notation to path fragments.
        """
        # Build a lookup: module-path fragment → node id
        # e.g.  "clockwork/scanner/scanner.py" → 42
        path_index: dict[str, int] = {}
        for fpath, nid in file_node_ids.items():
            normalised = fpath.replace("\\", "/")
            path_index[normalised] = nid
            # also index stem (without extension)
            stem_key = normalised.rsplit(".", 1)[0]
            path_index.setdefault(stem_key, nid)
            # and dotted module form
            dot_key = stem_key.replace("/", ".")
            path_index.setdefault(dot_key, nid)

        for f in files:
            src_path = f.get("path", "").replace("\\", "/")
            src_nid  = file_node_ids.get(f.get("path", ""))
            if not src_nid:
                continue

            for imp in f.get("imports", []):
                target_nid = _resolve_import(imp, src_path, path_index)
                if target_nid and target_nid != src_nid:
                    self._s.insert_edge(src_nid, target_nid, EdgeType.IMPORTS)

    # ── external dependency nodes ──────────────────────────────────────────

    def _build_external_dep_nodes(
        self,
        files: list[dict[str, Any]],
        file_node_ids: dict[str, int],
    ) -> None:
        """
        Imports that could NOT be resolved to internal files are treated
        as external dependencies.  One DEPENDENCY node per unique package
        root name, with a 'depends_on' edge from each importing file.
        """
        # Build set of known internal module stems for quick lookup
        internal_stems: set[str] = set()
        for fpath in file_node_ids:
            norm = fpath.replace("\\", "/").rsplit(".", 1)[0]
            for part in norm.replace("/", ".").split("."):
                internal_stems.add(part)

        for f in files:
            src_nid  = file_node_ids.get(f.get("path", ""))
            if not src_nid:
                continue
            for imp in f.get("imports", []):
                root = imp.split(".")[0]
                # skip stdlib-ish and known internal names
                if root in _STDLIB_ROOTS or root in internal_stems:
                    continue
                dep_nid = self._s.get_or_create_node(
                    NodeType.DEPENDENCY, root
                )
                self._s.insert_edge(src_nid, dep_nid, EdgeType.DEPENDS_ON)


# ── helpers ────────────────────────────────────────────────────────────────

def _detect_layer(file_path: str) -> str:
    """Map a file path to an architectural layer name."""
    norm = file_path.replace("\\", "/").lower()
    for layer, keywords in LAYER_PATTERNS.items():
        for kw in keywords:
            if f"/{kw}/" in norm or norm.startswith(kw + "/"):
                return layer
    # fallback: tests
    if file_path.lower().endswith("_test.py") or "test" in file_path.lower():
        return "tests"
    return "backend"  # sensible default for unlabelled files


def _detect_service(file_path: str) -> str:
    """Return '<parent>/<service>' string if file is inside a service dir."""
    parts = Path(file_path).parts
    service_parents = {"services", "apps", "packages", "modules", "components"}
    if len(parts) >= 2 and parts[0].lower() in service_parents:
        return f"{parts[0]}/{parts[1]}"
    return ""


def _resolve_import(
    imp: str,
    src_path: str,
    path_index: dict[str, int],
) -> int | None:
    """
    Try to resolve an import string to a known file node id.
    Returns the node id or None.
    """
    # Direct match (e.g. "clockwork.scanner.scanner")
    candidate = path_index.get(imp)
    if candidate:
        return candidate

    # Relative: strip leading dots and try
    stripped = imp.lstrip(".")
    candidate = path_index.get(stripped)
    if candidate:
        return candidate

    # Convert dots to slash path
    slash_form = stripped.replace(".", "/")
    candidate = path_index.get(slash_form)
    if candidate:
        return candidate

    # Try adding .py
    candidate = path_index.get(slash_form + ".py")
    if candidate:
        return candidate

    return None


# Common stdlib root names to skip as external deps
_STDLIB_ROOTS: frozenset[str] = frozenset({
    "os", "sys", "re", "io", "abc", "ast", "csv", "json", "math",
    "time", "copy", "enum", "uuid", "glob", "shutil", "string",
    "struct", "textwrap", "hashlib", "logging", "pathlib", "typing",
    "datetime", "dataclasses", "functools", "itertools", "collections",
    "contextlib", "subprocess", "threading", "multiprocessing",
    "unittest", "tempfile", "zipfile", "tarfile", "sqlite3",
    "urllib", "http", "email", "html", "xml", "base64", "platform",
    "__future__", "builtins", "warnings", "inspect", "importlib",
    "traceback", "argparse", "configparser", "getpass", "socket",
    "ssl", "select", "signal", "ctypes", "weakref", "gc",
})


```

### File: `clockwork/graph/graph_engine.py`

```python
﻿"""
clockwork/graph/graph_engine.py
--------------------------------
Main entry-point for the Knowledge Graph subsystem.

Replaces the previous stub with a full implementation.

Spec §8 pipeline:
    Repository Scan  →  AST Parsing  →  Dependency Detection
    →  Relationship Extraction  →  Graph Construction

Usage::

    engine = GraphEngine(repo_root=Path("."))
    stats  = engine.build()
    q      = engine.query()
    deps   = q.who_depends_on("clockwork/scanner/scanner.py")
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from .builder import GraphBuilder
from .models import GraphStats
from .queries import GraphQueryEngine
from .storage import GraphStorage


class GraphEngine:
    """
    Facade that wires together GraphStorage, GraphBuilder, and
    GraphQueryEngine.

    Parameters
    ----------
    repo_path:
        Root of the repository.  The engine reads
        ``.clockwork/repo_map.json`` and writes to
        ``.clockwork/knowledge_graph.db``.
    """

    def __init__(self, repo_path: Path) -> None:
        self.repo_path    = repo_path.resolve()
        self.clockwork_dir = self.repo_path / ".clockwork"
        self.db_path      = self.clockwork_dir / "knowledge_graph.db"
        self._storage: Optional[GraphStorage] = None

    # ── public API ─────────────────────────────────────────────────────────

    def build(self, repo_map: Optional[dict[str, Any]] = None) -> GraphStats:
        """
        Build (or rebuild) the knowledge graph.

        Parameters
        ----------
        repo_map:
            Pre-loaded repo_map dict.  If omitted, the engine loads
            ``.clockwork/repo_map.json`` automatically.

        Returns
        -------
        GraphStats
            Node/edge counts and elapsed time.
        """
        if repo_map is None:
            repo_map = self._load_repo_map()

        storage = GraphStorage(self.db_path)
        storage.open()
        try:
            storage.initialise(drop_existing=True)
            builder = GraphBuilder(storage)
            stats   = builder.build(repo_map)
            storage.set_meta("built_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            storage.set_meta("stats", json.dumps(stats.to_dict()))
            storage.commit()
        except Exception:
            storage.close()
            raise
        self._storage = storage
        return stats

    def query(self) -> GraphQueryEngine:
        """
        Return a GraphQueryEngine backed by the current database.

        Automatically opens the database if not already open.
        """
        if self._storage is None or self._storage._conn is None:
            storage = GraphStorage(self.db_path)
            storage.open()
            self._storage = storage
        return GraphQueryEngine(self._storage)

    def close(self) -> None:
        """Close the underlying database connection."""
        if self._storage:
            self._storage.close()
            self._storage = None

    def db_exists(self) -> bool:
        """Return True if the knowledge_graph.db file exists."""
        return self.db_path.exists()

    # ── private helpers ────────────────────────────────────────────────────

    def _load_repo_map(self) -> dict[str, Any]:
        repo_map_path = self.clockwork_dir / "repo_map.json"
        if not repo_map_path.exists():
            raise FileNotFoundError(
                f"repo_map.json not found at {repo_map_path}. "
                "Run:  clockwork scan"
            )
        try:
            return json.loads(repo_map_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Cannot parse repo_map.json: {exc}") from exc

    def __enter__(self) -> "GraphEngine":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


```

### File: `clockwork/graph/models.py`

```python
﻿"""
clockwork/graph/models.py
--------------------------
Data models for the Knowledge Graph subsystem.

Defines node types, edge types, and query result containers
used throughout the graph engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Node / Edge type constants ─────────────────────────────────────────────

class NodeType:
    FILE       = "file"
    MODULE     = "module"
    CLASS      = "class"
    FUNCTION   = "function"
    DEPENDENCY = "dependency"
    SERVICE    = "service"
    LANGUAGE   = "language"
    LAYER      = "layer"


class EdgeType:
    IMPORTS       = "imports"
    CALLS         = "calls"
    DEPENDS_ON    = "depends_on"
    BELONGS_TO    = "belongs_to"
    CONTAINS      = "contains"
    PART_OF_LAYER = "part_of_layer"
    PART_OF_SERVICE = "part_of_service"


# ── Architecture layer detection ───────────────────────────────────────────

LAYER_PATTERNS: dict[str, list[str]] = {
    "frontend":       ["frontend", "ui", "client", "web", "static", "public", "views", "templates"],
    "backend":        ["backend", "server", "api", "app", "core", "services", "handlers", "routes"],
    "database":       ["database", "db", "models", "migrations", "schema", "repositories", "dao"],
    "infrastructure": ["infra", "infrastructure", "devops", "deploy", "docker", "k8s", "terraform", "scripts"],
    "tests":          ["tests", "test", "spec", "specs", "__tests__"],
}


# ── Data classes ───────────────────────────────────────────────────────────

@dataclass
class GraphNode:
    """A single node in the knowledge graph."""

    node_id:   int
    kind:      str                        # NodeType constant
    label:     str                        # display name
    file_path: str       = ""
    language:  str       = ""
    layer:     str       = ""
    metadata:  str       = "{}"          # JSON string of extra attributes

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":        self.node_id,
            "kind":      self.kind,
            "label":     self.label,
            "file_path": self.file_path,
            "language":  self.language,
            "layer":     self.layer,
        }


@dataclass
class GraphEdge:
    """A directed edge between two nodes."""

    edge_id:          int
    source_id:        int
    target_id:        int
    relationship:     str          # EdgeType constant
    weight:           float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id":           self.edge_id,
            "source":       self.source_id,
            "target":       self.target_id,
            "relationship": self.relationship,
            "weight":       self.weight,
        }


@dataclass
class GraphStats:
    """Summary statistics returned after a build."""

    node_count:    int = 0
    edge_count:    int = 0
    file_count:    int = 0
    layer_count:   int = 0
    service_count: int = 0
    language_count: int = 0
    elapsed_ms:    float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_count":     self.node_count,
            "edge_count":     self.edge_count,
            "file_count":     self.file_count,
            "layer_count":    self.layer_count,
            "service_count":  self.service_count,
            "language_count": self.language_count,
            "elapsed_ms":     round(self.elapsed_ms, 1),
        }


@dataclass
class QueryResult:
    """Container for graph query results."""

    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


```

### File: `clockwork/graph/queries.py`

```python
﻿"""
clockwork/graph/queries.py
---------------------------
High-level query API for the Knowledge Graph.

Answers the questions defined in spec §13:
  - Which files depend on X?
  - Which modules import Y?
  - Which components belong to layer Z?
  - Which files would be affected if X is deleted?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EdgeType, GraphNode, NodeType, QueryResult
from .storage import GraphStorage


class GraphQueryEngine:
    """
    Provides a clean query API on top of GraphStorage.

    Usage::

        q = GraphQueryEngine(storage)
        dependents = q.who_depends_on("clockwork/scanner/scanner.py")
        layer_files = q.files_in_layer("backend")
    """

    def __init__(self, storage: GraphStorage) -> None:
        self._s = storage

    # ── dependency queries (spec §13, §14) ─────────────────────────────────

    def who_depends_on(self, file_path: str) -> list[GraphNode]:
        """
        Return all files that directly import / depend on *file_path*.

        Used by the Brain before allowing file deletion (spec §14).
        """
        return self._s.fetch_dependents(file_path)

    def dependencies_of(self, file_path: str) -> list[GraphNode]:
        """Return all files / packages that *file_path* imports."""
        return self._s.fetch_dependencies(file_path)

    def is_safe_to_delete(self, file_path: str) -> tuple[bool, list[str]]:
        """
        Returns (safe, [reasons]).

        safe=False means other files import this file — deletion would break them.
        """
        dependents = self.who_depends_on(file_path)
        if dependents:
            reasons = [f"{d.file_path} imports {file_path}" for d in dependents]
            return False, reasons
        return True, []

    # ── layer queries ──────────────────────────────────────────────────────

    def files_in_layer(self, layer: str) -> list[GraphNode]:
        """Return all file nodes tagged to the given architectural layer."""
        return self._s.fetch_nodes(kind=NodeType.FILE, layer=layer)

    def layer_summary(self) -> dict[str, int]:
        """Return {layer_name: file_count} for all layers."""
        nodes = self._s.fetch_nodes(kind=NodeType.FILE, limit=10_000)
        summary: dict[str, int] = {}
        for node in nodes:
            lyr = node.layer or "unknown"
            summary[lyr] = summary.get(lyr, 0) + 1
        return summary

    # ── language queries ───────────────────────────────────────────────────

    def files_by_language(self, language: str) -> list[GraphNode]:
        """Return all file nodes for the given language."""
        if self._s._conn is None:
            raise RuntimeError("GraphStorage is not open. Call storage.open() before querying.")
        rows = self._s._conn.execute(
            "SELECT * FROM nodes WHERE kind=? AND language=? LIMIT 500",
            (NodeType.FILE, language),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    def language_counts(self) -> dict[str, int]:
        """Return {language: file_count}."""
        assert self._s._conn
        rows = self._s._conn.execute(
            "SELECT language, COUNT(*) AS c FROM nodes "
            "WHERE kind=? AND language != '' GROUP BY language",
            (NodeType.FILE,),
        ).fetchall()
        return {r["language"]: r["c"] for r in rows}

    # ── import queries ─────────────────────────────────────────────────────

    def files_importing(self, module_name: str) -> list[GraphNode]:
        """
        Return files that import *module_name* (exact label match on
        DEPENDENCY or FILE nodes, following depends_on / imports edges).
        """
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT src.*
            FROM nodes src
            JOIN edges e  ON e.source_id = src.id
            JOIN nodes tgt ON tgt.id = e.target_id
            WHERE tgt.label = ?
              AND e.relationship IN ('imports','depends_on')
            LIMIT 200
            """,
            (module_name,),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    # ── service queries ────────────────────────────────────────────────────

    def files_in_service(self, service_path: str) -> list[GraphNode]:
        """Return all files belonging to a service node."""
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT f.*
            FROM nodes f
            JOIN edges e ON e.source_id = f.id
            JOIN nodes s ON s.id = e.target_id
            WHERE s.kind=? AND s.label=?
              AND e.relationship=?
            LIMIT 200
            """,
            (NodeType.SERVICE, service_path, EdgeType.PART_OF_SERVICE),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    def services(self) -> list[GraphNode]:
        """Return all service nodes."""
        return self._s.fetch_nodes(kind=NodeType.SERVICE)

    # ── class / function queries ───────────────────────────────────────────

    def symbols_in_file(self, file_path: str) -> list[GraphNode]:
        """Return all class/function nodes contained in a file."""
        assert self._s._conn
        rows = self._s._conn.execute(
            """
            SELECT DISTINCT sym.*
            FROM nodes sym
            JOIN edges e ON e.source_id = sym.id
            JOIN nodes f ON f.id = e.target_id
            WHERE f.file_path=?
              AND e.relationship=?
              AND sym.kind IN (?,?)
            LIMIT 200
            """,
            (file_path, EdgeType.CONTAINS, NodeType.CLASS, NodeType.FUNCTION),
        ).fetchall()
        from .storage import _row_to_node
        return [_row_to_node(r) for r in rows]

    # ── full graph export ──────────────────────────────────────────────────

    def export(self) -> dict[str, Any]:
        """Export the entire graph as a dict (for JSON serialisation)."""
        return self._s.export_json()

    def stats(self) -> dict[str, Any]:
        """Return per-kind node counts and edge count."""
        return {
            "nodes_by_kind": self._s.count_nodes_by_kind(),
            "total_nodes":   self._s.count_nodes(),
            "total_edges":   self._s.count_edges(),
            "layers":        self.layer_summary(),
            "languages":     self.language_counts(),
        }


```

### File: `clockwork/graph/storage.py`

```python
﻿"""
clockwork/graph/storage.py
---------------------------
SQLite persistence layer for the Knowledge Graph.

Owns schema creation, node/edge insertion, and raw SQL queries.
All higher-level logic lives in graph_engine.py.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from .models import GraphEdge, GraphNode, GraphStats


# ── DDL ────────────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS graph_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    kind      TEXT    NOT NULL,
    label     TEXT    NOT NULL,
    file_path TEXT    NOT NULL DEFAULT '',
    language  TEXT    NOT NULL DEFAULT '',
    layer     TEXT    NOT NULL DEFAULT '',
    metadata  TEXT    NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS edges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id    INTEGER NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relationship TEXT    NOT NULL,
    weight       REAL    NOT NULL DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_nodes_kind      ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_label     ON nodes(label);
CREATE INDEX IF NOT EXISTS idx_nodes_layer     ON nodes(layer);
CREATE INDEX IF NOT EXISTS idx_nodes_file_path ON nodes(file_path);
CREATE INDEX IF NOT EXISTS idx_edges_source    ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target    ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_rel       ON edges(relationship);
"""

_DROP_SQL = """
DROP TABLE IF EXISTS edges;
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS graph_meta;
"""


class GraphStorage:
    """
    Manages the SQLite database that backs the knowledge graph.

    Usage::

        storage = GraphStorage(db_path)
        storage.initialise(drop_existing=True)
        nid = storage.insert_node("file", "app.py", file_path="app.py")
        storage.commit()
        storage.close()
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    def open(self) -> None:
        """Open (or create) the database file."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # FK cascades enabled below after connect
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        """Commit and close the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def __enter__(self) -> "GraphStorage":
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── schema ─────────────────────────────────────────────────────────────

    def initialise(self, drop_existing: bool = False) -> None:
        """Create tables (optionally dropping existing ones first)."""
        assert self._conn, "Call open() first"
        if drop_existing:
            self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ── node operations ────────────────────────────────────────────────────

    def insert_node(
        self,
        kind:      str,
        label:     str,
        file_path: str = "",
        language:  str = "",
        layer:     str = "",
        metadata:  Optional[dict[str, Any]] = None,
    ) -> int:
        """Insert a node and return its row-id."""
        assert self._conn
        cur = self._conn.execute(
            "INSERT INTO nodes (kind, label, file_path, language, layer, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, label, file_path, language, layer,
             json.dumps(metadata or {})),
        )
        return cur.lastrowid  # type: ignore[return-value]

    def get_or_create_node(
        self,
        kind:  str,
        label: str,
        **kwargs: Any,
    ) -> int:
        """Return existing node id if (kind, label) exists, else insert."""
        assert self._conn
        row = self._conn.execute(
            "SELECT id FROM nodes WHERE kind = ? AND label = ?",
            (kind, label),
        ).fetchone()
        if row:
            return int(row["id"])
        return self.insert_node(kind, label, **kwargs)

    def node_exists(self, kind: str, label: str) -> bool:
        assert self._conn
        row = self._conn.execute(
            "SELECT 1 FROM nodes WHERE kind=? AND label=?", (kind, label)
        ).fetchone()
        return row is not None

    # ── edge operations ────────────────────────────────────────────────────

    def insert_edge(
        self,
        source_id:    int,
        target_id:    int,
        relationship: str,
        weight:       float = 1.0,
    ) -> int:
        """Insert an edge (deduplicates by source/target/relationship)."""
        assert self._conn
        existing = self._conn.execute(
            "SELECT id FROM edges WHERE source_id=? AND target_id=? AND relationship=?",
            (source_id, target_id, relationship),
        ).fetchone()
        if existing:
            return int(existing["id"])
        cur = self._conn.execute(
            "INSERT INTO edges (source_id, target_id, relationship, weight) "
            "VALUES (?, ?, ?, ?)",
            (source_id, target_id, relationship, weight),
        )
        return cur.lastrowid  # type: ignore[return-value]

    # ── metadata ───────────────────────────────────────────────────────────

    def set_meta(self, key: str, value: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT OR REPLACE INTO graph_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_meta(self, key: str) -> Optional[str]:
        assert self._conn
        row = self._conn.execute(
            "SELECT value FROM graph_meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    # ── read queries ───────────────────────────────────────────────────────

    def fetch_nodes(
        self,
        kind:  Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 500,
    ) -> list[GraphNode]:
        assert self._conn
        sql   = "SELECT * FROM nodes WHERE 1=1"
        params: list[Any] = []
        if kind:
            sql += " AND kind = ?"
            params.append(kind)
        if layer:
            sql += " AND layer = ?"
            params.append(layer)
        sql += f" LIMIT {limit}"
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_node(r) for r in rows]

    def fetch_edges(
        self,
        relationship: Optional[str] = None,
        limit: int = 2000,
    ) -> list[GraphEdge]:
        assert self._conn
        if relationship:
            rows = self._conn.execute(
                "SELECT * FROM edges WHERE relationship=? LIMIT ?",
                (relationship, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM edges LIMIT ?", (limit,)
            ).fetchall()
        return [_row_to_edge(r) for r in rows]

    def fetch_dependents(self, file_path: str) -> list[GraphNode]:
        """Return all nodes that import/depend on the given file path."""
        assert self._conn
        rows = self._conn.execute(
            """
            SELECT DISTINCT n.*
            FROM nodes n
            JOIN edges e ON e.source_id = n.id
            JOIN nodes t ON t.id = e.target_id
            WHERE t.file_path = ?
              AND e.relationship IN ('imports', 'depends_on')
            LIMIT 200
            """,
            (file_path,),
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def fetch_dependencies(self, file_path: str) -> list[GraphNode]:
        """Return all nodes that the given file imports/depends on."""
        assert self._conn
        rows = self._conn.execute(
            """
            SELECT DISTINCT t.*
            FROM nodes n
            JOIN edges e ON e.source_id = n.id
            JOIN nodes t ON t.id = e.target_id
            WHERE n.file_path = ?
              AND e.relationship IN ('imports', 'depends_on')
            LIMIT 200
            """,
            (file_path,),
        ).fetchall()
        return [_row_to_node(r) for r in rows]

    def count_nodes(self) -> int:
        assert self._conn
        return int(self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])

    def count_edges(self) -> int:
        assert self._conn
        return int(self._conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0])

    def count_nodes_by_kind(self) -> dict[str, int]:
        assert self._conn
        rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS c FROM nodes GROUP BY kind"
        ).fetchall()
        return {r["kind"]: r["c"] for r in rows}

    def export_json(self) -> dict[str, Any]:
        """Export the entire graph as a JSON-serialisable dict."""
        assert self._conn
        nodes = [_row_to_node(r).to_dict() for r in
                 self._conn.execute("SELECT * FROM nodes").fetchall()]
        edges = [_row_to_edge(r).to_dict() for r in
                 self._conn.execute("SELECT * FROM edges").fetchall()]
        return {"nodes": nodes, "edges": edges}


# ── helpers ────────────────────────────────────────────────────────────────

def _row_to_node(row: sqlite3.Row) -> GraphNode:
    return GraphNode(
        node_id=row["id"],
        kind=row["kind"],
        label=row["label"],
        file_path=row["file_path"],
        language=row["language"],
        layer=row["layer"],
        metadata=row["metadata"],
    )


def _row_to_edge(row: sqlite3.Row) -> GraphEdge:
    return GraphEdge(
        edge_id=row["id"],
        source_id=row["source_id"],
        target_id=row["target_id"],
        relationship=row["relationship"],
        weight=row["weight"],
    )


```

### File: `clockwork/handoff/__init__.py`

```python
﻿"""
clockwork.handoff
-----------------
Agent Handoff subsystem for the Clockwork project.

Public surface::

    from clockwork.handoff import HandoffEngine
    engine = HandoffEngine(repo_root=Path("."))
    success, msg = engine.run(target_agent="Claude")
"""

from .engine import HandoffEngine
from .models import HandoffData, HandoffLogEntry
from .validator import ValidationResult, validate_before_handoff

__all__ = [
    "HandoffEngine",
    "HandoffData",
    "HandoffLogEntry",
    "ValidationResult",
    "validate_before_handoff",
]
```

### File: `clockwork/handoff/aggregator.py`

```python
﻿"""
Clockwork — Agent Handoff System
aggregator.py: Collects handoff data from all subsystem sources.

Sources:
  - .clockwork/context.yaml      (Context Engine)
  - .clockwork/repo_map.json     (Repository Scanner)
  - .clockwork/rules.md          (Rule Engine reference)
  - .clockwork/tasks.json        (Task Tracker)
  - .clockwork/skills.json       (Skill Detection)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from .models import HandoffData

_SENSITIVE_PATTERNS: List[str] = [
    ".env", "credentials", "secret", "private_key", "api_key", "token",
]


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:
        return {}


def _load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _is_sensitive(key: str) -> bool:
    lower = key.lower()
    return any(pattern in lower for pattern in _SENSITIVE_PATTERNS)


def _sanitise(data: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in data.items() if not _is_sensitive(k)}


def aggregate_handoff_data(clockwork_dir: Path) -> HandoffData:
    """
    Read all Clockwork runtime files and produce a HandoffData object.

    Args:
        clockwork_dir: Path to the .clockwork directory.

    Returns:
        Populated HandoffData ready for serialisation.
    """
    context = _sanitise(_load_yaml(clockwork_dir / "context.yaml"))
    repo_map = _load_json(clockwork_dir / "repo_map.json")
    tasks_raw = _load_json(clockwork_dir / "tasks.json")
    skills_raw = _load_json(clockwork_dir / "skills.json")

    project_name: str = context.get("project_name", "unknown_project")
    architecture: str = context.get("architecture", "unknown")
    current_summary: str = context.get("current_summary", "No summary available.")

    next_task: str = "No pending tasks."
    if isinstance(tasks_raw, list) and tasks_raw:
        for task in tasks_raw:
            if isinstance(task, dict) and task.get("status", "open") != "done":
                next_task = task.get("description", str(task))
                break
    elif isinstance(tasks_raw, dict):
        next_task = tasks_raw.get("next_task", next_task)

    skills: List[str] = []
    if isinstance(skills_raw, list):
        skills = [str(s) for s in skills_raw]
    elif isinstance(skills_raw, dict):
        skills = skills_raw.get("required", [])

    languages: List[str] = []
    if isinstance(repo_map, dict):
        raw_langs = repo_map.get("languages", [])
        if isinstance(raw_langs, dict):
            languages = list(raw_langs.keys())
        elif isinstance(raw_langs, list):
            languages = raw_langs
        if not skills:
            skills = languages

    frameworks: List[str] = []
    if isinstance(repo_map, dict):
        frameworks = repo_map.get("frameworks", [])

    task_state: str = context.get("task_state", "in_progress")

    return HandoffData(
        project=project_name,
        architecture=architecture,
        current_summary=current_summary,
        next_task=next_task,
        skills_required=skills,
        rules_reference=".clockwork/rules.md",
        frameworks=frameworks,
        languages=languages,
        task_state=task_state,
    )
```

### File: `clockwork/handoff/brief_generator.py`

```python
﻿"""
Clockwork — Agent Handoff System
brief_generator.py: Renders the human-readable next_agent_brief.md.
"""

from __future__ import annotations

from .models import HandoffData


_TEMPLATE = """\
# Clockwork Agent Handoff Brief

---

## Project Summary

{current_summary}

---

## Next Task

{next_task}

---

## Skills Required

{skills_list}

---

## Frameworks & Languages

**Frameworks:** {frameworks}
**Languages:** {languages}

---

## Architecture

{architecture}

---

## Task State

{task_state}

---

## Rules

Follow repository rules defined in `{rules_reference}`.

---

*Generated by Clockwork on {generated_at}*
"""


def render_brief(data: HandoffData) -> str:
    """
    Render a Markdown agent brief from HandoffData.

    Args:
        data: Populated HandoffData instance.

    Returns:
        Markdown string ready to be written to next_agent_brief.md.
    """
    skills_list = "\n".join(f"- {s}" for s in data.skills_required) or "- Not specified"
    frameworks = ", ".join(data.frameworks) or "Not detected"
    languages = ", ".join(data.languages) or "Not detected"

    return _TEMPLATE.format(
        current_summary=data.current_summary,
        next_task=data.next_task,
        skills_list=skills_list,
        frameworks=frameworks,
        languages=languages,
        architecture=data.architecture,
        task_state=data.task_state,
        rules_reference=data.rules_reference,
        generated_at=data.generated_at,
    )
```

### File: `clockwork/handoff/engine.py`

```python
﻿"""
Clockwork — Agent Handoff System
engine.py: Orchestrates the complete handoff generation pipeline.

Pipeline:
  1. Validate repository state
  2. Aggregate data from all subsystems
  3. Render human-readable brief (next_agent_brief.md)
  4. Write machine-readable JSON (handoff.json)
  5. Log the handoff event
"""

from __future__ import annotations

import json
from pathlib import Path

from .aggregator import aggregate_handoff_data
from .brief_generator import render_brief
from .logger import log_handoff
from .models import HandoffData
from .validator import ValidationResult, validate_before_handoff


class HandoffEngine:
    """
    Main entry-point for the Agent Handoff subsystem.

    Usage::

        engine = HandoffEngine(repo_root=Path("."))
        result = engine.run(target_agent="Claude")
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.handoff_dir = self.clockwork_dir / "handoff"

    def run(self, target_agent: str = "unknown") -> tuple[bool, str]:
        """
        Execute the full handoff pipeline.

        Args:
            target_agent: Label for the agent receiving the handoff.

        Returns:
            (success: bool, message: str)
        """
        validation: ValidationResult = validate_before_handoff(self.clockwork_dir)
        if not validation.passed:
            reasons = "\n".join(f"  * {e}" for e in validation.errors)
            return False, f"Handoff blocked - validation failed:\n{reasons}"

        data: HandoffData = aggregate_handoff_data(self.clockwork_dir)

        self.handoff_dir.mkdir(parents=True, exist_ok=True)

        brief_md = render_brief(data)
        brief_path = self.handoff_dir / "next_agent_brief.md"
        brief_path.write_text(brief_md, encoding="utf-8")

        handoff_path = self.handoff_dir / "handoff.json"
        handoff_path.write_text(
            json.dumps(data.to_dict(), indent=2), encoding="utf-8"
        )

        log_handoff(self.clockwork_dir, data, target_agent=target_agent)

        warn_text = ""
        if validation.warnings:
            warn_lines = "\n".join(f"  ! {w}" for w in validation.warnings)
            warn_text = f"\nWarnings:\n{warn_lines}"

        return True, (
            f"Handoff generated successfully.\n"
            f"  -> {brief_path.relative_to(self.repo_root)}\n"
            f"  -> {handoff_path.relative_to(self.repo_root)}"
            f"{warn_text}"
        )
```

### File: `clockwork/handoff/logger.py`

```python
﻿"""
Clockwork — Agent Handoff System
logger.py: Appends handoff events to .clockwork/handoff_log.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import HandoffData


def log_handoff(clockwork_dir: Path, data: HandoffData, target_agent: str = "unknown") -> None:
    """
    Append a handoff log entry to .clockwork/handoff_log.json.

    Args:
        clockwork_dir: Path to the .clockwork directory.
        data:          The HandoffData that was generated.
        target_agent:  Name/label of the receiving agent (e.g. "Claude").
    """
    log_path = clockwork_dir / "handoff_log.json"

    entries: list = []
    if log_path.exists():
        try:
            entries = json.loads(log_path.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = [entries]
        except (json.JSONDecodeError, OSError):
            entries = []

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "handoff_to": target_agent,
        "project": data.project,
        "next_task": data.next_task,
        "task_state": data.task_state,
    }
    entries.append(entry)

    log_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
```

### File: `clockwork/handoff/models.py`

```python
﻿"""
Clockwork — Agent Handoff System
models.py: Data models for handoff structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class HandoffData:
    """
    Complete machine-readable handoff payload.

    Aggregated from Context Engine, Repository Scanner,
    Rule Engine, and Brain Manager.
    """

    project: str
    architecture: str
    current_summary: str
    next_task: str
    skills_required: List[str]
    rules_reference: str
    frameworks: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    task_state: str = "in_progress"
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialise to plain dictionary for JSON output."""
        return {
            "project": self.project,
            "architecture": self.architecture,
            "current_summary": self.current_summary,
            "next_task": self.next_task,
            "skills_required": self.skills_required,
            "frameworks": self.frameworks,
            "languages": self.languages,
            "task_state": self.task_state,
            "rules_reference": self.rules_reference,
            "generated_at": self.generated_at,
        }


@dataclass
class HandoffLogEntry:
    """Single entry written to handoff_log.json after each handoff."""

    timestamp: str
    handoff_to: str
    next_task: str
    project: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "handoff_to": self.handoff_to,
            "next_task": self.next_task,
            "project": self.project,
        }
```

### File: `clockwork/handoff/validator.py`

```python
﻿"""
Clockwork — Agent Handoff System
validator.py: Pre-handoff repository integrity validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ValidationResult:
    """Result of a pre-handoff validation pass."""

    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_before_handoff(clockwork_dir: Path) -> ValidationResult:
    """
    Run all pre-handoff checks against the .clockwork directory.

    Args:
        clockwork_dir: Path to the .clockwork directory.

    Returns:
        ValidationResult with pass/fail status and diagnostic messages.
    """
    result = ValidationResult(passed=True)

    if not clockwork_dir.exists():
        result.add_error(
            "Clockwork is not initialised. Run `clockwork init` first."
        )
        return result

    context_path = clockwork_dir / "context.yaml"
    if not context_path.exists():
        result.add_error(
            "context.yaml is missing. Run `clockwork update` to regenerate."
        )

    repo_map_path = clockwork_dir / "repo_map.json"
    if not repo_map_path.exists():
        result.add_warning(
            "repo_map.json not found. Run `clockwork scan` for richer handoff data."
        )
    else:
        try:
            content = json.loads(repo_map_path.read_text(encoding="utf-8"))
            if not content:
                result.add_warning("repo_map.json is empty.")
        except json.JSONDecodeError:
            result.add_error("repo_map.json is malformed JSON.")

    rules_path = clockwork_dir / "rules.md"
    if not rules_path.exists():
        result.add_warning(
            "rules.md not found. Handoff will reference a missing rules file."
        )

    log_path = clockwork_dir / "validation_log.json"
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text(encoding="utf-8"))
            entries = log if isinstance(log, list) else [log]
            recent = entries[-1] if entries else {}
            if recent.get("status") == "failed":
                result.add_error(
                    f"Last validation failed: {recent.get('reason', 'unknown reason')}. "
                    "Resolve before generating a handoff."
                )
        except (json.JSONDecodeError, KeyError):
            result.add_warning("Could not read validation_log.json.")

    return result
```

### File: `clockwork/index/__init__.py`

```python
﻿"""
clockwork/index/__init__.py
----------------------------
Live Context Index subsystem.

Turns Clockwork into a real-time repository intelligence system
by watching filesystem events and updating the index, graph, and
context engine incrementally — without full rescans.

Public API::

    from clockwork.index import LiveContextIndex

    engine = LiveContextIndex(repo_root=Path("."))
    stats  = engine.build()       # initial full index
    engine.watch()                # start real-time watching
    engine.stop()                 # stop watching

CLI commands added:
    clockwork index   — build / refresh the index
    clockwork repair  — wipe and rebuild from scratch
    clockwork watch   — start real-time monitoring
"""

from clockwork.index.index_engine import LiveContextIndex
from clockwork.index.models import (
    ChangeEvent,
    EventType,
    IndexEntry,
    IndexStats,
)

__all__ = [
    "LiveContextIndex",
    "ChangeEvent",
    "EventType",
    "IndexEntry",
    "IndexStats",
]


```

### File: `clockwork/index/incremental_scanner.py`

```python
﻿"""
clockwork/index/incremental_scanner.py
----------------------------------------
Incremental file scanner for the Live Context Index.

Instead of rescanning the entire repository, this module scans
only a single changed file and returns its metadata — feeding
the index storage and graph updater.

Spec §6 pipeline:
    File Modified → Incremental Parser → Dependency Update → Graph Update
"""

from __future__ import annotations

import ast
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from .models import IndexEntry, compute_file_hash


# ── Language detection ─────────────────────────────────────────────────────

_EXT_LANGUAGE: dict[str, str] = {
    ".py":   "Python",   ".js":  "JavaScript", ".ts":  "TypeScript",
    ".jsx":  "JavaScript", ".tsx": "TypeScript", ".go":  "Go",
    ".rs":   "Rust",     ".java": "Java",       ".rb":  "Ruby",
    ".php":  "PHP",      ".cs":   "C#",         ".cpp": "C++",
    ".c":    "C",        ".h":    "C/C++ Header",
    ".yaml": "YAML",     ".yml":  "YAML",       ".json": "JSON",
    ".md":   "Markdown", ".toml": "TOML",       ".sh":  "Shell",
    ".sql":  "SQL",
}

_MODULE_TYPE_RULES = [
    (lambda p: "test" in p.lower() or p.endswith("_test.py"), "test"),
    (lambda p: p.endswith((".yaml", ".yml", ".toml", ".json", ".cfg", ".ini")), "config"),
    (lambda p: p.endswith((".py", ".js", ".ts", ".go", ".rs", ".java")), "source"),
]

_LAYER_PATTERNS: dict[str, list[str]] = {
    "frontend":       ["frontend", "ui", "client", "web", "static", "public"],
    "backend":        ["backend", "server", "api", "app", "core", "services"],
    "database":       ["database", "db", "models", "migrations", "schema"],
    "infrastructure": ["infra", "infrastructure", "devops", "docker", "scripts"],
    "tests":          ["tests", "test", "spec"],
}

_SENSITIVE = {".env", "credentials.json", "secrets.json", ".netrc", "id_rsa"}


class IncrementalScanner:
    """
    Scans a single file and returns an IndexEntry.

    All analysis is purely static — no code is executed (spec §16).
    """

    def scan_file(self, file_path: str, repo_root: str) -> Optional[IndexEntry]:
        """
        Scan one file and return an IndexEntry, or None if the file
        should be skipped (binary, sensitive, or non-existent).
        """
        abs_path = Path(file_path)
        if not abs_path.exists() or not abs_path.is_file():
            return None

        filename = abs_path.name
        if filename in _SENSITIVE or filename.startswith(".env"):
            return None

        # relative path for storage
        try:
            rel_path = str(abs_path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            rel_path = str(abs_path).replace("\\", "/")

        ext      = abs_path.suffix.lower()
        language = _EXT_LANGUAGE.get(ext, "Other")
        mtime    = abs_path.stat().st_mtime
        size     = abs_path.stat().st_size
        fhash    = compute_file_hash(file_path)
        layer    = _detect_layer(rel_path)
        mod_type = _detect_module_type(rel_path)
        deps     = self._extract_dependencies(abs_path, language)

        return IndexEntry(
            file_path=rel_path,
            last_modified=mtime,
            file_hash=fhash,
            size_bytes=size,
            language=language,
            module_type=mod_type,
            dependencies=json.dumps(deps),
            layer=layer,
        )

    # ── dependency extraction ──────────────────────────────────────────────

    def _extract_dependencies(self, path: Path, language: str) -> list[str]:
        """Extract import strings from a source file (static only)."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        if language == "Python":
            return self._python_imports(content)
        if language in ("JavaScript", "TypeScript"):
            return self._js_imports(content)
        if language == "Go":
            return self._go_imports(content)
        return []

    def _python_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
        except SyntaxError:
            # fallback: regex
            for m in re.finditer(r"^\s*(?:import|from)\s+([\w.]+)", source, re.MULTILINE):
                imports.append(m.group(1))
        return list(dict.fromkeys(imports))  # deduplicate, preserve order

    def _js_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        for m in re.finditer(
            r"""(?:import|require)\s*[\(\s]['"]([^'"]+)['"]""", source
        ):
            imports.append(m.group(1))
        return list(dict.fromkeys(imports))

    def _go_imports(self, source: str) -> list[str]:
        imports: list[str] = []
        block = re.search(r'import\s*\(([^)]+)\)', source, re.DOTALL)
        if block:
            for m in re.finditer(r'"([^"]+)"', block.group(1)):
                imports.append(m.group(1))
        for m in re.finditer(r'^\s*import\s+"([^"]+)"', source, re.MULTILINE):
            imports.append(m.group(1))
        return list(dict.fromkeys(imports))


# ── helpers ────────────────────────────────────────────────────────────────

def _detect_layer(rel_path: str) -> str:
    norm = rel_path.lower()
    for layer, keywords in _LAYER_PATTERNS.items():
        for kw in keywords:
            if f"/{kw}/" in norm or norm.startswith(kw + "/"):
                return layer
    if "test" in norm:
        return "tests"
    return "backend"


def _detect_module_type(rel_path: str) -> str:
    for rule, kind in _MODULE_TYPE_RULES:
        if rule(rel_path):
            return kind
    return "other"


```

### File: `clockwork/index/index_engine.py`

```python
﻿"""
clockwork/index/index_engine.py
--------------------------------
Main engine for the Live Context Index subsystem.

Orchestrates:
  - IndexStorage   (.clockwork/index.db)
  - IncrementalScanner  (single-file analysis)
  - RepositoryWatcher   (watchdog filesystem events)
  - Graph + Context sync after each change

Spec §3 pipeline:
    Repository Filesystem
        ↓
    Filesystem Watcher
        ↓
    Change Event Queue
        ↓
    Incremental Analysis
        ↓
    Knowledge Graph Update
        ↓
    Context Engine Sync
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from .incremental_scanner import IncrementalScanner
from .models import ChangeEvent, EventType, IndexEntry, IndexStats, compute_file_hash
from .storage import IndexStorage
from .watcher import RepositoryWatcher

logger = logging.getLogger("clockwork.index")


class LiveContextIndex:
    """
    The primary entry point for module 10.

    Responsibilities:
      1. Build / repair the full index from the current repository state.
      2. Watch for file changes and update the index incrementally.
      3. Sync the Knowledge Graph and Context Engine after each change.

    Usage::

        engine = LiveContextIndex(repo_root=Path("."))
        stats  = engine.build()          # full initial index
        engine.watch()                   # start real-time watching
        # ... later ...
        engine.stop()
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.db_path       = self.clockwork_dir / "index.db"
        self._storage      = IndexStorage(self.db_path)
        self._scanner      = IncrementalScanner()
        self._watcher: Optional[RepositoryWatcher] = None
        self._watching     = False

    # ── full index build ───────────────────────────────────────────────────

    def build(self, drop_existing: bool = False) -> IndexStats:
        """
        Walk the entire repository and populate index.db.

        Skips files whose hash hasn't changed (spec §12).
        Used by `clockwork index` and `clockwork repair`.
        """
        t0 = time.perf_counter()

        self._storage.open()
        self._storage.initialise(drop_existing=drop_existing)

        total = indexed = skipped = 0

        for root_dir, dirs, files in os.walk(str(self.repo_root)):
            # prune ignored directories in-place
            dirs[:] = [
                d for d in dirs
                if d not in _IGNORE_DIRS and not d.startswith(".")
            ]

            for fname in files:
                abs_path = os.path.join(root_dir, fname)
                total += 1

                # fast hash check before full scan
                try:
                    mtime    = os.path.getmtime(abs_path)
                    fhash    = compute_file_hash(abs_path)
                except OSError:
                    skipped += 1
                    continue

                if not self._storage.has_changed(
                    _rel(abs_path, self.repo_root), mtime, fhash
                ):
                    skipped += 1
                    continue

                entry = self._scanner.scan_file(abs_path, str(self.repo_root))
                if entry is None:
                    skipped += 1
                    continue

                self._storage.upsert(entry)
                indexed += 1

        self._storage.set_meta("built_at", time.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self._storage.commit()
        self._storage.close()

        elapsed = (time.perf_counter() - t0) * 1000
        return IndexStats(
            total_files=total,
            indexed_files=indexed,
            skipped_files=skipped,
            elapsed_ms=elapsed,
        )

    # ── real-time watching ─────────────────────────────────────────────────

    def watch(self, debounce_s: float = 0.2) -> bool:
        """
        Start real-time filesystem watching.

        Returns True if watchdog is available, False if not installed
        (index will still work via manual `clockwork index` calls).
        """
        if self._watching:
            return True

        self._storage.open()
        self._storage.initialise()

        self._watcher = RepositoryWatcher(
            repo_root=self.repo_root,
            on_change=self._handle_event,
            debounce_s=debounce_s,
        )
        try:
            result = self._watcher.start()
        except Exception:
            self._storage.close()
            self._watcher = None
            raise
        self._watching = True
        return result

    def stop(self) -> None:
        """Stop watching and close the database."""
        self._watching = False
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
        self._storage.close()

    def is_watching(self) -> bool:
        return self._watching and (
            self._watcher is not None and self._watcher.is_watching()
        )

    # ── single-file update ─────────────────────────────────────────────────

    def update_file(self, file_path: str) -> Optional[IndexEntry]:
        """
        Manually trigger an incremental update for one file.
        Useful when watchdog is not available.
        """
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
            self._storage.initialise()

        entry = self._scanner.scan_file(file_path, str(self.repo_root))
        if entry:
            self._storage.upsert(entry)
            self._storage.commit()
            self._sync_graph(entry)
            self._sync_context(entry)
            logger.debug("Updated index entry for %s", file_path)
        else:
            # file deleted or unreadable
            rel = _rel(file_path, self.repo_root)
            self._storage.delete(rel)
            self._storage.commit()

        if not was_open:
            self._storage.close()

        return entry

    # ── repair ────────────────────────────────────────────────────────────

    def repair(self) -> IndexStats:
        """
        Wipe the index and rebuild it from scratch.
        Implements `clockwork repair` (spec §14).
        """
        logger.info("Repairing index — wiping and rebuilding...")
        return self.build(drop_existing=True)

    # ── query helpers ──────────────────────────────────────────────────────

    def get_entry(self, file_path: str) -> Optional[IndexEntry]:
        """Return the cached IndexEntry for a file, or None."""
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        entry = self._storage.get(file_path)
        if not was_open:
            self._storage.close()
        return entry

    def all_entries(self) -> list[IndexEntry]:
        """Return all IndexEntry records."""
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        entries = self._storage.all_entries()
        if not was_open:
            self._storage.close()
        return entries

    def count(self) -> int:
        was_open = self._storage._conn is not None
        if not was_open:
            self._storage.open()
        n = self._storage.count()
        if not was_open:
            self._storage.close()
        return n

    # ── internal event handler ─────────────────────────────────────────────

    def _handle_event(self, event: ChangeEvent) -> None:
        """
        Called by DebouncedProcessor for each debounced filesystem event.
        Implements spec §6 (incremental scanner) and §7 (graph update).
        """
        logger.info("Event: %s %s", event.event_type, event.file_path)

        if event.event_type == EventType.DELETED:
            rel = _rel(event.file_path, self.repo_root)
            self._storage.delete(rel)
            self._storage.commit()
            return

        if event.event_type == EventType.RENAMED and event.src_path:
            old_rel = _rel(event.src_path, self.repo_root)
            self._storage.delete(old_rel)

        entry = self._scanner.scan_file(event.file_path, str(self.repo_root))
        if entry is None:
            return

        # check if content actually changed (spec §12)
        if not self._storage.has_changed(entry.file_path, entry.last_modified, entry.file_hash):
            logger.debug("No meaningful change in %s — skipping", entry.file_path)
            return

        self._storage.upsert(entry)
        self._storage.commit()

        # downstream sync
        self._sync_graph(entry)
        self._sync_context(entry)

    # ── downstream sync ────────────────────────────────────────────────────

    def _sync_graph(self, entry: IndexEntry) -> None:
        """
        Update the Knowledge Graph for the changed file (spec §7).

        Steps: remove old node relationships → parse new file → insert nodes.
        Gracefully skips if knowledge_graph.db doesn't exist yet.
        """
        db_path = self.clockwork_dir / "knowledge_graph.db"
        if not db_path.exists():
            return

        try:
            from clockwork.graph.storage import GraphStorage
            from clockwork.graph.models import NodeType, EdgeType
            from clockwork.graph.builder import _detect_layer

            storage = GraphStorage(db_path)
            storage.open()

            # remove old file node + its edges (cascade delete handles edges)
            if storage._conn is None:
                raise RuntimeError("GraphStorage connection is None inside _sync_graph")
            storage._conn.execute(
                "DELETE FROM nodes WHERE kind=? AND file_path=?",
                (NodeType.FILE, entry.file_path),
            )

            # insert fresh file node
            layer = entry.layer or _detect_layer(entry.file_path)
            nid = storage.insert_node(
                kind=NodeType.FILE,
                label=Path(entry.file_path).name,
                file_path=entry.file_path,
                language=entry.language,
                layer=layer,
            )

            # re-add dependency edges for known internal files
            deps = json.loads(entry.dependencies)
            for imp in deps:
                slash = imp.replace(".", "/")
                for ext in (".py", ""):
                    row = storage._conn.execute(
                        "SELECT id FROM nodes WHERE kind=? AND (file_path=? OR file_path=?)",
                        (NodeType.FILE, slash + ext, slash),
                    ).fetchone()
                    if row:
                        storage.insert_edge(nid, row["id"], EdgeType.IMPORTS)
                        break

            storage.commit()
            storage.close()
            logger.debug("Graph synced for %s", entry.file_path)

        except Exception as exc:
            logger.warning("Graph sync failed for %s: %s", entry.file_path, exc)

    def _sync_context(self, entry: IndexEntry) -> None:
        """
        Notify the Context Engine of the change (spec §8).

        Records the changed file in context.yaml recent_changes.
        Gracefully skips if context.yaml doesn't exist yet.
        """
        context_path = self.clockwork_dir / "context.yaml"
        if not context_path.exists():
            return

        try:
            from clockwork.context import ContextEngine
            engine = ContextEngine(self.clockwork_dir)
            engine.record_change(
                description=f"File changed: {entry.file_path}",
                changed_files=[entry.file_path],
                agent="clockwork.index",
                change_type="file_change",
            )
            logger.debug("Context synced for %s", entry.file_path)
        except Exception as exc:
            logger.warning("Context sync failed for %s: %s", entry.file_path, exc)


# ── helpers ────────────────────────────────────────────────────────────────

_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
    "eggs",
}


def _rel(abs_path: str, repo_root: Path) -> str:
    """Return a repo-relative forward-slash path."""
    try:
        return str(Path(abs_path).relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return abs_path.replace("\\", "/")


```

### File: `clockwork/index/models.py`

```python
﻿"""
clockwork/index/models.py
--------------------------
Data models for the Live Context Index subsystem.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    CREATED  = "created"
    MODIFIED = "modified"
    DELETED  = "deleted"
    RENAMED  = "renamed"


@dataclass
class ChangeEvent:
    """A single filesystem change event placed into the queue."""

    event_type: str          # EventType value
    file_path:  str          # absolute or repo-relative path
    timestamp:  float        # unix timestamp
    src_path:   str = ""     # for renames: original path

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "file_path":  self.file_path,
            "timestamp":  self.timestamp,
            "src_path":   self.src_path,
        }


@dataclass
class IndexEntry:
    """
    Cached metadata for a single file in the index.

    Stored in .clockwork/index.db — fields match spec §11.
    """

    file_path:     str
    last_modified: float
    file_hash:     str
    size_bytes:    int    = 0
    language:      str    = ""
    module_type:   str    = ""      # "source" | "test" | "config" | "other"
    dependencies:  str    = "[]"    # JSON list of import strings
    layer:         str    = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path":     self.file_path,
            "last_modified": self.last_modified,
            "file_hash":     self.file_hash,
            "size_bytes":    self.size_bytes,
            "language":      self.language,
            "module_type":   self.module_type,
            "dependencies":  self.dependencies,
            "layer":         self.layer,
        }


@dataclass
class IndexStats:
    """Summary returned after a full index build or repair."""

    total_files:    int   = 0
    indexed_files:  int   = 0
    skipped_files:  int   = 0
    elapsed_ms:     float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files":   self.total_files,
            "indexed_files": self.indexed_files,
            "skipped_files": self.skipped_files,
            "elapsed_ms":    round(self.elapsed_ms, 1),
        }


def compute_file_hash(path_str: str) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(path_str, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


```

### File: `clockwork/index/storage.py`

```python
﻿"""
clockwork/index/storage.py
---------------------------
SQLite persistence layer for the Live Context Index.

Stores per-file metadata in .clockwork/index.db so Clockwork
can detect meaningful changes without re-reading every file.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

from .models import IndexEntry

_SCHEMA_SQL = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS index_entries (
    file_path     TEXT PRIMARY KEY,
    last_modified REAL NOT NULL,
    file_hash     TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL DEFAULT 0,
    language      TEXT NOT NULL DEFAULT '',
    module_type   TEXT NOT NULL DEFAULT '',
    dependencies  TEXT NOT NULL DEFAULT '[]',
    layer         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS index_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_language ON index_entries(language);
CREATE INDEX IF NOT EXISTS idx_layer    ON index_entries(layer);
"""

_DROP_SQL = """
DROP TABLE IF EXISTS index_entries;
DROP TABLE IF EXISTS index_meta;
"""


class IndexStorage:
    """
    Manages .clockwork/index.db.

    Usage::

        store = IndexStorage(db_path)
        store.open()
        store.initialise()
        store.upsert(entry)
        store.commit()
        store.close()
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def open(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

    def close(self) -> None:
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def __enter__(self) -> "IndexStorage":
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def initialise(self, drop_existing: bool = False) -> None:
        assert self._conn
        if drop_existing:
            self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    # ── CRUD ───────────────────────────────────────────────────────────────

    def upsert(self, entry: IndexEntry) -> None:
        """Insert or replace an index entry."""
        assert self._conn
        self._conn.execute(
            """
            INSERT OR REPLACE INTO index_entries
              (file_path, last_modified, file_hash, size_bytes,
               language, module_type, dependencies, layer)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.file_path,
                entry.last_modified,
                entry.file_hash,
                entry.size_bytes,
                entry.language,
                entry.module_type,
                entry.dependencies,
                entry.layer,
            ),
        )

    def delete(self, file_path: str) -> None:
        assert self._conn
        self._conn.execute(
            "DELETE FROM index_entries WHERE file_path=?", (file_path,)
        )

    def get(self, file_path: str) -> Optional[IndexEntry]:
        assert self._conn
        row = self._conn.execute(
            "SELECT * FROM index_entries WHERE file_path=?", (file_path,)
        ).fetchone()
        return _row_to_entry(row) if row else None

    def all_entries(self) -> list[IndexEntry]:
        assert self._conn
        rows = self._conn.execute("SELECT * FROM index_entries").fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        assert self._conn
        return int(
            self._conn.execute("SELECT COUNT(*) FROM index_entries").fetchone()[0]
        )

    def has_changed(self, file_path: str, mtime: float, file_hash: str) -> bool:
        """
        Return True if the file is not in the index or its hash differs.
        This is the core change-detection check (spec §12).
        """
        assert self._conn
        row = self._conn.execute(
            "SELECT file_hash, last_modified FROM index_entries WHERE file_path=?",
            (file_path,),
        ).fetchone()
        if row is None:
            return True                        # new file
        if row["file_hash"] != file_hash:
            return True                        # content changed
        return False                           # unchanged — skip

    # ── metadata ───────────────────────────────────────────────────────────

    def set_meta(self, key: str, value: str) -> None:
        assert self._conn
        self._conn.execute(
            "INSERT OR REPLACE INTO index_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_meta(self, key: str) -> Optional[str]:
        assert self._conn
        row = self._conn.execute(
            "SELECT value FROM index_meta WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def drop_all(self) -> None:
        """Wipe the index completely (used by repair)."""
        assert self._conn
        self._conn.executescript(_DROP_SQL)
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()


def _row_to_entry(row: sqlite3.Row) -> IndexEntry:
    return IndexEntry(
        file_path=row["file_path"],
        last_modified=row["last_modified"],
        file_hash=row["file_hash"],
        size_bytes=row["size_bytes"],
        language=row["language"],
        module_type=row["module_type"],
        dependencies=row["dependencies"],
        layer=row["layer"],
    )


```

### File: `clockwork/index/watcher.py`

```python
﻿"""
clockwork/index/watcher.py
---------------------------
Filesystem watcher for the Live Context Index.

Uses the `watchdog` library (spec §4) to capture file events
and feeds them into a thread-safe queue with debouncing (spec §9).

Events captured:
  created / modified / deleted / renamed
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .models import ChangeEvent, EventType

logger = logging.getLogger("clockwork.index.watcher")

# Default debounce window in seconds (spec §9: 200 ms)
DEFAULT_DEBOUNCE_S = 0.2

# Directories always ignored
_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
}

# File extensions always ignored
_IGNORE_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".swp", ".tmp", ".log"}


class ChangeEventHandler:
    """
    Watchdog event handler that filters and queues filesystem events.

    Designed to work with or without watchdog installed — if watchdog
    is missing, the watcher gracefully degrades to poll-based fallback.
    """

    def __init__(
        self,
        event_queue: "queue.Queue[ChangeEvent]",
        repo_root: str,
    ) -> None:
        self._queue     = event_queue
        self._repo_root = repo_root

    def _should_ignore(self, path: str) -> bool:
        parts = Path(path).parts
        for part in parts:
            if part in _IGNORE_DIRS:
                return True
        ext = Path(path).suffix.lower()
        if ext in _IGNORE_EXTENSIONS:
            return True
        return False

    def _enqueue(self, event_type: str, path: str, src_path: str = "") -> None:
        if self._should_ignore(path):
            return
        event = ChangeEvent(
            event_type=event_type,
            file_path=path,
            timestamp=time.time(),
            src_path=src_path,
        )
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue full — dropping event for %s", path)

    # watchdog callback interface
    def on_created(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.CREATED, getattr(event, "src_path", ""))

    def on_modified(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.MODIFIED, getattr(event, "src_path", ""))

    def on_deleted(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.DELETED, getattr(event, "src_path", ""))

    def on_moved(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(
                EventType.RENAMED,
                getattr(event, "dest_path", ""),
                src_path=getattr(event, "src_path", ""),
            )


class DebouncedProcessor:
    """
    Reads from the event queue, deduplicates rapid-fire events for the
    same file (spec §9: 200 ms window), then calls the process callback.

    Runs in its own daemon thread.
    """

    def __init__(
        self,
        event_queue: "queue.Queue[ChangeEvent]",
        process_fn: Callable[[ChangeEvent], None],
        debounce_s: float = DEFAULT_DEBOUNCE_S,
    ) -> None:
        self._queue      = event_queue
        self._process_fn = process_fn
        self._debounce_s = debounce_s
        self._pending:   dict[str, ChangeEvent] = {}
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()
        self._thread     = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            # drain available events into _pending (last-write-wins per path)
            try:
                while True:
                    event = self._queue.get_nowait()
                    with self._lock:
                        self._pending[event.file_path] = event
            except queue.Empty:
                pass

            # flush events whose debounce window has elapsed
            now = time.time()
            to_process: list[ChangeEvent] = []
            with self._lock:
                for path, ev in list(self._pending.items()):
                    if now - ev.timestamp >= self._debounce_s:
                        to_process.append(ev)
                        del self._pending[path]

            for ev in to_process:
                try:
                    self._process_fn(ev)
                except Exception as exc:
                    logger.error("Error processing event %s: %s", ev.file_path, exc)

            time.sleep(0.05)  # 50 ms poll interval


class RepositoryWatcher:
    """
    High-level watcher that combines watchdog + DebouncedProcessor.

    Usage::

        def on_change(event: ChangeEvent):
            print(event)

        watcher = RepositoryWatcher(repo_root=Path("."), on_change=on_change)
        watcher.start()
        # ... do work ...
        watcher.stop()
    """

    def __init__(
        self,
        repo_root: Path,
        on_change: Callable[[ChangeEvent], None],
        debounce_s: float = DEFAULT_DEBOUNCE_S,
        queue_maxsize: int = 1000,
    ) -> None:
        self.repo_root  = repo_root.resolve()
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._event_queue: queue.Queue[ChangeEvent] = queue.Queue(maxsize=queue_maxsize)
        self._processor   = DebouncedProcessor(self._event_queue, on_change, debounce_s)
        self._observer: Optional[object] = None
        self._watchdog_available = False

    def start(self) -> bool:
        """
        Start watching.  Returns True if watchdog is available and
        real-time watching started, False if watchdog is not installed
        (caller should fall back to polling or manual index updates).
        """
        self._processor.start()

        try:
            from watchdog.observers import Observer  # type: ignore
            from watchdog.events import FileSystemEventHandler  # type: ignore

            handler = _WatchdogAdapter(
                ChangeEventHandler(self._event_queue, str(self.repo_root))
            )
            observer = Observer()
            observer.schedule(handler, str(self.repo_root), recursive=True)
            observer.start()
            self._observer = observer
            self._watchdog_available = True
            logger.info("Watchdog observer started on %s", self.repo_root)
            return True

        except ImportError:
            logger.warning(
                "watchdog not installed — real-time watching unavailable. "
                "Install it with: pip install watchdog"
            )
            return False

    def stop(self) -> None:
        if self._observer:
            try:
                self._observer.stop()   # type: ignore
                self._observer.join()   # type: ignore
            except Exception:
                pass
        self._processor.stop()

    def is_watching(self) -> bool:
        return self._watchdog_available and self._observer is not None

    def inject_event(self, event: ChangeEvent) -> None:
        """Manually inject an event (useful for testing without watchdog)."""
        self._event_queue.put_nowait(event)


class _WatchdogAdapter:
    """
    Thin adapter that converts watchdog FileSystemEventHandler interface
    to our ChangeEventHandler interface.
    """

    def __init__(self, handler: ChangeEventHandler) -> None:
        self._h = handler

    def on_created(self, event: object)  -> None: self._h.on_created(event)
    def on_modified(self, event: object) -> None: self._h.on_modified(event)
    def on_deleted(self, event: object)  -> None: self._h.on_deleted(event)
    def on_moved(self, event: object)    -> None: self._h.on_moved(event)

    # watchdog requires these
    def on_any_event(self, event: object) -> None: pass
    dispatch = on_any_event


```

### File: `clockwork/packaging/__init__.py`

```python
"""
Clockwork Packaging Engine
--------------------------
Exports and imports full project intelligence state as a portable .clockwork archive.
"""

from clockwork.packaging.packer import PackagingEngine
from clockwork.packaging.loader import PackageLoader
from clockwork.packaging.models import PackageMetadata

__all__ = ["PackagingEngine", "PackageLoader", "PackageMetadata"]

```

### File: `clockwork/packaging/checksum.py`

```python
"""
clockwork/packaging/checksum.py
--------------------------------
Checksum utilities for package integrity verification.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_file_checksum(path: Path, algorithm: str = "sha256") -> str:
    """Return the hex digest of a single file."""
    h = hashlib.new(algorithm)
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_directory_checksum(directory: Path, algorithm: str = "sha256") -> str:
    """
    Compute a deterministic checksum over all files inside *directory*.

    Files are sorted by relative path so the result is stable across
    machines regardless of filesystem ordering.
    """
    h = hashlib.new(algorithm)
    for file_path in sorted(directory.rglob("*")):
        if not file_path.is_file():
            continue
        # Include relative path in the hash so renames are detected.
        relative = str(file_path.relative_to(directory))
        h.update(relative.encode())
        h.update(b"\n")
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65_536), b""):
                h.update(chunk)
    return h.hexdigest()


def write_checksum_file(checksum: str, destination: Path) -> None:
    """Write checksum string to *destination*."""
    destination.write_text(checksum, encoding="utf-8")


def verify_checksum_file(checksum: str, checksum_file: Path) -> bool:
    """Return True if the stored checksum matches *checksum*."""
    if not checksum_file.exists():
        return False
    stored = checksum_file.read_text(encoding="utf-8").strip()
    return stored == checksum


def build_manifest(directory: Path) -> dict[str, str]:
    """
    Build a {relative_path: sha256} manifest for all files in *directory*.
    Used for fine-grained integrity reporting.
    """
    manifest: dict[str, str] = {}
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            rel = str(file_path.relative_to(directory))
            manifest[rel] = compute_file_checksum(file_path)
    return manifest

```

### File: `clockwork/packaging/cli_commands.py`

```python
"""
clockwork/packaging/cli_commands.py
-------------------------------------
Typer CLI command handlers for `clockwork pack` and `clockwork load`.

These functions are registered in the main CLI app (clockwork/cli/app.py).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from clockwork.packaging.packer import PackagingEngine, PackagingError
from clockwork.packaging.loader import PackageLoader, LoadError


def cmd_pack(
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Root directory of the repository (defaults to current directory).",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Directory to write the .clockwork package (defaults to .clockwork/packages/).",
    ),
    project_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Override the project name used in the package filename.",
    ),
) -> None:
    """
    Package the full project intelligence into a portable .clockwork archive.

    Output is stored in .clockwork/packages/<project_name>.clockwork by default.
    """
    root = (repo_root or Path.cwd()).resolve()

    try:
        engine = PackagingEngine(
            repo_root=root,
            output_dir=output_dir,
            project_name=project_name,
        )
        output_path = engine.pack()
        typer.echo(f"\nPackage ready: {output_path}")
    except PackagingError as exc:
        typer.echo(f"\nError:\n{exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"\nUnexpected error: {exc}", err=True)
        raise typer.Exit(code=2)


def cmd_load(
    package_file: Path = typer.Argument(
        ...,
        help="Path to the .clockwork package file to load.",
        exists=True,
        readable=True,
    ),
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo",
        "-r",
        help="Root directory of the target repository (defaults to current directory).",
    ),
) -> None:
    """
    Load a .clockwork package into the local repository.

    Restores project intelligence from the portable archive into .clockwork/.
    """
    root = (repo_root or Path.cwd()).resolve()

    try:
        loader = PackageLoader(repo_root=root)
        loader.load(package_path=package_file)
        typer.echo("\nProject intelligence restored successfully.")
    except LoadError as exc:
        typer.echo(f"\nError:\n{exc}", err=True)
        raise typer.Exit(code=1)
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"\nUnexpected error: {exc}", err=True)
        raise typer.Exit(code=2)

```

### File: `clockwork/packaging/loader.py`

```python
"""
clockwork/packaging/loader.py
------------------------------
PackageLoader — imports a .clockwork archive into the local repository.

Import Pipeline (spec §9):
    Package Load
    ↓
    Integrity Validation
    ↓
    Context Merge
    ↓
    Rule Validation
    ↓
    Context Activation
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Optional

from clockwork.packaging.checksum import (
    compute_directory_checksum,
    verify_checksum_file,
)
from clockwork.packaging.models import PackageMetadata


class LoadError(Exception):
    """Raised when a package cannot be loaded."""


class PackageLoader:
    """
    Loads a .clockwork package into a target repository.

    Usage::

        loader = PackageLoader(repo_root=Path("/path/to/repo"))
        loader.load(package_path=Path("project.clockwork"))
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def load(self, package_path: Path) -> None:
        """
        Execute the full import pipeline for *package_path*.

        Raises LoadError if validation fails at any stage.
        """
        start = time.perf_counter()

        print(f"Clockwork Load — importing {package_path.name}...")

        # 1. Package Load — extract to temp
        package_path = package_path.resolve()
        if not package_path.exists():
            raise LoadError(f"Package file not found: {package_path}")

        if not zipfile.is_zipfile(package_path):
            raise LoadError(
                f"'{package_path.name}' is not a valid .clockwork archive."
            )

        with tempfile.TemporaryDirectory(prefix="clockwork_load_") as tmp:
            staging = Path(tmp) / "extracted"
            staging.mkdir()

            self._extract(package_path, staging)

            # 2. Integrity Validation
            self._validate_integrity(staging)

            # 3. Compatibility Validation
            metadata = self._load_metadata(staging)
            self._validate_compatibility(metadata)

            # 4. Context Merge — copy files into .clockwork
            self._merge_context(staging)

        elapsed_ms = (time.perf_counter() - start) * 1000
        print("Package loaded successfully.")
        print(f"Project: {metadata.project_name}  |  Packed: {metadata.generated_at}")
        print(f"Completed in {elapsed_ms:.1f} ms")

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract(package_path: Path, staging: Path) -> None:
        """Unzip the archive into the staging directory."""
        with zipfile.ZipFile(package_path, "r") as zf:
            zf.extractall(staging)

    def _validate_integrity(self, staging: Path) -> None:
        """
        Verify the package checksum.

        Re-computes the directory checksum (excluding the checksum file itself)
        and compares it against the stored value.
        """
        checksum_file = staging / "package_checksum.txt"
        if not checksum_file.exists():
            raise LoadError(
                "Package integrity check failed: 'package_checksum.txt' not found.\n"
                "The archive may be corrupt or tampered with."
            )

        # Compute checksum over everything *except* the checksum file itself.
        # Move it outside the staging directory so rglob does not pick it up.
        stored = checksum_file.read_text(encoding="utf-8").strip()
        tmp_check = staging.parent / "_cw_checksum_verify.txt"
        checksum_file.rename(tmp_check)
        try:
            actual = compute_directory_checksum(staging)
        finally:
            tmp_check.rename(checksum_file)

        if stored != actual:
            raise LoadError(
                "Package integrity check FAILED.\n"
                f"  Expected: {stored}\n"
                f"  Actual:   {actual}\n"
                "The package may be corrupt or has been modified."
            )

        print("  ✓ Integrity check passed.")

    @staticmethod
    def _load_metadata(staging: Path) -> PackageMetadata:
        """Parse and return the package metadata."""
        meta_path = staging / "metadata.json"
        if not meta_path.exists():
            raise LoadError(
                "Package is missing 'metadata.json'. Cannot determine compatibility."
            )
        return PackageMetadata.from_json(meta_path.read_text(encoding="utf-8"))

    @staticmethod
    def _validate_compatibility(metadata: PackageMetadata) -> None:
        """Refuse loading if version is incompatible."""
        if not metadata.is_compatible():
            raise LoadError(
                f"Incompatible package version.\n"
                f"  Package clockwork_version : {metadata.clockwork_version}\n"
                f"  Package schema_version    : {metadata.package_version}\n"
                f"  Running clockwork_version : {metadata.clockwork_version}\n"
                "Upgrade Clockwork or use a compatible package."
            )
        print(f"  ✓ Compatibility check passed (v{metadata.clockwork_version}).")

    def _merge_context(self, staging: Path) -> None:
        """
        Copy staged files into .clockwork/, creating directories as needed.

        Skips metadata and checksum files — those are package-internal.
        """
        skip = {"metadata.json", "package_checksum.txt"}
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        for src in sorted(staging.rglob("*")):
            if not src.is_file():
                continue
            rel = str(src.relative_to(staging))
            if rel in skip:
                continue

            dest = self.clockwork_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied.append(rel)

        print(f"  ✓ Context merged: {len(copied)} file(s) restored.")
        for name in copied:
            print(f"    → .clockwork/{name}")

```

### File: `clockwork/packaging/models.py`

```python
"""
clockwork/packaging/models.py
------------------------------
Data models for the Clockwork Packaging Engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CLOCKWORK_VERSION = "0.1"
PACKAGE_SCHEMA_VERSION = 1

# Files that are ALWAYS excluded from packages for security reasons
SENSITIVE_EXCLUSIONS: set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "secret.json",
    "service_account.json",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
}

# Required source files from .clockwork/ that must be present to build a package
REQUIRED_SOURCE_FILES: list[str] = [
    "context.yaml",
    "repo_map.json",
]

# Optional source files included when present
OPTIONAL_SOURCE_FILES: list[str] = [
    "rules.md",
    "skills.json",
    "agent_history.json",
    "handoff/handoff.json",
    "validation_log.json",
    "config.yaml",
]


@dataclass
class PackageMetadata:
    """Describes a .clockwork package artifact."""

    clockwork_version: str = CLOCKWORK_VERSION
    package_version: int = PACKAGE_SCHEMA_VERSION
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    project_name: str = "unknown_project"
    clockwork_required: str = f">={CLOCKWORK_VERSION}"
    source_machine: Optional[str] = None
    file_manifest: list[str] = field(default_factory=list)
    checksum: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Serialisation helpers
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return metadata as a plain dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "PackageMetadata":
        """Deserialise from a plain dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, raw: str) -> "PackageMetadata":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------ #
    # Compatibility check
    # ------------------------------------------------------------------ #

    def is_compatible(self) -> bool:
        """
        Check whether this package is compatible with the running Clockwork version.

        Currently enforces:
          - package_version must equal PACKAGE_SCHEMA_VERSION
          - clockwork_version must match (simple equality; extend for semver later)
        """
        return (
            self.package_version == PACKAGE_SCHEMA_VERSION
            and self.clockwork_version == CLOCKWORK_VERSION
        )

```

### File: `clockwork/packaging/packaging_engine.py`

```python
"""Packaging Engine - full pre-pack and import pipeline."""
import json, zipfile, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import yaml

PACKAGE_FILES = ["context.yaml","repo_map.json","rules.yaml","rules.md","tasks.json","skills.json","agent_history.json","handoff/handoff.json","handoff/next_agent_brief.md"]

class PackagingEngine:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.d = repo_path / ".clockwork"

    def pack(self, output_name: str = "project.clockwork") -> Path:
        """Full pipeline: Context -> Scan check -> Rules -> Brain -> Assemble -> Compress."""
        ctx = self._load_context()
        if not ctx:
            raise RuntimeError("context.yaml missing. Run: clockwork init")
        if not (self.d / "repo_map.json").exists():
            raise RuntimeError("repo_map.json not found. Run: clockwork scan")
        from clockwork.rules.rule_engine import RuleEngine
        passed, violations = RuleEngine(self.repo_path).verify()
        if not passed:
            raise RuntimeError("Rule Engine failed before pack:\n" + "\n".join(f"  - {v}" for v in violations))
        # MiniBrain.analyze() does not exist - removed to prevent TypeError
        assessment: dict[str, Any] = {}
        (self.d / "packages").mkdir(exist_ok=True)
        out = self.d / "packages" / output_name
        meta = self._meta(ctx, assessment)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps(meta, indent=2))
            for f in PACKAGE_FILES:
                src = self.d / f
                if src.exists(): zf.write(src, arcname=f)
            zf.writestr("package_checksum.txt", hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest())
        return out

    def load(self, package_path: Path) -> None:
        """Pipeline: Load -> Integrity -> Version check -> Restore -> Rule validation."""
        if not zipfile.is_zipfile(package_path):
            raise ValueError("Not a valid .clockwork package")
        with zipfile.ZipFile(package_path, "r") as zf:
            names = zf.namelist()
            if "metadata.json" not in names: raise ValueError("Missing metadata.json")
            if "package_checksum.txt" not in names: raise ValueError("Missing package_checksum.txt")
            meta = json.loads(zf.read("metadata.json"))
            stored = zf.read("package_checksum.txt").decode().strip()
            computed = hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()
            if stored != computed: raise ValueError("Checksum mismatch - package may be corrupted.")
            if meta.get("package_version", 1) > 1: raise ValueError("Incompatible package version.")
            self.d.mkdir(exist_ok=True)
            (self.d / "handoff").mkdir(exist_ok=True)
            for name in names:
                if name in ("metadata.json", "package_checksum.txt"): continue
                dest = self.d / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
        from clockwork.rules.rule_engine import RuleEngine
        passed, violations = RuleEngine(self.repo_path).verify()
        if not passed:
            raise RuntimeError("Loaded package failed rule validation:\n" + "\n".join(f"  - {v}" for v in violations))

    def _meta(self, ctx: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        return {"clockwork_version": "0.1", "package_version": 1, "clockwork_required": ">=0.1", "generated_at": datetime.now(timezone.utc).isoformat(), "project_name": ctx.get("project_name", "unknown"), "languages": assessment.get("languages", []), "total_files": assessment.get("files", 0)}

    def _load_context(self) -> dict[str, Any]:
        p = self.d / "context.yaml"
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {} if p.exists() else {}

```

### File: `clockwork/packaging/packer.py`

```python
"""
clockwork/packaging/packer.py
------------------------------
PackagingEngine — builds a portable .clockwork archive.

Pipeline (spec §6):
    Context Load
    ↓
    Repository Scan Validation
    ↓
    Rule Engine Validation
    ↓
    Brain Verification
    ↓
    Package Assembly
    ↓
    File Compression
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from clockwork.packaging.checksum import (
    compute_directory_checksum,
    write_checksum_file,
    build_manifest,
)
from clockwork.packaging.models import (
    PackageMetadata,
    SENSITIVE_EXCLUSIONS,
    REQUIRED_SOURCE_FILES,
    OPTIONAL_SOURCE_FILES,
    CLOCKWORK_VERSION,
    PACKAGE_SCHEMA_VERSION,
)


class PackagingError(Exception):
    """Raised when the packaging pipeline cannot proceed."""


class PackagingEngine:
    """
    Builds and exports a .clockwork package from the project's .clockwork directory.

    Usage::

        engine = PackagingEngine(repo_root=Path("/path/to/repo"))
        output_path = engine.pack()          # returns Path to .clockwork file
    """

    PACKAGE_STORE = ".clockwork/packages"

    def __init__(
        self,
        repo_root: Path,
        output_dir: Optional[Path] = None,
        project_name: Optional[str] = None,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.output_dir: Path = output_dir or (self.repo_root / self.PACKAGE_STORE)
        self.project_name = project_name or self.repo_root.name

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def pack(self) -> Path:
        """
        Execute the full packaging pipeline and return the path to the
        generated .clockwork archive.

        Raises PackagingError on validation failure.
        """
        start = time.perf_counter()

        print("Clockwork Pack — starting packaging pipeline...")

        # 1. Context Load & Validation
        self._validate_clockwork_dir()
        self._validate_required_files()

        # 2. Collect files
        files_to_pack = self._collect_files()

        # 3. Assemble package in a temp directory
        with tempfile.TemporaryDirectory(prefix="clockwork_pack_") as tmp:
            staging = Path(tmp) / "staging"
            staging.mkdir()

            self._copy_files(files_to_pack, staging)

            # 4. Write metadata
            metadata = self._build_metadata(staging)
            (staging / "metadata.json").write_text(
                metadata.to_json(), encoding="utf-8"
            )

            # 5. Compute checksum over staged content (excluding the checksum file)
            #    The loader replicates this exclusion when verifying.
            checksum = compute_directory_checksum(staging)
            write_checksum_file(checksum, staging / "package_checksum.txt")

            # 6. Compress
            self.output_dir.mkdir(parents=True, exist_ok=True)
            output_path = self.output_dir / f"{self.project_name}.clockwork"
            self._compress(staging, output_path)

        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"Package created: {output_path}")
        print(f"Completed in {elapsed_ms:.1f} ms")
        return output_path

    # ------------------------------------------------------------------ #
    # Pipeline steps
    # ------------------------------------------------------------------ #

    def _validate_clockwork_dir(self) -> None:
        """Ensure .clockwork directory exists."""
        if not self.clockwork_dir.is_dir():
            raise PackagingError(
                "Clockwork not initialized in this repository.\n"
                "Run:  clockwork init"
            )

    def _validate_required_files(self) -> None:
        """Ensure all required source files are present."""
        missing = [
            f
            for f in REQUIRED_SOURCE_FILES
            if not (self.clockwork_dir / f).exists()
        ]
        if missing:
            raise PackagingError(
                f"Required files missing from .clockwork/:\n"
                + "\n".join(f"  - {m}" for m in missing)
                + "\nRun:  clockwork scan && clockwork update"
            )

    def _collect_files(self) -> list[tuple[Path, str]]:
        """
        Return a list of (absolute_path, archive_name) tuples.

        Includes required + optional files; excludes sensitive filenames.
        """
        collected: list[tuple[Path, str]] = []

        # Required files
        for rel in REQUIRED_SOURCE_FILES:
            src = self.clockwork_dir / rel
            if src.exists():
                collected.append((src, rel))

        # Optional files
        for rel in OPTIONAL_SOURCE_FILES:
            src = self.clockwork_dir / rel
            if src.exists():
                collected.append((src, rel))

        # Filter sensitive files
        collected = [
            (p, name)
            for p, name in collected
            if not self._is_sensitive(name)
        ]

        return collected

    @staticmethod
    def _is_sensitive(filename: str) -> bool:
        """Return True if the filename matches any sensitive pattern."""
        base = Path(filename).name.lower()
        for pattern in SENSITIVE_EXCLUSIONS:
            # Simple wildcard support: *.ext
            if pattern.startswith("*"):
                if base.endswith(pattern[1:]):
                    return True
            elif base == pattern.lower():
                return True
        return False

    def _copy_files(
        self, files: list[tuple[Path, str]], staging: Path
    ) -> None:
        """Copy collected files into the staging directory."""
        for src, archive_name in files:
            dest = staging / archive_name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    def _build_metadata(self, staging: Path) -> PackageMetadata:
        """Build and return a PackageMetadata instance."""
        manifest = build_manifest(staging)
        return PackageMetadata(
            clockwork_version=CLOCKWORK_VERSION,
            package_version=PACKAGE_SCHEMA_VERSION,
            generated_at=datetime.now(timezone.utc).isoformat(),
            project_name=self.project_name,
            source_machine=platform.node(),
            file_manifest=list(manifest.keys()),
        )

    @staticmethod
    def _compress(staging: Path, output_path: Path) -> None:
        """Compress the staging directory into a ZIP-based .clockwork archive."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(staging.rglob("*")):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(staging))
                    zf.write(file_path, arcname)

```

### File: `clockwork/registry/__init__.py`

```python
﻿"""
clockwork/registry/__init__.py
--------------------------------
Registry & Ecosystem subsystem (spec §14).

Transforms Clockwork from a standalone tool into a platform by
providing plugin discovery, installation, publishing, and versioning.

Supports offline mode — the local cache works without a live server.

Public API::

    from clockwork.registry import RegistryEngine

    reg = RegistryEngine(repo_root=Path("."))

    results = reg.search("security")
    reg.install("security_scanner")
    reg.list_installed()
    reg.publish(Path(".clockwork/plugins/my_plugin"))

CLI commands added:
    clockwork registry search [query]
    clockwork registry info <n>
    clockwork registry refresh
    clockwork registry status

    clockwork plugin install <n>
    clockwork plugin list
    clockwork plugin update <n>
    clockwork plugin remove <n>
    clockwork plugin publish [path]
"""

from clockwork.registry.registry_engine import RegistryEngine
from clockwork.registry.cache import RegistryCacheManager
from clockwork.registry.models import (
    ArtifactType,
    InstalledPlugin,
    RegistryCache,
    RegistryEntry,
)

__all__ = [
    "RegistryEngine",
    "RegistryCacheManager",
    "ArtifactType",
    "InstalledPlugin",
    "RegistryCache",
    "RegistryEntry",
]


```

### File: `clockwork/registry/cache.py`

```python
﻿"""
clockwork/registry/cache.py
----------------------------
Local registry cache manager (spec §14, §15).

Manages .clockwork/registry_cache.json so users can search and
discover plugins even when the registry server is offline.

On first use (empty cache) a set of built-in example entries is
seeded so the tool works immediately without a live server.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from .models import ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry


# ── Built-in seed entries (offline catalogue) ──────────────────────────────

_SEED_ENTRIES: list[dict] = [
    {
        "name": "security_scanner",
        "version": "0.2.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Advanced security scanning — secrets detection, CVE checks, SAST rules",
        "tags": ["security", "scanner", "sast"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "dependency_audit",
        "version": "0.1.3",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Audits third-party dependencies for known vulnerabilities",
        "tags": ["security", "dependencies", "audit"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "network_access"],
        "trusted": True,
    },
    {
        "name": "architecture_analyzer",
        "version": "0.3.1",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Detects architectural anti-patterns and layer violations",
        "tags": ["architecture", "analysis", "patterns"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "test_generator",
        "version": "0.1.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Auto-generates unit test scaffolding for Python modules",
        "tags": ["testing", "codegen", "python"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "repository_write"],
        "trusted": False,
    },
    {
        "name": "ollama_brain",
        "version": "0.2.0",
        "artifact_type": ArtifactType.BRAIN,
        "author": "clockwork-team",
        "description": "Local LLM reasoning engine powered by Ollama",
        "tags": ["brain", "llm", "local", "ollama"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "api_security_checker",
        "version": "0.1.1",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Checks REST API endpoints for common security misconfigurations",
        "tags": ["security", "api", "rest"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": False,
    },
    {
        "name": "doc_generator",
        "version": "0.1.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Generates markdown documentation from code symbols and docstrings",
        "tags": ["documentation", "codegen", "markdown"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "repository_write"],
        "trusted": False,
    },
    {
        "name": "ci_analyzer",
        "version": "0.1.2",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Analyses CI/CD pipeline configurations for best practices",
        "tags": ["ci", "devops", "github-actions", "analysis"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
]


class RegistryCacheManager:
    """
    Manages the local registry cache at .clockwork/registry_cache.json.

    Supports offline mode — falls back to seed entries when the cache
    is empty or the registry server is unreachable (spec §15).

    Usage::

        mgr = RegistryCacheManager(clockwork_dir)
        mgr.ensure_populated()
        results = mgr.search("security")
        entry   = mgr.get("security_scanner")
    """

    CACHE_TTL = 3600.0    # 1 hour

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir
        self.cache_path    = clockwork_dir / "registry_cache.json"
        self.installed_path = clockwork_dir / "installed_plugins.json"

    # ── cache lifecycle ────────────────────────────────────────────────────

    def load(self) -> RegistryCache:
        """Load cache from disk, returning empty cache if not found."""
        import logging as _logging
        _log = _logging.getLogger("clockwork.registry.cache")
        if not self.cache_path.exists():
            return RegistryCache()
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return RegistryCache.from_dict(data)
        except json.JSONDecodeError as exc:
            _log.warning("Registry cache corrupted (%s); returning empty cache. Original preserved at %s.bak", exc, self.cache_path)
            try:
                import shutil as _shutil
                _shutil.copy2(self.cache_path, str(self.cache_path) + ".bak")
            except OSError:
                pass
            return RegistryCache()
        except Exception as exc:
            _log.warning("Failed to load registry cache: %s", exc)
            return RegistryCache()

    def save(self, cache: RegistryCache) -> None:
        """Persist cache to disk."""
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(cache.to_dict(), indent=2), encoding="utf-8"
        )

    def ensure_populated(self) -> RegistryCache:
        """
        Load cache; if empty or missing, seed with built-in entries.
        Returns the populated cache.
        """
        cache = self.load()
        if not cache.entries:
            cache = self._seed()
            self.save(cache)
        return cache

    def _seed(self) -> RegistryCache:
        entries = [RegistryEntry.from_dict(e) for e in _SEED_ENTRIES]
        return RegistryCache(
            entries=entries,
            last_updated=time.time(),
            registry_url="https://registry.clockwork.dev",
        )

    # ── search + lookup ────────────────────────────────────────────────────

    def search(self, query: str = "", artifact_type: str = "") -> list[RegistryEntry]:
        """Search the local cache. Works offline."""
        cache = self.ensure_populated()
        results = cache.search(query)
        if artifact_type:
            results = [r for r in results if r.artifact_type == artifact_type]
        return results

    def get(self, name: str) -> Optional[RegistryEntry]:
        """Look up one entry by name."""
        cache = self.ensure_populated()
        return cache.get(name)

    def add_entry(self, entry: RegistryEntry) -> None:
        """Add or update an entry in the cache (used by publish)."""
        cache = self.ensure_populated()
        cache.entries = [e for e in cache.entries if e.name != entry.name]
        cache.entries.append(entry)
        cache.last_updated = time.time()
        self.save(cache)

    def remove_entry(self, name: str) -> bool:
        cache = self.ensure_populated()
        before = len(cache.entries)
        cache.entries = [e for e in cache.entries if e.name != name]
        if len(cache.entries) < before:
            self.save(cache)
            return True
        return False

    # ── installed plugins ──────────────────────────────────────────────────

    def list_installed(self) -> list[InstalledPlugin]:
        if not self.installed_path.exists():
            return []
        try:
            data = json.loads(self.installed_path.read_text(encoding="utf-8"))
            return [InstalledPlugin.from_dict(p) for p in data]
        except Exception:
            return []

    def record_install(self, plugin: InstalledPlugin) -> None:
        installed = self.list_installed()
        installed = [p for p in installed if p.name != plugin.name]
        installed.append(plugin)
        self.installed_path.write_text(
            json.dumps([p.to_dict() for p in installed], indent=2),
            encoding="utf-8",
        )

    def record_uninstall(self, name: str) -> bool:
        installed = self.list_installed()
        before    = len(installed)
        installed = [p for p in installed if p.name != name]
        if len(installed) < before:
            self.installed_path.write_text(
                json.dumps([p.to_dict() for p in installed], indent=2),
                encoding="utf-8",
            )
            return True
        return False

    def get_installed(self, name: str) -> Optional[InstalledPlugin]:
        for p in self.list_installed():
            if p.name == name:
                return p
        return None

    def cache_info(self) -> dict:
        cache = self.load()
        return {
            "entries":      len(cache.entries),
            "last_updated": cache.last_updated,
            "registry_url": cache.registry_url,
            "is_stale":     cache.is_stale(self.CACHE_TTL),
            "installed":    len(self.list_installed()),
        }


```

### File: `clockwork/registry/models.py`

```python
﻿"""
clockwork/registry/models.py
-----------------------------
Data models for the Registry & Ecosystem subsystem (spec §14).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Artifact types (spec §2) ───────────────────────────────────────────────

class ArtifactType:
    PLUGIN  = "plugin"
    BRAIN   = "brain"
    PACKAGE = "package"


# ── Registry entry ─────────────────────────────────────────────────────────

@dataclass
class RegistryEntry:
    """
    One record in the registry index.

    Represents a published plugin, brain, or package.
    """

    name:               str
    version:            str
    artifact_type:      str             = ArtifactType.PLUGIN
    author:             str             = ""
    description:        str             = ""
    requires_clockwork: str             = ">=0.1"
    permissions:        list[str]       = field(default_factory=list)
    tags:               list[str]       = field(default_factory=list)
    checksum:           str             = ""
    download_url:       str             = ""
    published_at:       float           = field(default_factory=time.time)
    trusted:            bool            = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":               self.name,
            "version":            self.version,
            "artifact_type":      self.artifact_type,
            "author":             self.author,
            "description":        self.description,
            "requires_clockwork": self.requires_clockwork,
            "permissions":        self.permissions,
            "tags":               self.tags,
            "checksum":           self.checksum,
            "download_url":       self.download_url,
            "published_at":       self.published_at,
            "trusted":            self.trusted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RegistryEntry":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            artifact_type=d.get("artifact_type", ArtifactType.PLUGIN),
            author=d.get("author", ""),
            description=d.get("description", ""),
            requires_clockwork=d.get("requires_clockwork", ">=0.1"),
            permissions=d.get("permissions", []),
            tags=d.get("tags", []),
            checksum=d.get("checksum", ""),
            download_url=d.get("download_url", ""),
            published_at=d.get("published_at", time.time()),
            trusted=d.get("trusted", False),
        )

    def matches_query(self, query: str) -> bool:
        """Return True if this entry matches a search query string."""
        q = query.lower()
        return (
            q in self.name.lower()
            or q in self.description.lower()
            or any(q in t.lower() for t in self.tags)
            or q in self.author.lower()
        )


# ── Registry cache (spec §14) ──────────────────────────────────────────────

@dataclass
class RegistryCache:
    """
    Local cache of registry metadata stored at
    .clockwork/registry_cache.json
    """

    entries:      list[RegistryEntry]   = field(default_factory=list)
    last_updated: float                 = 0.0
    registry_url: str                   = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries":      [e.to_dict() for e in self.entries],
            "last_updated": self.last_updated,
            "registry_url": self.registry_url,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RegistryCache":
        return cls(
            entries=[RegistryEntry.from_dict(e) for e in d.get("entries", [])],
            last_updated=d.get("last_updated", 0.0),
            registry_url=d.get("registry_url", ""),
        )

    def is_stale(self, ttl_seconds: float = 3600.0) -> bool:
        return (time.time() - self.last_updated) > ttl_seconds

    def search(self, query: str) -> list[RegistryEntry]:
        if not query:
            return list(self.entries)
        return [e for e in self.entries if e.matches_query(query)]

    def get(self, name: str) -> Optional[RegistryEntry]:
        for e in self.entries:
            if e.name == name:
                return e
        return None


# ── Install record ─────────────────────────────────────────────────────────

@dataclass
class InstalledPlugin:
    """Record of a locally installed plugin."""

    name:          str
    version:       str
    install_path:  str
    installed_at:  float = field(default_factory=time.time)
    enabled:       bool  = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":         self.name,
            "version":      self.version,
            "install_path": self.install_path,
            "installed_at": self.installed_at,
            "enabled":      self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InstalledPlugin":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            install_path=d.get("install_path", ""),
            installed_at=d.get("installed_at", time.time()),
            enabled=d.get("enabled", True),
        )


```

### File: `clockwork/registry/registry_engine.py`

```python
﻿"""
clockwork/registry/registry_engine.py
---------------------------------------
Main registry engine (spec §14).

Handles:
  - plugin search and discovery  (spec §8)
  - plugin installation          (spec §9)
  - plugin publishing            (spec §5)
  - plugin update / removal      (spec §4)
  - version management           (spec §7)
  - registry security checks     (spec §11)
  - offline mode                 (spec §15)
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from .cache import RegistryCacheManager
from .models import ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry


class RegistryEngine:
    """
    Top-level facade for the Registry subsystem.

    Usage::

        reg = RegistryEngine(repo_root=Path("."))
        results = reg.search("security")
        reg.install("security_scanner")
        reg.publish(Path(".clockwork/plugins/my_plugin"))
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.plugins_dir   = self.clockwork_dir / "plugins"
        self.cache_mgr     = RegistryCacheManager(self.clockwork_dir)

    # ── search (spec §8) ──────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        artifact_type: str = "",
    ) -> list[RegistryEntry]:
        """Search the registry for plugins/brains/packages."""
        return self.cache_mgr.search(query, artifact_type)

    def get(self, name: str) -> Optional[RegistryEntry]:
        """Look up one registry entry by name."""
        return self.cache_mgr.get(name)

    # ── install (spec §9) ─────────────────────────────────────────────────

    def install(self, name: str, version: str = "") -> tuple[bool, str]:
        """
        Install a plugin from the registry.

        For entries with a download_url, attempts a real download.
        For built-in/seed entries without a URL, creates a scaffold
        directory so the plugin slot is reserved (offline-safe).

        Returns (success, message).
        """
        entry = self.cache_mgr.get(name)
        if entry is None:
            return False, f"Plugin '{name}' not found in registry. Run: clockwork registry search"

        # check if already installed
        existing = self.cache_mgr.get_installed(name)
        if existing:
            return False, f"Plugin '{name}' is already installed (version {existing.version})."

        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        plugin_dir = self.plugins_dir / name

        # security verification before install (spec §11)
        ok, sec_issues = self._security_check(entry)
        if not ok:
            return False, f"Security check failed: {'; '.join(sec_issues)}"

        if entry.download_url:
            success, msg = self._download_and_install(entry, plugin_dir)
            if not success:
                return False, msg
        else:
            # offline scaffold — create directory + manifest
            self._create_scaffold(entry, plugin_dir)

        record = InstalledPlugin(
            name=entry.name,
            version=entry.version,
            install_path=str(plugin_dir),
        )
        self.cache_mgr.record_install(record)
        return True, f"Plugin '{name}' v{entry.version} installed to {plugin_dir}"

    # ── update (spec §4) ──────────────────────────────────────────────────

    def update(self, name: str) -> tuple[bool, str]:
        """Update an installed plugin to its latest registry version."""
        installed = self.cache_mgr.get_installed(name)
        if not installed:
            return False, f"Plugin '{name}' is not installed."

        entry = self.cache_mgr.get(name)
        if entry is None:
            return False, f"Plugin '{name}' not found in registry."

        if installed.version == entry.version:
            return True, f"Plugin '{name}' is already at the latest version ({entry.version})."

        # reinstall
        plugin_dir = Path(installed.install_path)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        self.cache_mgr.record_uninstall(name)
        return self.install(name)

    # ── remove (spec §4) ──────────────────────────────────────────────────

    def remove(self, name: str) -> tuple[bool, str]:
        """Remove an installed plugin."""
        installed = self.cache_mgr.get_installed(name)
        if not installed:
            return False, f"Plugin '{name}' is not installed."

        plugin_dir = Path(installed.install_path)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        self.cache_mgr.record_uninstall(name)
        return True, f"Plugin '{name}' removed."

    # ── publish (spec §5) ─────────────────────────────────────────────────

    def publish(self, plugin_dir: Path) -> tuple[bool, str]:
        """
        Publish a plugin to the registry.

        Pipeline (spec §5):
            Plugin validation → Manifest verification → Security scan → Registry upload
        """
        # step 1: validate manifest
        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            return False, "plugin.yaml manifest not found. Create one before publishing."

        try:
            import yaml  # type: ignore
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            return False, f"Invalid manifest: {exc}"

        name    = data.get("name", "")
        version = data.get("version", "")
        if not name or not version:
            return False, "Manifest must include 'name' and 'version'."

        # step 2: security verification
        try:
            from clockwork.security import SecurityEngine
            sec    = SecurityEngine(self.repo_root)
            ok, issues = sec.verify_plugin(plugin_dir)
            if not ok:
                return False, f"Security verification failed: {'; '.join(issues)}"
        except ImportError:
            pass  # security module optional for publish

        # step 3: compute checksum
        checksum = self._checksum_dir(plugin_dir)

        # step 4: add to local registry cache
        entry = RegistryEntry(
            name=name,
            version=version,
            artifact_type=data.get("artifact_type", ArtifactType.PLUGIN),
            author=data.get("author", ""),
            description=data.get("description", ""),
            requires_clockwork=data.get("requires_clockwork", ">=0.1"),
            permissions=data.get("permissions", []),
            tags=data.get("tags", []),
            checksum=checksum,
            published_at=time.time(),
        )
        self.cache_mgr.add_entry(entry)
        return True, (
            f"Plugin '{name}' v{version} published to local registry.\n"
            f"  Checksum: {checksum[:16]}...\n"
            "  Note: to publish to the global registry, set up a registry server."
        )

    # ── list installed ─────────────────────────────────────────────────────

    def list_installed(self) -> list[InstalledPlugin]:
        return self.cache_mgr.list_installed()

    # ── refresh cache ──────────────────────────────────────────────────────

    def refresh(self, registry_url: str = "") -> tuple[bool, str]:
        """
        Refresh the registry cache from a remote server.

        Falls back gracefully if the server is unreachable (spec §15).
        """
        if not registry_url:
            # try to get URL from existing cache
            existing = self.cache_mgr.load()
            registry_url = existing.registry_url or "https://registry.clockwork.dev"

        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(
                f"{registry_url}/plugins",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data    = json.loads(resp.read().decode("utf-8"))
                entries = [RegistryEntry.from_dict(e) for e in data.get("plugins", [])]
                cache   = RegistryCache(
                    entries=entries,
                    last_updated=time.time(),
                    registry_url=registry_url,
                )
                self.cache_mgr.save(cache)
                return True, f"Registry refreshed — {len(entries)} entries from {registry_url}"
        except Exception as exc:
            return False, (
                f"Could not reach registry at {registry_url}: {exc}\n"
                "Using local cache (offline mode)."
            )

    # ── cache info ─────────────────────────────────────────────────────────

    def cache_info(self) -> dict[str, Any]:
        return self.cache_mgr.cache_info()

    # ── private helpers ────────────────────────────────────────────────────

    def _security_check(self, entry: RegistryEntry) -> tuple[bool, list[str]]:
        """Basic pre-install security check (spec §11)."""
        issues: list[str] = []
        from clockwork.security.models import Permission
        dangerous = {Permission.SYSTEM_COMMAND}
        bad_perms = [p for p in entry.permissions if p in dangerous]
        if bad_perms:
            issues.append(
                f"Plugin requests dangerous permissions: {', '.join(bad_perms)}"
            )
        return len(issues) == 0, issues

    def _download_and_install(
        self, entry: RegistryEntry, plugin_dir: Path
    ) -> tuple[bool, str]:
        """Download a plugin archive and extract it."""
        try:
            import urllib.request
            import zipfile, tempfile, os
            with tempfile.TemporaryDirectory() as tmp:
                archive = os.path.join(tmp, f"{entry.name}.zip")
                urllib.request.urlretrieve(entry.download_url, archive)

                # verify checksum if provided (spec §11)
                if entry.checksum:
                    h = hashlib.sha256()
                    with open(archive, "rb") as fh:
                        for chunk in iter(lambda: fh.read(65536), b""):
                            h.update(chunk)
                    if h.hexdigest() != entry.checksum:
                        return False, "Checksum mismatch — download may be corrupted."

                with zipfile.ZipFile(archive) as zf:
                    zf.extractall(str(plugin_dir))
            return True, "Downloaded and extracted."
        except Exception as exc:
            return False, f"Download failed: {exc}"

    def _create_scaffold(self, entry: RegistryEntry, plugin_dir: Path) -> None:
        """Create a plugin scaffold directory for offline/seed entries."""
        plugin_dir.mkdir(parents=True, exist_ok=True)
        try:
            import yaml  # type: ignore
            manifest = {
                "name":               entry.name,
                "version":            entry.version,
                "author":             entry.author,
                "description":        entry.description,
                "requires_clockwork": entry.requires_clockwork,
                "permissions":        entry.permissions,
                "tags":               entry.tags,
                "status":             "scaffold",
            }
            (plugin_dir / "plugin.yaml").write_text(
                yaml.dump(manifest, default_flow_style=False), encoding="utf-8"
            )
        except ImportError:
            import json as _json
            (plugin_dir / "plugin.yaml").write_text(
                f"name: {entry.name}\nversion: {entry.version}\nstatus: scaffold\n",
                encoding="utf-8",
            )
        (plugin_dir / "README.md").write_text(
            f"# {entry.name}\n\n{entry.description}\n\n"
            "_This is a scaffold placeholder. Replace with the actual plugin implementation._\n",
            encoding="utf-8",
        )

    def _checksum_dir(self, plugin_dir: Path) -> str:
        h = hashlib.sha256()
        for fp in sorted(plugin_dir.rglob("*")):
            if fp.is_file():
                try:
                    h.update(fp.read_bytes())
                except OSError:
                    pass
        return h.hexdigest()


```

### File: `clockwork/rules/__init__.py`

```python
﻿"""
Clockwork Rule Engine subsystem.
"""
from clockwork.rules.models import (
    RuleCategory, RuleSeverity, RuleViolation, RuleReport, RuleConfig,
)
from clockwork.rules.loader import RuleLoader
from clockwork.rules.engine import RuleEngine

__all__ = [
    "RuleCategory", "RuleSeverity", "RuleViolation",
    "RuleReport", "RuleConfig", "RuleLoader", "RuleEngine",
]

```

### File: `clockwork/rules/default_rules.yaml`

```yaml
﻿rules:
  forbid_core_file_deletion: true
  require_tests_for_new_modules: true
  enforce_architecture_layers: true
  protected_files:
    - ".clockwork/context.yaml"
    - ".clockwork/rules.md"
    - ".clockwork/rules.yaml"
    - ".clockwork/repo_map.json"
  protected_directories:
    - "core/"
    - "database/"
  forbid_file_patterns:
    - "*.env"
    - ".env"
    - "credentials.json"
    - "secrets*"
  require_tests_for:
    - "backend/"
    - "services/"
    - "clockwork/"
  dependency_files:
    - "requirements.txt"
    - "pyproject.toml"
    - "package.json"

```

### File: `clockwork/rules/engine.py`

```python
﻿from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from clockwork.rules.evaluators import ArchitectureEvaluator, ContextEvaluator, DevelopmentEvaluator, SafetyEvaluator
from clockwork.rules.loader import RuleLoader
from clockwork.rules.models import RuleConfig, RuleReport, RuleSeverity, RuleViolation

logger = logging.getLogger(__name__)


class RuleEngine:
    _EVALUATOR_CLASSES = [SafetyEvaluator, ArchitectureEvaluator, DevelopmentEvaluator, ContextEvaluator]

    def __init__(self, repo_root: Path | None = None) -> None:
        self._repo_root = repo_root or Path.cwd()
        self._clockwork_dir = self._repo_root / ".clockwork"
        self._rule_log_path = self._clockwork_dir / "rule_log.json"
        self._override_log_path = self._clockwork_dir / "override_log.json"
        self._config: RuleConfig = RuleLoader(self._clockwork_dir).load()
        self._evaluators = [cls(self._config, self._repo_root) for cls in self._EVALUATOR_CLASSES]

    def evaluate(self, changed_files: list[str], deleted_files: list[str] | None = None) -> RuleReport:
        deleted_files = deleted_files or []
        all_files = list(set(changed_files + deleted_files))
        start = time.perf_counter()
        violations: list[RuleViolation] = []
        for evaluator in self._evaluators:
            try:
                violations.extend(evaluator.evaluate(changed_files, deleted_files))
            except Exception as exc:
                logger.error("Evaluator %s error: %s", evaluator.__class__.__name__, exc)
        duration_ms = (time.perf_counter() - start) * 1000
        violations = self._resolve_conflicts(violations)
        report = RuleReport(violations=violations, evaluated_files=all_files, duration_ms=duration_ms)
        self._log_report(report)
        return report

    def record_override(self, rule_id: str, reason: str, operator: str = "user") -> None:
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "rule_id": rule_id, "reason": reason, "operator": operator}
        log = []
        if self._override_log_path.exists():
            try:
                log = json.loads(self._override_log_path.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(entry)
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._override_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

    @property
    def config(self) -> RuleConfig:
        return self._config

    @staticmethod
    def _resolve_conflicts(violations: list[RuleViolation]) -> list[RuleViolation]:
        by_file: dict = {}
        for v in violations:
            _fkey = v.file_path if v.file_path is not None else id(v)
            by_file.setdefault(_fkey, []).append(v)
        resolved = []
        for file_violations in by_file.values():
            if len(file_violations) <= 1:
                resolved.extend(file_violations)
                continue
            sorted_v = sorted(file_violations, key=lambda v: v.category.priority)
            top_priority = sorted_v[0].category.priority
            for v in sorted_v:
                if v.category.priority > top_priority and v.severity == RuleSeverity.BLOCK:
                    resolved.append(RuleViolation(rule_id=v.rule_id, category=v.category, severity=RuleSeverity.WARN, message=v.message + " [demoted]", file_path=v.file_path, timestamp=v.timestamp))
                else:
                    resolved.append(v)
        return resolved

    def _log_report(self, report: RuleReport) -> None:
        entry = {"timestamp": datetime.utcnow().isoformat(), "passed": report.passed, "duration_ms": round(report.duration_ms, 2), "violations": [v.to_dict() for v in report.violations]}
        log = []
        if self._rule_log_path.exists():
            try:
                log = json.loads(self._rule_log_path.read_text(encoding="utf-8"))
            except Exception:
                log = []
        log.append(entry)
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._rule_log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")

```

### File: `clockwork/rules/evaluators.py`

```python
﻿from __future__ import annotations
import fnmatch
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from clockwork.rules.models import RuleCategory, RuleConfig, RuleSeverity, RuleViolation

logger = logging.getLogger(__name__)


class BaseEvaluator(ABC):
    category: RuleCategory

    def __init__(self, config: RuleConfig, repo_root: Path) -> None:
        self._config = config
        self._repo_root = repo_root

    @abstractmethod
    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]: ...

    def _violation(self, rule_id: str, message: str, file_path: str | None = None, severity: RuleSeverity = RuleSeverity.BLOCK) -> RuleViolation:
        return RuleViolation(rule_id=rule_id, category=self.category, severity=severity, message=message, file_path=file_path)

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        for p in patterns:
            if fnmatch.fnmatch(path, p) or fnmatch.fnmatch(Path(path).name, p):
                return True
        return False

    @staticmethod
    def _under_prefix(path: str, prefixes: list[str]) -> bool:
        return any(path.replace("\\", "/").startswith(p) for p in prefixes)


class SafetyEvaluator(BaseEvaluator):
    category = RuleCategory.SAFETY

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        violations = []
        for path in changed_files:
            if path in self._config.protected_files:
                violations.append(self._violation("protected_file_modification", f"Protected file modification attempted: {path}", path))
                continue
            for d in self._config.protected_directories:
                if path.startswith(d):
                    violations.append(self._violation("protected_directory_modification", f"Protected directory modified: {path}", path))
            if self._matches_any(path, self._config.forbid_file_patterns):
                violations.append(self._violation("forbidden_file_pattern", f"Forbidden file pattern: {path}", path))
        if self._config.forbid_core_file_deletion:
            for path in deleted_files:
                if path in self._config.protected_files:
                    violations.append(self._violation("core_file_deletion", f"Deletion of protected file attempted: {path}", path))
        return violations


class ArchitectureEvaluator(BaseEvaluator):
    category = RuleCategory.ARCHITECTURE
    _FORBIDDEN_PAIRS = [("frontend/", "database/"), ("frontend/", "models/"), ("ui/", "database/")]

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        if not self._config.enforce_architecture_layers:
            return []
        violations = []
        for path in changed_files:
            full = self._repo_root / path
            if not full.exists() or full.suffix not in {".py", ".js", ".ts"}:
                continue
            try:
                source = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for src_prefix, tgt_prefix in self._FORBIDDEN_PAIRS:
                if not path.startswith(src_prefix):
                    continue
                tgt_module = tgt_prefix.rstrip("/").replace("/", ".")
                if tgt_module in source:
                    violations.append(self._violation("architecture_layer_violation", f"Layer violation in {path}: '{src_prefix}' must not import from '{tgt_prefix}'", path))
        return violations


class DevelopmentEvaluator(BaseEvaluator):
    category = RuleCategory.DEVELOPMENT

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        if not self._config.require_tests_for_new_modules:
            return []
        violations = []
        for path in changed_files:
            if not path.endswith(".py"):
                continue
            if not self._under_prefix(path, self._config.require_tests_for):
                continue
            if Path(path).name.startswith("__") or "test" in path.lower():
                continue
            expected = f"tests/test_{Path(path).stem}.py"
            if not (self._repo_root / expected).exists() and expected not in changed_files:
                violations.append(self._violation("missing_test_file", f"New module without test:\n  Module  : {path}\n  Expected: {expected}", path, RuleSeverity.WARN))
        return violations


class ContextEvaluator(BaseEvaluator):
    category = RuleCategory.CONTEXT
    _MANAGED = frozenset({".clockwork/context.yaml", ".clockwork/repo_map.json", ".clockwork/agent_history.json", ".clockwork/validation_log.json", ".clockwork/rule_log.json"})

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        violations = []
        for path in changed_files + deleted_files:
            if path in self._MANAGED:
                violations.append(self._violation("clockwork_memory_tampered", f"Clockwork-managed file modified outside Clockwork: {path}", path, RuleSeverity.WARN))
        return violations

```

### File: `clockwork/rules/loader.py`

```python
﻿from __future__ import annotations
import logging
from pathlib import Path
import yaml
from clockwork.rules.models import RuleConfig

logger = logging.getLogger(__name__)

_DEFAULT_RULES_YAML = """
rules:
  forbid_core_file_deletion: true
  require_tests_for_new_modules: true
  enforce_architecture_layers: true
  protected_files:
    - ".clockwork/context.yaml"
    - ".clockwork/rules.md"
    - ".clockwork/rules.yaml"
    - ".clockwork/repo_map.json"
  protected_directories:
    - "core/"
    - "database/"
  forbid_file_patterns:
    - "*.env"
    - ".env"
    - "credentials.json"
    - "secrets*"
  require_tests_for:
    - "backend/"
    - "services/"
    - "clockwork/"
  dependency_files:
    - "requirements.txt"
    - "pyproject.toml"
    - "package.json"
"""


class RuleLoader:
    def __init__(self, clockwork_dir: Path) -> None:
        self._clockwork_dir = clockwork_dir
        self._rules_yaml_path = clockwork_dir / "rules.yaml"

    def load(self) -> RuleConfig:
        if not self._rules_yaml_path.exists():
            logger.warning("rules.yaml not found — using defaults")
            return RuleConfig()
        try:
            raw = self._rules_yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
            return RuleConfig.from_dict(data)
        except Exception as exc:
            logger.error("Cannot load rules.yaml: %s — using defaults", exc)
            return RuleConfig()

    def write_defaults(self, overwrite: bool = False) -> bool:
        if self._rules_yaml_path.exists() and not overwrite:
            return False
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._rules_yaml_path.write_text(_DEFAULT_RULES_YAML.strip(), encoding="utf-8")
        return True

    def save(self, config: RuleConfig) -> None:
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        with self._rules_yaml_path.open("w", encoding="utf-8") as fh:
            yaml.dump(config.to_dict(), fh, default_flow_style=False, sort_keys=False)

```

### File: `clockwork/rules/models.py`

```python
﻿from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RuleCategory(str, Enum):
    SAFETY = "safety"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    CONTEXT = "context"

    @property
    def priority(self) -> int:
        return {
            RuleCategory.SAFETY: 1,
            RuleCategory.ARCHITECTURE: 2,
            RuleCategory.DEVELOPMENT: 3,
            RuleCategory.CONTEXT: 4,
        }[self]


class RuleSeverity(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    INFO = "info"


@dataclass
class RuleViolation:
    rule_id: str
    category: RuleCategory
    severity: RuleSeverity
    message: str
    file_path: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    overridden: bool = False

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat(),
            "overridden": self.overridden,
        }

    def __str__(self) -> str:
        path_info = f"\n  File: {self.file_path}" if self.file_path else ""
        return f"[{self.category.value.upper()}] {self.rule_id}: {self.message}{path_info}"


@dataclass
class RuleReport:
    violations: list[RuleViolation] = field(default_factory=list)
    evaluated_files: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return not any(
            v.severity == RuleSeverity.BLOCK and not v.overridden
            for v in self.violations
        )

    @property
    def blocking_violations(self) -> list[RuleViolation]:
        return [v for v in self.violations if v.severity == RuleSeverity.BLOCK and not v.overridden]

    @property
    def warnings(self) -> list[RuleViolation]:
        return [v for v in self.violations if v.severity == RuleSeverity.WARN]

    def summary(self) -> str:
        status = "Passed" if self.passed else "Failed"
        lines = [
            f"Rule Engine Report — {status}",
            f"  Files evaluated : {len(self.evaluated_files)}",
            f"  Violations      : {len(self.violations)}",
            f"  Blocking        : {len(self.blocking_violations)}",
            f"  Warnings        : {len(self.warnings)}",
            f"  Duration        : {self.duration_ms:.1f} ms",
        ]
        if self.blocking_violations:
            lines.append("\nBlocking Violations:")
            for v in self.blocking_violations:
                lines.append(f"  * {v}")
        if self.warnings:
            lines.append("\nWarnings:")
            for v in self.warnings:
                lines.append(f"  ! {v}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "evaluated_files": self.evaluated_files,
            "duration_ms": self.duration_ms,
            "violations": [v.to_dict() for v in self.violations],
        }


@dataclass
class RuleConfig:
    forbid_core_file_deletion: bool = True
    require_tests_for_new_modules: bool = True
    enforce_architecture_layers: bool = True
    protected_files: list[str] = field(default_factory=lambda: [
        ".clockwork/context.yaml",
        ".clockwork/rules.md",
        ".clockwork/rules.yaml",
        ".clockwork/repo_map.json",
    ])
    protected_directories: list[str] = field(default_factory=lambda: ["core/", "database/"])
    forbid_file_patterns: list[str] = field(default_factory=lambda: [
        "*.env", ".env", "credentials.json", "secrets*",
    ])
    require_tests_for: list[str] = field(default_factory=lambda: [
        "backend/", "services/", "clockwork/",
    ])
    dependency_files: list[str] = field(default_factory=lambda: [
        "requirements.txt", "pyproject.toml", "package.json",
    ])

    @classmethod
    def from_dict(cls, data: dict) -> "RuleConfig":
        r = data.get("rules", {})
        return cls(
            forbid_core_file_deletion=r.get("forbid_core_file_deletion", True),
            require_tests_for_new_modules=r.get("require_tests_for_new_modules", True),
            enforce_architecture_layers=r.get("enforce_architecture_layers", True),
            protected_files=r.get("protected_files", [".clockwork/context.yaml", ".clockwork/rules.md", ".clockwork/rules.yaml", ".clockwork/repo_map.json"]),
            protected_directories=r.get("protected_directories", ["core/", "database/"]),
            forbid_file_patterns=r.get("forbid_file_patterns", ["*.env", ".env", "credentials.json", "secrets*"]),
            require_tests_for=r.get("require_tests_for", ["backend/", "services/", "clockwork/"]),
            dependency_files=r.get("dependency_files", ["requirements.txt", "pyproject.toml", "package.json"]),
        )

    def to_dict(self) -> dict:
        return {"rules": {
            "forbid_core_file_deletion": self.forbid_core_file_deletion,
            "require_tests_for_new_modules": self.require_tests_for_new_modules,
            "enforce_architecture_layers": self.enforce_architecture_layers,
            "protected_files": self.protected_files,
            "protected_directories": self.protected_directories,
            "forbid_file_patterns": self.forbid_file_patterns,
            "require_tests_for": self.require_tests_for,
            "dependency_files": self.dependency_files,
        }}

```

### File: `clockwork/rules/rule_engine.py`

```python
# -*- coding: utf-8 -*-
"""Rule Engine - real static analysis for all 3 rules."""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import yaml

PROTECTED_CORE_FILES = ["clockwork/cli/main.py","clockwork/scanner/repository_scanner.py","clockwork/context/context_engine.py","clockwork/rules/rule_engine.py","clockwork/brain/mini_brain.py","clockwork/handoff/handoff_engine.py","clockwork/packaging/packaging_engine.py","clockwork/graph/graph_engine.py"]
SCHEMA_FILE_PATTERNS = ["schema.sql","schema.py","models.py","models.sql","create_tables","db_schema","database_schema"]
MIGRATION_PATTERNS = ["migrations/","migration/","alembic/","flyway/","migrate_","_migration","001_","002_","003_"]
DIRECT_DB_PATTERNS = ["sqlite3.connect","psycopg2.connect","pymysql.connect","mysql.connector","cx_Oracle","pyodbc.connect"]
API_LAYER_FILES = ["api.py","routes.py","views.py","endpoints.py","router.py","controllers.py"]

class RuleEngine:
    """Evaluates repository state against Clockwork rules."""
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.clockwork_dir = repo_path / ".clockwork"

    def _load_rules(self) -> list[dict[str, Any]]:
        p = self.clockwork_dir / "rules.yaml"
        if not p.exists(): return []
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return data.get("rules", []) if data else []

    def _load_repo_map(self) -> dict[str, Any]:
        p = self.clockwork_dir / "repo_map.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def verify(self) -> tuple[bool, list[str]]:
        """Run all rules. Returns (passed, violations)."""
        rules = self._load_rules()
        repo_map = self._load_repo_map()
        violations: list[str] = []
        for rule in rules:
            v = self._evaluate_rule(rule, repo_map)
            if v: violations.append(v)
        passed = len(violations) == 0
        self._log_validation(passed, violations)
        self._log_rule(rules, passed, violations)
        self._log_agent_action("rule_engine.verify", passed, violations)
        return passed, violations

    def _evaluate_rule(self, rule: dict[str, Any], repo_map: dict[str, Any]) -> str | None:
        """Real static analysis per rule."""
        rule_id = rule.get("id", "")
        file_paths = [f["path"] for f in repo_map.get("files", [])]
        if rule_id == "no_schema_change_without_migration":
            return self._check_schema_without_migration(file_paths)
        if rule_id == "no_bypass_api_layer":
            return self._check_api_layer_bypass(file_paths)
        if rule_id == "no_delete_core_modules":
            return self._check_core_modules_present(file_paths)
        return None

    def _check_schema_without_migration(self, file_paths: list[str]) -> str | None:
        has_schema = any(any(p in fp.lower() for p in SCHEMA_FILE_PATTERNS) for fp in file_paths)
        has_migration = any(any(p in fp.lower() for p in MIGRATION_PATTERNS) for fp in file_paths)
        if has_schema and not has_migration:
            schema_files = [fp for fp in file_paths if any(p in fp.lower() for p in SCHEMA_FILE_PATTERNS)]
            return f"Rule [no_schema_change_without_migration]: Schema file(s) detected ({', '.join(schema_files[:3])}) but no migration files found."
        return None

    def _check_api_layer_bypass(self, file_paths: list[str]) -> str | None:
        has_api = any(any(a in fp.lower() for a in API_LAYER_FILES) for fp in file_paths)
        if not has_api: return None
        found: list[str] = []
        for fp in file_paths:
            if not fp.endswith(".py"): continue
            if any(a in fp.lower() for a in API_LAYER_FILES): continue
            full = self.repo_path / fp
            if not full.exists(): continue
            try:
                content = full.read_text(encoding="utf-8", errors="ignore")
                for pat in DIRECT_DB_PATTERNS:
                    if pat in content:
                        found.append(f"{fp} uses {pat}"); break
            except OSError: continue
        if found:
            return f"Rule [no_bypass_api_layer]: Direct DB access outside API layer: {', '.join(found[:3])}"
        return None

    def _check_core_modules_present(self, file_paths: list[str]) -> str | None:
        is_cw = any("clockwork/cli" in p or "clockwork\\cli" in p for p in file_paths)
        if not is_cw: return None
        missing = [f for f in PROTECTED_CORE_FILES
                   if not (self.repo_path / f).exists()
                   and not (self.repo_path / f.replace("/", "\\")).exists()]
        if missing:
            return f"Rule [no_delete_core_modules]: Core module(s) missing from disk: {', '.join(missing[:3])}"
        return None

    def _log_validation(self, passed: bool, violations: list[str]) -> None:
        p = self.clockwork_dir / "validation_log.json"
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append({"timestamp": datetime.now(timezone.utc).isoformat(), "passed": passed, "violations": violations})
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")

    def _log_rule(self, rules: list[dict[str, Any]], passed: bool, violations: list[str]) -> None:
        p = self.clockwork_dir / "logs" / "rule_log.json"
        p.parent.mkdir(exist_ok=True)
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append({"timestamp": datetime.now(timezone.utc).isoformat(), "rules_evaluated": len(rules), "passed": passed, "violations": violations})
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")

    def _log_agent_action(self, action: str, passed: bool, violations: list[str]) -> None:
        p = self.clockwork_dir / "agent_history.json"
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append({"timestamp": datetime.now(timezone.utc).isoformat(), "agent": "rule_engine", "action": action, "result": "passed" if passed else "failed", "violations": violations})
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")
```

### File: `clockwork/scanner/__init__.py`

```python
"""
clockwork/scanner/__init__.py
-------------------------------
Repository Scanner subsystem.

Public API::

    from clockwork.scanner import RepositoryScanner, ScanResult

    scanner = RepositoryScanner(repo_root=Path("/path/to/repo"))
    result  = scanner.scan()
    result.save(clockwork_dir)
"""

from clockwork.scanner.models import (
    FileEntry,
    DirectoryEntry,
    ScanResult,
    LanguageSummary,
)
from clockwork.scanner.scanner import RepositoryScanner
from clockwork.scanner.language import LanguageDetector
from clockwork.scanner.symbols import SymbolExtractor

__all__ = [
    "RepositoryScanner",
    "ScanResult",
    "FileEntry",
    "DirectoryEntry",
    "LanguageSummary",
    "LanguageDetector",
    "SymbolExtractor",
]

```

### File: `clockwork/scanner/filters.py`

```python
"""
clockwork/scanner/filters.py
------------------------------
Filtering rules for the Repository Scanner.

Determines which files and directories should be:
  • skipped entirely (ignored dirs, binary files, sensitive files)
  • flagged as sensitive and excluded from packages
  • classified as test / config / entry-point files
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import re


# ── Default ignore sets ────────────────────────────────────────────────────

DEFAULT_IGNORE_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "node_modules", ".npm", ".yarn",
    ".venv", "venv", "env", ".env_dir",
    "dist", "build", "target", "out", "bin", "obj",
    ".clockwork",
    ".idea", ".vscode", ".eclipse",
    "eggs", "*.egg-info",
    ".tox",
    "htmlcov", ".coverage",
    "site-packages",
})

DEFAULT_IGNORE_EXTENSIONS: frozenset[str] = frozenset({
    # Compiled / binary
    ".pyc", ".pyo", ".pyd",
    ".class", ".jar", ".war",
    ".o", ".obj", ".lib", ".a", ".so", ".dll", ".dylib", ".exe",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".whl", ".egg",
    # Media
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".ttf", ".woff", ".woff2", ".eot",
    # Documents
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Database / lock
    ".db", ".sqlite", ".sqlite3",
    ".lock",   # package-lock.json excluded separately
    # IDE / OS
    ".DS_Store",
})

# Sensitive filenames — always excluded from packages, never indexed
SENSITIVE_FILENAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "credentials.json", "secrets.json", "secret.json",
    "service_account.json", "google_credentials.json",
    ".netrc", ".htpasswd",
    "id_rsa", "id_rsa.pub", "id_ed25519", "id_ed25519.pub",
    "id_dsa", "id_ecdsa",
})

SENSITIVE_EXTENSIONS: frozenset[str] = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".cer", ".crt",
})

# Entry-point filename heuristics
ENTRY_POINT_NAMES: frozenset[str] = frozenset({
    "main.py", "app.py", "server.py", "run.py", "manage.py",
    "wsgi.py", "asgi.py", "cli.py", "entrypoint.py",
    "index.js", "index.ts", "main.js", "main.ts",
    "app.js", "app.ts", "server.js", "server.ts",
    "main.go", "main.rs", "main.java", "Main.java",
    "main.c", "main.cpp",
    "program.cs",
})

# Dependency / config files of interest
DEPENDENCY_FILES: frozenset[str] = frozenset({
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "requirements-dev.txt", "requirements-test.txt", "pipfile",
    "package.json", "yarn.lock", "package-lock.json",
    "go.mod", "go.sum",
    "cargo.toml", "cargo.lock",
    "pom.xml", "build.gradle", "settings.gradle",
    "gemfile", "gemfile.lock",
    "composer.json",
    "dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".github",
    "tox.ini", "pytest.ini", ".flake8", "mypy.ini",
    ".eslintrc", ".eslintrc.js", ".eslintrc.json",
    "tsconfig.json", "jsconfig.json",
    "makefile", "cmakelists.txt",
})


# ── Classifier ────────────────────────────────────────────────────────────

class ScanFilter:
    """
    Encapsulates all filtering and classification logic for the scanner.

    Extra ignore dirs/extensions can be provided via config.yaml.
    """

    def __init__(
        self,
        extra_ignore_dirs: Optional[set[str]] = None,
        extra_ignore_extensions: Optional[set[str]] = None,
    ) -> None:
        self.ignore_dirs: frozenset[str] = (
            DEFAULT_IGNORE_DIRS | frozenset(extra_ignore_dirs or set())
        )
        self.ignore_extensions: frozenset[str] = (
            DEFAULT_IGNORE_EXTENSIONS | frozenset(extra_ignore_extensions or set())
        )

    # ------------------------------------------------------------------ #
    # Path-level decisions
    # ------------------------------------------------------------------ #

    def should_skip_directory(self, dir_path: Path, repo_root: Path) -> bool:
        """Return True if this directory should be ignored entirely."""
        for part in dir_path.relative_to(repo_root).parts:
            if part in self.ignore_dirs:
                return True
        return False

    def should_skip_file(self, file_path: Path) -> bool:
        """Return True if this file should be excluded from scanning."""
        name_lower = file_path.name.lower()
        ext_lower  = file_path.suffix.lower()

        # Sensitive
        if self.is_sensitive(file_path):
            return True

        # Extension-based ignore
        if ext_lower in self.ignore_extensions:
            return True

        # Hidden files (except common dotfiles we want)
        if name_lower.startswith(".") and name_lower not in {
            ".gitignore", ".editorconfig", ".eslintrc", ".prettierrc",
            ".babelrc", ".npmrc", ".yarnrc", ".flake8",
        }:
            return True

        return False

    # ------------------------------------------------------------------ #
    # Classification
    # ------------------------------------------------------------------ #

    def is_sensitive(self, file_path: Path) -> bool:
        """Return True if the file contains credentials or secrets."""
        name_lower = file_path.name.lower()
        ext_lower  = file_path.suffix.lower()
        return name_lower in SENSITIVE_FILENAMES or ext_lower in SENSITIVE_EXTENSIONS

    def is_entry_point(self, file_path: Path) -> bool:
        """Return True if the file looks like a repository entry point."""
        return file_path.name.lower() in ENTRY_POINT_NAMES

    def is_test_file(self, file_path: Path) -> bool:
        """Return True if the file appears to be a test file."""
        name = file_path.name.lower()
        parts = [p.lower() for p in file_path.parts]

        return (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith(".test.js")
            or name.endswith(".test.ts")
            or name.endswith(".spec.js")
            or name.endswith(".spec.ts")
            or "tests" in parts
            or "test" in parts
            or "__tests__" in parts
        )

    def is_config_file(self, file_path: Path) -> bool:
        """Return True if the file is a configuration / dependency file."""
        return file_path.name.lower() in DEPENDENCY_FILES

    def is_dependency_file(self, file_path: Path) -> bool:
        """Return True if the file declares project dependencies."""
        dep_names = {
            "pyproject.toml", "setup.py", "requirements.txt", "pipfile",
            "package.json", "go.mod", "cargo.toml", "pom.xml",
            "build.gradle", "gemfile",
        }
        return file_path.name.lower() in dep_names

```

### File: `clockwork/scanner/frameworks.py`

```python
"""
clockwork/scanner/frameworks.py
---------------------------------
Framework and dependency detection from repository manifest files.

Reads:
  • requirements.txt / requirements-*.txt
  • pyproject.toml         (Python)
  • package.json           (JS / TS)
  • go.mod                 (Go)
  • cargo.toml             (Rust)
  • pom.xml / build.gradle (JVM)
  • dockerfile             (Docker)
  • docker-compose.yml     (Docker Compose)

All parsing is static — no code is executed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# ── Python framework map ───────────────────────────────────────────────────

PYTHON_FRAMEWORKS: dict[str, str] = {
    "fastapi":      "FastAPI",
    "flask":        "Flask",
    "django":       "Django",
    "starlette":    "Starlette",
    "tornado":      "Tornado",
    "aiohttp":      "aiohttp",
    "sanic":        "Sanic",
    "falcon":       "Falcon",
    "pyramid":      "Pyramid",
    "typer":        "Typer",
    "click":        "Click",
    "argparse":     "argparse",
    "sqlalchemy":   "SQLAlchemy",
    "alembic":      "Alembic",
    "pydantic":     "Pydantic",
    "celery":       "Celery",
    "dramatiq":     "Dramatiq",
    "rq":           "RQ",
    "pytest":       "pytest",
    "unittest":     "unittest",
    "numpy":        "NumPy",
    "pandas":       "Pandas",
    "scipy":        "SciPy",
    "sklearn":      "scikit-learn",
    "scikit-learn": "scikit-learn",
    "tensorflow":   "TensorFlow",
    "torch":        "PyTorch",
    "transformers": "HuggingFace Transformers",
    "langchain":    "LangChain",
    "anthropic":    "Anthropic SDK",
    "openai":       "OpenAI SDK",
    "boto3":        "AWS Boto3",
    "redis":        "Redis",
    "pymongo":      "MongoDB (pymongo)",
    "motor":        "MongoDB (motor)",
    "asyncpg":      "PostgreSQL (asyncpg)",
    "psycopg2":     "PostgreSQL (psycopg2)",
    "httpx":        "HTTPX",
    "requests":     "Requests",
    "grpcio":       "gRPC",
}

# ── JS/TS framework map ────────────────────────────────────────────────────

JS_FRAMEWORKS: dict[str, str] = {
    "react":        "React",
    "vue":          "Vue",
    "angular":      "Angular",
    "svelte":       "Svelte",
    "solid-js":     "SolidJS",
    "next":         "Next.js",
    "nuxt":         "Nuxt",
    "remix":        "Remix",
    "gatsby":       "Gatsby",
    "express":      "Express",
    "fastify":      "Fastify",
    "koa":          "Koa",
    "nestjs":       "NestJS",
    "@nestjs/core": "NestJS",
    "hono":         "Hono",
    "trpc":         "tRPC",
    "graphql":      "GraphQL",
    "prisma":       "Prisma",
    "typeorm":      "TypeORM",
    "sequelize":    "Sequelize",
    "mongoose":     "Mongoose",
    "jest":         "Jest",
    "vitest":       "Vitest",
    "playwright":   "Playwright",
    "cypress":      "Cypress",
    "vite":         "Vite",
    "webpack":      "Webpack",
    "esbuild":      "esbuild",
    "tailwindcss":  "Tailwind CSS",
}

# ── Go module map ──────────────────────────────────────────────────────────

GO_FRAMEWORKS: dict[str, str] = {
    "gin-gonic/gin":    "Gin",
    "labstack/echo":    "Echo",
    "gofiber/fiber":    "Fiber",
    "gorilla/mux":      "Gorilla Mux",
    "go-chi/chi":       "Chi",
    "beego":            "Beego",
    "gorm.io/gorm":     "GORM",
    "go.uber.org/zap":  "Zap",
    "sirupsen/logrus":  "Logrus",
    "grpc":             "gRPC",
}

# ── Rust crate map ─────────────────────────────────────────────────────────

RUST_FRAMEWORKS: dict[str, str] = {
    "actix-web":    "Actix-Web",
    "axum":         "Axum",
    "rocket":       "Rocket",
    "warp":         "Warp",
    "tokio":        "Tokio",
    "serde":        "Serde",
    "sqlx":         "SQLx",
    "diesel":       "Diesel",
    "tonic":        "Tonic (gRPC)",
}


class FrameworkDetector:
    """
    Detects frameworks and libraries used in a repository by analysing
    manifest files found during scanning.
    """

    def detect(self, repo_root: Path, file_paths: list[str]) -> list[str]:
        """
        Return a deduplicated list of framework names detected in the repo.

        *file_paths* is the list of relative paths from ScanResult.files.
        """
        file_names_lower = {Path(p).name.lower() for p in file_paths}
        detected: list[str] = []

        # Python
        if "requirements.txt" in file_names_lower:
            detected += self._parse_requirements(repo_root / "requirements.txt")
        for name in file_names_lower:
            if name.startswith("requirements") and name.endswith(".txt"):
                path = repo_root / name
                if path.exists():
                    detected += self._parse_requirements(path)
        if "pyproject.toml" in file_names_lower:
            detected += self._parse_pyproject(repo_root / "pyproject.toml")
        if "setup.py" in file_names_lower:
            detected += self._parse_setup_py(repo_root / "setup.py")

        # JavaScript / TypeScript
        if "package.json" in file_names_lower:
            detected += self._parse_package_json(repo_root / "package.json")

        # Go
        if "go.mod" in file_names_lower:
            detected += self._parse_go_mod(repo_root / "go.mod")

        # Rust
        if "cargo.toml" in file_names_lower:
            detected += self._parse_cargo_toml(repo_root / "cargo.toml")

        # Infrastructure
        if "dockerfile" in file_names_lower:
            detected.append("Docker")
        if "docker-compose.yml" in file_names_lower or "docker-compose.yaml" in file_names_lower:
            detected.append("Docker Compose")
        if any(n.endswith(".tf") or n == "terraform" for n in file_names_lower):
            detected.append("Terraform")
        if ".github" in file_names_lower or any("github/workflows" in p for p in file_paths):
            detected.append("GitHub Actions")

        # JVM
        if "pom.xml" in file_names_lower:
            detected.append("Maven")
        if "build.gradle" in file_names_lower:
            detected.append("Gradle")

        return list(dict.fromkeys(detected))  # deduplicate, preserve order

    # ------------------------------------------------------------------ #
    # Parsers
    # ------------------------------------------------------------------ #

    def _parse_requirements(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                pkg = re.split(r"[>=<!;\[]", line)[0].strip().lower()
                if pkg in PYTHON_FRAMEWORKS:
                    found.append(PYTHON_FRAMEWORKS[pkg])
        except OSError:
            pass
        return found

    def _parse_pyproject(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            for keyword, name in PYTHON_FRAMEWORKS.items():
                # Match as a quoted string in dependencies arrays
                if f'"{keyword}' in content or f"'{keyword}" in content or f"\n{keyword}" in content:
                    found.append(name)
        except OSError:
            pass
        return found

    def _parse_setup_py(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
            for keyword, name in PYTHON_FRAMEWORKS.items():
                if f'"{keyword}' in content or f"'{keyword}" in content:
                    found.append(name)
        except OSError:
            pass
        return found

    def _parse_package_json(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, json.JSONDecodeError):
            return []

        all_deps: dict[str, str] = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))
        all_deps.update(data.get("peerDependencies", {}))

        for raw_name in all_deps:
            # Strip scope: @nestjs/core → nestjs/core → check full then base
            name_lower = raw_name.lower().lstrip("@")
            if raw_name.lower() in JS_FRAMEWORKS:
                found.append(JS_FRAMEWORKS[raw_name.lower()])
            elif name_lower in JS_FRAMEWORKS:
                found.append(JS_FRAMEWORKS[name_lower])
            else:
                base = name_lower.split("/")[-1]
                if base in JS_FRAMEWORKS:
                    found.append(JS_FRAMEWORKS[base])

        return found

    def _parse_go_mod(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        for module_prefix, name in GO_FRAMEWORKS.items():
            if module_prefix in content:
                found.append(name)

        return found

    def _parse_cargo_toml(self, path: Path) -> list[str]:
        found: list[str] = []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore").lower()
        except OSError:
            return []

        for crate, name in RUST_FRAMEWORKS.items():
            if crate.lower() in content:
                found.append(name)

        return found

```

### File: `clockwork/scanner/language.py`

```python
"""
clockwork/scanner/language.py
-------------------------------
Language detection for repository files.

Detection strategy (in order of priority):
  1. Exact filename match  (e.g. Makefile, Dockerfile)
  2. File extension match
  3. Shebang line sniff    (#!/usr/bin/env python3)
  4. Content heuristics    (fallback)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


# ── Extension → language map ───────────────────────────────────────────────

EXTENSION_MAP: dict[str, str] = {
    # Python
    ".py": "Python", ".pyi": "Python", ".pyw": "Python",
    # JavaScript / TypeScript
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".mts": "TypeScript",
    # Web
    ".html": "HTML", ".htm": "HTML",
    ".css": "CSS", ".scss": "SCSS", ".sass": "SCSS", ".less": "LESS",
    # Data / Config
    ".json": "JSON", ".jsonc": "JSON",
    ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".ini": "INI", ".cfg": "INI", ".conf": "INI",
    ".xml": "XML", ".xsd": "XML", ".xsl": "XML",
    ".env": "ENV",
    # Systems
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala",
    ".swift": "Swift",
    ".m": "Objective-C",
    # Scripting
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".fish": "Shell",
    ".ps1": "PowerShell", ".psm1": "PowerShell",
    ".rb": "Ruby", ".erb": "Ruby",
    ".php": "PHP",
    ".pl": "Perl", ".pm": "Perl",
    ".lua": "Lua",
    ".r": "R", ".R": "R",
    # Data science
    ".ipynb": "Jupyter",
    # Infrastructure
    ".tf": "Terraform", ".tfvars": "Terraform",
    ".dockerfile": "Dockerfile",
    # Docs
    ".md": "Markdown", ".mdx": "Markdown",
    ".rst": "reStructuredText",
    ".tex": "LaTeX",
    # DB
    ".sql": "SQL",
    # Other
    ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir",
    ".erl": "Erlang",
    ".hs": "Haskell",
    ".clj": "Clojure",
    ".groovy": "Groovy",
    ".gradle": "Groovy",
    ".proto": "Protobuf",
    ".graphql": "GraphQL", ".gql": "GraphQL",
}

# Exact filename → language (case-insensitive)
FILENAME_MAP: dict[str, str] = {
    "makefile": "Makefile",
    "dockerfile": "Dockerfile",
    "jenkinsfile": "Groovy",
    "vagrantfile": "Ruby",
    "gemfile": "Ruby",
    "rakefile": "Ruby",
    "procfile": "Config",
    "brewfile": "Ruby",
    ".gitignore": "Config",
    ".gitattributes": "Config",
    ".editorconfig": "Config",
    ".npmrc": "Config",
    ".yarnrc": "Config",
    ".babelrc": "JSON",
    ".eslintrc": "JSON",
    ".prettierrc": "JSON",
    "pyproject.toml": "TOML",
    "cargo.toml": "TOML",
    "go.mod": "Go",
    "go.sum": "Go",
    "requirements.txt": "Config",
    "pipfile": "TOML",
    "setup.py": "Python",
    "setup.cfg": "INI",
    "tox.ini": "INI",
    "conftest.py": "Python",
}

# Shebang prefixes → language
SHEBANG_MAP: dict[str, str] = {
    "python": "Python",
    "python3": "Python",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "ruby": "Ruby",
    "perl": "Perl",
    "php": "PHP",
    "lua": "Lua",
    "rscript": "R",
}


class LanguageDetector:
    """
    Detects the programming language of a single file using a multi-strategy
    approach.  All analysis is static — no code is executed.
    """

    def detect(self, path: Path) -> str:
        """
        Return the detected language name for *path*.

        Returns ``"Other"`` when no match is found.
        """
        # 1. Exact filename
        name_lower = path.name.lower()
        if name_lower in FILENAME_MAP:
            return FILENAME_MAP[name_lower]

        # 2. Extension
        ext = path.suffix.lower()
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        # 3. No extension — try shebang
        if not ext:
            lang = self._detect_shebang(path)
            if lang:
                return lang

        return "Other"

    def _detect_shebang(self, path: Path) -> Optional[str]:
        """Read the first line and check for a shebang."""
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as fh:
                first_line = fh.readline(200).strip()
        except OSError:
            return None

        if not first_line.startswith("#!"):
            return None

        # e.g.  #!/usr/bin/env python3  or  #!/bin/bash
        parts = first_line[2:].strip().split()
        if not parts:
            return None

        interpreter = parts[-1].lower()   # handle /usr/bin/env python3
        interpreter_base = Path(interpreter).name

        return SHEBANG_MAP.get(interpreter_base)

    # ------------------------------------------------------------------ #
    # Bulk helpers
    # ------------------------------------------------------------------ #

    def detect_primary_language(self, language_counts: dict[str, int]) -> str:
        """
        Return the language with the highest file count.

        Config/data languages (YAML, JSON, TOML, Markdown, INI, Config, Other)
        are deprioritised so the primary code language surfaces.
        """
        NON_CODE = {"YAML", "JSON", "TOML", "Markdown", "INI", "Config",
                    "Other", "ENV", "reStructuredText", "LaTeX", "XML"}

        code_langs = {k: v for k, v in language_counts.items() if k not in NON_CODE}
        if code_langs:
            return max(code_langs, key=lambda k: code_langs[k])

        if language_counts:
            return max(language_counts, key=lambda k: language_counts[k])

        return ""

    @staticmethod
    def extension_for(language: str) -> list[str]:
        """Return all file extensions associated with *language*."""
        return [ext for ext, lang in EXTENSION_MAP.items() if lang == language]

```

### File: `clockwork/scanner/models.py`

```python
﻿"""
clockwork/scanner/models.py
-----------------------------
Data models for the Repository Scanner subsystem.

These models are the contract between the scanner and all downstream
subsystems (Context Engine, Rule Engine, Graph, Packaging).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── File-level model ───────────────────────────────────────────────────────

@dataclass
class SymbolInfo:
    """A named symbol (class, function, variable) found in a source file."""

    name: str
    kind: str           # "class" | "function" | "method" | "variable" | "import"
    line: int
    parent: Optional[str] = None   # enclosing class name, if any


@dataclass
class FileEntry:
    """
    Complete metadata for a single repository file.

    All fields except *path* are optional — a file may be unreadable
    or its language unsupported.
    """

    path: str                           # relative to repo root
    extension: str
    language: str
    size_bytes: int
    lines: int = 0
    is_entry_point: bool = False
    is_test: bool = False
    is_config: bool = False
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    last_modified: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Directory-level model ──────────────────────────────────────────────────

@dataclass
class DirectoryEntry:
    """Metadata for a directory node in the repository tree."""

    path: str           # relative to repo root  ("." = root)
    file_count: int = 0
    subdirectory_count: int = 0
    languages: list[str] = field(default_factory=list)
    has_init: bool = False          # Python package?
    has_tests: bool = False


# ── Language summary ───────────────────────────────────────────────────────

@dataclass
class LanguageSummary:
    """Aggregated statistics for a single detected language."""

    name: str
    file_count: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    extensions: list[str] = field(default_factory=list)

    @property
    def average_file_size(self) -> float:
        if self.file_count == 0:
            return 0.0
        return self.total_bytes / self.file_count


# ── Top-level scan result ──────────────────────────────────────────────────

@dataclass
class ScanResult:
    """
    Complete result of a full repository scan.

    This is the canonical data structure written to .clockwork/repo_map.json
    and consumed by all downstream Clockwork subsystems.
    """

    # Identity
    scanned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    root: str = ""
    project_name: str = ""
    clockwork_version: str = "0.1"

    # Counts
    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0

    # Languages
    primary_language: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    language_details: list[LanguageSummary] = field(default_factory=list)

    # Structure
    files: list[FileEntry] = field(default_factory=list)
    directories: list[DirectoryEntry] = field(default_factory=list)
    directory_tree: dict[str, list[str]] = field(default_factory=dict)

    # Key items
    entry_points: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)

    # Framework / dependency hints
    frameworks: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        """Reconstruct from a plain dict (e.g. loaded from repo_map.json)."""
        # Rebuild nested models
        files = [
            FileEntry(
                **{k: v for k, v in f.items()
                   if k != "symbols"},
                symbols=[SymbolInfo(**s) for s in f.get("symbols", [])],
            )
            for f in data.get("files", [])
        ]
        dirs = [DirectoryEntry(**d) for d in data.get("directories", [])]
        lang_details = [
            LanguageSummary(**l) for l in data.get("language_details", [])
        ]
        import dataclasses as _dc
        _known = {f.name for f in _dc.fields(cls)}
        top = {
            k: v for k, v in data.items()
            if k not in ("files", "directories", "language_details") and k in _known
        }
        return cls(**top, files=files, directories=dirs, language_details=lang_details)

    @classmethod
    def from_json(cls, raw: str) -> "ScanResult":
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, clockwork_dir: Path) -> Path:
        """Write repo_map.json into *clockwork_dir*."""
        out = clockwork_dir / "repo_map.json"
        out.write_text(self.to_json(), encoding="utf-8")
        return out

    @classmethod
    def load(cls, clockwork_dir: Path) -> "ScanResult":
        """Load repo_map.json from *clockwork_dir*."""
        path = clockwork_dir / "repo_map.json"
        return cls.from_json(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ #
    # Derived queries
    # ------------------------------------------------------------------ #

    def files_by_language(self, language: str) -> list[FileEntry]:
        return [f for f in self.files if f.language == language]

    def entry_point_files(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_entry_point]

    def test_file_entries(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_test]

    def config_file_entries(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_config]

```

### File: `clockwork/scanner/repository_scanner.py`

```python
﻿"""Repository Scanner."""
import json, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

IGNORED_DIRS = {".git",".clockwork","__pycache__","node_modules",".venv","venv"}
IGNORED_FILES = {".env","credentials.json","secrets.json"}
LANGUAGE_MAP: dict[str,str] = {".py":"Python",".js":"JavaScript",".ts":"TypeScript",".java":"Java",".go":"Go",".rs":"Rust",".cs":"C#",".cpp":"C++",".c":"C",".rb":"Ruby",".php":"PHP",".html":"HTML",".css":"CSS",".json":"JSON",".yaml":"YAML",".yml":"YAML",".md":"Markdown",".sh":"Shell",".ps1":"PowerShell",".sql":"SQL"}

class RepositoryScanner:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.clockwork_dir = repo_path / ".clockwork"

    def scan(self) -> dict[str, Any]:
        files: list[dict[str,Any]] = []
        lang_counts: dict[str,int] = {}
        for root, dirs, filenames in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fn in filenames:
                if fn in IGNORED_FILES: continue
                fp = Path(root) / fn
                rel = fp.relative_to(self.repo_path)
                lang = LANGUAGE_MAP.get(fp.suffix.lower(), "Unknown")
                try:
                    import hashlib as _hl
                    _fhash = _hl.sha256(fp.read_bytes()).hexdigest()
                    _fsize = fp.stat().st_size
                except OSError:
                    _fhash = ""
                    _fsize = 0
                files.append({"path": str(rel), "language": lang, "size_bytes": _fsize, "file_hash": _fhash})
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        languages: dict[str, int] = {l: c for l, c in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True) if l != "Unknown"}
        result: dict[str,Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "total_files": len(files), "languages": languages, "files": files}
        (self.clockwork_dir / "repo_map.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

```

### File: `clockwork/scanner/scanner.py`

```python
"""
clockwork/scanner/scanner.py
------------------------------
RepositoryScanner — the main orchestrator for the scan subsystem.

Scan pipeline:
  1. Walk repository tree
  2. Filter directories and files
  3. Classify each file (entry point / test / config)
  4. Detect language per file
  5. Count lines and bytes
  6. Extract symbols and imports (Python + JS/TS + Go + Java)
  7. Detect frameworks from dependency manifests
  8. Aggregate language statistics
  9. Build directory tree
  10. Produce ScanResult

All operations are static — no code is executed.
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from clockwork.scanner.filters import ScanFilter, DEPENDENCY_FILES
from clockwork.scanner.frameworks import FrameworkDetector
from clockwork.scanner.language import LanguageDetector
from clockwork.scanner.models import (
    DirectoryEntry,
    FileEntry,
    LanguageSummary,
    ScanResult,
    SymbolInfo,
)
from clockwork.scanner.symbols import SymbolExtractor


class RepositoryScanner:
    """
    Performs a full static analysis of a repository.

    Usage::

        scanner = RepositoryScanner(repo_root=Path("/path/to/repo"))
        result  = scanner.scan()
        result.save(Path("/path/to/repo/.clockwork"))
    """

    # Maximum file size to attempt symbol extraction (bytes)
    MAX_SYMBOL_EXTRACT_SIZE = 512_000   # 512 KB

    def __init__(
        self,
        repo_root: Path,
        extract_symbols: bool = True,
        verbose: bool = False,
    ) -> None:
        self.repo_root = repo_root.resolve()
        self.extract_symbols = extract_symbols
        self.verbose = verbose

        # Load config-driven ignore rules if .clockwork/config.yaml exists
        extra_ignore_dirs, extra_ignore_exts = self._load_config_ignores()

        self._filter     = ScanFilter(extra_ignore_dirs, extra_ignore_exts)
        self._lang       = LanguageDetector()
        self._symbols    = SymbolExtractor()
        self._frameworks = FrameworkDetector()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def scan(self) -> ScanResult:
        """
        Execute the full scan pipeline and return a ScanResult.

        This is the only public method external code needs to call.
        """
        start = time.perf_counter()

        if self.verbose:
            print(f"Scanning: {self.repo_root}")

        files: list[FileEntry]       = []
        directories: list[DirectoryEntry] = []
        lang_counts: dict[str, int]  = defaultdict(int)
        lang_details: dict[str, LanguageSummary] = {}
        dir_tree: dict[str, list[str]] = defaultdict(list)

        entry_points: list[str]  = []
        test_files: list[str]    = []
        config_files: list[str]  = []
        dep_files: list[str]     = []

        # ── Walk the tree ──────────────────────────────────────────────
        for abs_path in sorted(self.repo_root.rglob("*")):

            # Skip ignored directories
            if abs_path.is_dir():
                if self._filter.should_skip_directory(abs_path, self.repo_root):
                    continue
                continue   # directories processed at end from dir_tree

            if not abs_path.is_file():
                continue

            # Skip files in ignored dirs
            if self._filter.should_skip_directory(abs_path.parent, self.repo_root):
                continue

            # Skip filtered-out files
            if self._filter.should_skip_file(abs_path):
                continue

            rel = str(abs_path.relative_to(self.repo_root))

            # Language
            language = self._lang.detect(abs_path)

            # Size / lines
            size_bytes = 0
            line_count = 0
            try:
                size_bytes = abs_path.stat().st_size
                if language not in {"Other"} and size_bytes < self.MAX_SYMBOL_EXTRACT_SIZE:
                    line_count = _count_lines(abs_path)
            except OSError:
                pass

            # Classification
            is_entry  = self._filter.is_entry_point(abs_path)
            is_test   = self._filter.is_test_file(abs_path)
            is_config = self._filter.is_config_file(abs_path)
            is_dep    = self._filter.is_dependency_file(abs_path)

            # Last modified timestamp
            try:
                mtime = datetime.fromtimestamp(
                    abs_path.stat().st_mtime, tz=timezone.utc
                ).isoformat()
            except OSError:
                mtime = None

            # Symbol extraction
            symbols: list[SymbolInfo] = []
            imports: list[str] = []
            if (
                self.extract_symbols
                and size_bytes <= self.MAX_SYMBOL_EXTRACT_SIZE
                and language in {"Python", "JavaScript", "TypeScript", "Go", "Java"}
            ):
                symbols, imports = self._symbols.extract(abs_path, language)

            # Build FileEntry
            entry = FileEntry(
                path=rel,
                extension=abs_path.suffix.lower(),
                language=language,
                size_bytes=size_bytes,
                lines=line_count,
                is_entry_point=is_entry,
                is_test=is_test,
                is_config=is_config,
                symbols=symbols,
                imports=imports,
                last_modified=mtime,
            )
            files.append(entry)

            # Accumulators
            if language != "Other":
                lang_counts[language] += 1
                if language not in lang_details:
                    lang_details[language] = LanguageSummary(
                        name=language,
                        extensions=[abs_path.suffix.lower()],
                    )
                ls = lang_details[language]
                ls.file_count += 1
                ls.total_lines += line_count
                ls.total_bytes += size_bytes
                if abs_path.suffix.lower() not in ls.extensions:
                    ls.extensions.append(abs_path.suffix.lower())

            parent_rel = str(abs_path.parent.relative_to(self.repo_root)) or "."
            dir_tree[parent_rel].append(abs_path.name)

            if is_entry:  entry_points.append(rel)
            if is_test:   test_files.append(rel)
            if is_config: config_files.append(rel)
            if is_dep:    dep_files.append(rel)

        # ── Build directory entries ────────────────────────────────────
        for dir_rel, members in dir_tree.items():
            abs_dir = self.repo_root / dir_rel
            subdirs = [
                d.name for d in abs_dir.iterdir()
                if d.is_dir() and not self._filter.should_skip_directory(d, self.repo_root)
            ] if abs_dir.exists() else []

            member_langs = list({
                f.language for f in files
                if str(Path(f.path).parent) == dir_rel and f.language != "Other"
            })

            directories.append(DirectoryEntry(
                path=dir_rel,
                file_count=len(members),
                subdirectory_count=len(subdirs),
                languages=member_langs,
                has_init="__init__.py" in members,
                has_tests=any(
                    self._filter.is_test_file(Path(m)) for m in members
                ),
            ))

        # ── Framework detection ────────────────────────────────────────
        all_rel_paths = [f.path for f in files]
        frameworks = self._frameworks.detect(self.repo_root, all_rel_paths)

        # ── Primary language ───────────────────────────────────────────
        primary = self._lang.detect_primary_language(dict(lang_counts))

        elapsed = time.perf_counter() - start

        if self.verbose:
            print(
                f"Scan complete: {len(files)} files, "
                f"{len(lang_counts)} languages, "
                f"{elapsed*1000:.0f} ms"
            )

        return ScanResult(
            scanned_at=datetime.now(timezone.utc).isoformat(),
            root=str(self.repo_root),
            project_name=self.repo_root.name,
            clockwork_version="0.1",
            total_files=len(files),
            total_lines=sum(f.lines for f in files),
            total_bytes=sum(f.size_bytes for f in files),
            primary_language=primary,
            languages=dict(sorted(lang_counts.items(), key=lambda x: -x[1])),
            language_details=list(lang_details.values()),
            files=files,
            directories=directories,
            directory_tree=dict(dir_tree),
            entry_points=entry_points,
            test_files=test_files,
            config_files=config_files,
            frameworks=frameworks,
            dependency_files=dep_files,
        )

    # ------------------------------------------------------------------ #
    # Config loading
    # ------------------------------------------------------------------ #

    def _load_config_ignores(self) -> tuple[set[str], set[str]]:
        """Read extra ignore rules from .clockwork/config.yaml if present."""
        config_path = self.repo_root / ".clockwork" / "config.yaml"
        try:
            if config_path.exists():
                cfg = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
                scanner_cfg = cfg.get("scanner", {})
                dirs = set(scanner_cfg.get("ignore_dirs", []))
                exts = set(scanner_cfg.get("ignore_extensions", []))
                return dirs, exts
        except Exception:
            pass
        return set(), set()


# ── Helpers ────────────────────────────────────────────────────────────────

def _count_lines(path: Path) -> int:
    """Count newlines in a file. Returns 0 on read error."""
    try:
        with path.open("rb") as fh:
            return sum(chunk.count(b"\n") for chunk in iter(lambda: fh.read(65_536), b""))
    except OSError:
        return 0

```

### File: `clockwork/scanner/symbols.py`

```python
"""
clockwork/scanner/symbols.py
------------------------------
Static symbol extractor for Python source files.

Uses the stdlib ``ast`` module — no external dependencies.
Extracts:
  • top-level and nested class definitions
  • top-level and method-level function definitions
  • import statements (import X / from X import Y)

For non-Python files a lightweight regex-based fallback is used to
extract function/class-like constructs from common languages.

All analysis is static — no code is executed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Optional

from clockwork.scanner.models import SymbolInfo


class SymbolExtractor:
    """
    Extracts named symbols from source files.

    Usage::

        extractor = SymbolExtractor()
        symbols, imports = extractor.extract(path)
    """

    def extract(
        self, path: Path, language: str = ""
    ) -> tuple[list[SymbolInfo], list[str]]:
        """
        Return (symbols, imports) for the given file.

        Falls back to an empty result if the file cannot be parsed.
        """
        lang = language.lower() if language else ""

        if lang == "python" or path.suffix.lower() in (".py", ".pyi"):
            return self._extract_python(path)

        if lang in ("javascript", "typescript") or path.suffix.lower() in (
            ".js", ".ts", ".jsx", ".tsx", ".mjs"
        ):
            return self._extract_js_ts(path)

        if lang == "go" or path.suffix.lower() == ".go":
            return self._extract_go(path)

        if lang == "java" or path.suffix.lower() == ".java":
            return self._extract_java(path)

        return [], []

    # ------------------------------------------------------------------ #
    # Python — ast-based
    # ------------------------------------------------------------------ #

    def _extract_python(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(path))
        except (OSError, SyntaxError):
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        # Track which function nodes are methods so we can skip them in the
        # top-level walk (ast.walk visits all nodes regardless of nesting).
        method_nodes: set[int] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                symbols.append(
                    SymbolInfo(name=node.name, kind="class", line=node.lineno)
                )
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append(
                            SymbolInfo(
                                name=item.name,
                                kind="method",
                                line=item.lineno,
                                parent=node.name,
                            )
                        )
                        method_nodes.add(id(item))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if id(node) not in method_nodes:
                    symbols.append(
                        SymbolInfo(name=node.name, kind="function", line=node.lineno)
                    )

            # Imports
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        # Deduplicate imports while preserving order
        seen: set[str] = set()
        unique_imports = []
        for imp in imports:
            if imp not in seen:
                seen.add(imp)
                unique_imports.append(imp)

        return symbols, unique_imports

    # ------------------------------------------------------------------ #
    # JavaScript / TypeScript — regex-based
    # ------------------------------------------------------------------ #

    _JS_CLASS_RE    = re.compile(r"^(?:export\s+)?class\s+(\w+)", re.MULTILINE)
    _JS_FUNC_RE     = re.compile(
        r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE
    )
    _JS_ARROW_RE    = re.compile(
        r"^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(", re.MULTILINE
    )
    _JS_IMPORT_RE   = re.compile(
        r"""^import\s+(?:.*?\s+from\s+)?['"]([^'"]+)['"]""", re.MULTILINE
    )

    def _extract_js_ts(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._JS_CLASS_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._JS_FUNC_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JS_ARROW_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JS_IMPORT_RE.finditer(source):
            imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))

    # ------------------------------------------------------------------ #
    # Go — regex-based
    # ------------------------------------------------------------------ #

    _GO_FUNC_RE   = re.compile(r"^func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(", re.MULTILINE)
    _GO_STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct", re.MULTILINE)
    _GO_IMPORT_RE = re.compile(r'"([^"]+)"')

    def _extract_go(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._GO_STRUCT_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._GO_FUNC_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        # Go imports — handle both block and single-line forms
        import_block = re.search(r'import\s*\(([^)]+)\)', source, re.DOTALL)
        if import_block:
            for m in self._GO_IMPORT_RE.finditer(import_block.group(1)):
                imports.append(m.group(1))
        else:
            # Single-line: import "pkg"
            for m in re.finditer(r'^\s*import\s+"([^"]+)"', source, re.MULTILINE):
                imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))

    # ------------------------------------------------------------------ #
    # Java — regex-based
    # ------------------------------------------------------------------ #

    _JAVA_CLASS_RE  = re.compile(
        r"(?:public|private|protected|abstract|final)?\s*class\s+(\w+)", re.MULTILINE
    )
    _JAVA_METHOD_RE = re.compile(
        r"(?:public|private|protected|static|final|abstract|synchronized|\s)+\s+\w[\w<>\[\]]*\s+(\w+)\s*\(",
        re.MULTILINE,
    )
    _JAVA_IMPORT_RE = re.compile(r"^import\s+([\w.]+);", re.MULTILINE)

    def _extract_java(
        self, path: Path
    ) -> tuple[list[SymbolInfo], list[str]]:
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return [], []

        symbols: list[SymbolInfo] = []
        imports: list[str] = []

        for m in self._JAVA_CLASS_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="class", line=line))

        for m in self._JAVA_METHOD_RE.finditer(source):
            line = source[: m.start()].count("\n") + 1
            symbols.append(SymbolInfo(name=m.group(1), kind="function", line=line))

        for m in self._JAVA_IMPORT_RE.finditer(source):
            imports.append(m.group(1))

        return symbols, list(dict.fromkeys(imports))

```

### File: `clockwork/security/__init__.py`

```python
﻿"""
clockwork/security/__init__.py
--------------------------------
Security and Sandboxing subsystem (spec §13).

Protects the repository, developer machine, and Clockwork runtime
from malicious plugins, unsafe agent output, sensitive data exposure,
and repository corruption.

Public API::

    from clockwork.security import SecurityEngine, SecurityViolation

    sec = SecurityEngine(repo_root=Path("."))

    # validate a path
    sec.guard.check_path("/etc/passwd")       # raises SecurityViolation

    # scan for issues
    result = sec.scan()

    # full audit
    report = sec.audit()

    # check proposed changes from an agent
    safe, violations = sec.check_proposed_changes(
        ["modify backend/auth.py", "delete .env"],
        agent="claude_code",
    )

CLI commands added:
    clockwork security scan
    clockwork security audit
    clockwork security log
    clockwork security verify <plugin_path>
"""

from clockwork.security.security_engine import SecurityEngine, PluginVerifier
from clockwork.security.file_guard import FileGuard, SecurityViolation
from clockwork.security.logger import SecurityLogger
from clockwork.security.models import (
    Permission, RiskLevel, SecurityEvent,
    SecurityLogEntry, SecurityScanResult, PluginManifest,
)

__all__ = [
    "SecurityEngine",
    "PluginVerifier",
    "FileGuard",
    "SecurityViolation",
    "SecurityLogger",
    "Permission",
    "RiskLevel",
    "SecurityEvent",
    "SecurityLogEntry",
    "SecurityScanResult",
    "PluginManifest",
]


```

### File: `clockwork/security/file_guard.py`

```python
﻿"""
clockwork/security/file_guard.py
----------------------------------
File access guard (spec §5, §6, §8).

Enforces:
  - allowed path restrictions (repo root + .clockwork only)
  - sensitive file protection (.env, credentials, keys)
  - protected core file detection
  - dangerous command blocking
  - path traversal prevention
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from .logger import SecurityLogger
from .models import RiskLevel, SecurityEvent


# ── Sensitive file patterns (spec §6) ─────────────────────────────────────

SENSITIVE_FILENAMES: frozenset[str] = frozenset({
    ".env", ".env.local", ".env.production", ".env.development",
    ".env.staging", ".env.test",
    "credentials.json", "credentials.yaml", "credentials.yml",
    "secrets.json", "secrets.yaml", "secrets.yml",
    "secret.json", "secret.yaml",
    ".netrc", ".htpasswd",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
    "id_rsa.pub", "id_ed25519.pub",
    "private_key.pem", "private.pem", "privkey.pem",
    "server.key", "client.key",
    "aws_credentials", "gcloud_credentials.json",
    "service_account.json",
})

SENSITIVE_EXTENSIONS: frozenset[str] = frozenset({
    ".pem", ".key", ".p12", ".pfx", ".pkcs12",
    ".cer", ".crt",
})

SENSITIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\.env(\.|$)"),          # .env, .env.local, etc.
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"password", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"private[_\-]?key", re.IGNORECASE),
]

# ── Protected Clockwork core files ─────────────────────────────────────────

PROTECTED_CLOCKWORK_FILES: frozenset[str] = frozenset({
    ".clockwork/context.yaml",
    ".clockwork/repo_map.json",
    ".clockwork/rules.yaml",
    ".clockwork/rules.md",
    ".clockwork/handoff/handoff.json",
})

# ── Dangerous command fragments (spec §8) ─────────────────────────────────

DANGEROUS_COMMANDS: list[re.Pattern] = [
    re.compile(r"rm\s+-rf\s*/"),
    re.compile(r"rm\s+-rf\s+[~\\]"),
    re.compile(r"chmod\s+[0-7]{3,4}\s+/"),
    re.compile(r"chown\s+.*\s+/"),
    re.compile(r"mkfs"),
    re.compile(r"dd\s+if="),
    re.compile(r":\(\)\s*\{.*\}"),          # fork bomb
    re.compile(r"nmap\b"),
    re.compile(r"netcat\b|nc\s+-[lLe]"),
    re.compile(r"curl.*\|\s*(?:ba)?sh"),    # curl | bash
    re.compile(r"wget.*\|\s*(?:ba)?sh"),
    re.compile(r"eval\s*\("),
    re.compile(r"exec\s*\("),
    re.compile(r"/etc/passwd"),
    re.compile(r"/etc/shadow"),
]

# ── System restricted paths ────────────────────────────────────────────────

SYSTEM_RESTRICTED_PREFIXES: tuple[str, ...] = (
    "/etc/", "/sys/", "/proc/", "/boot/", "/dev/",
    "/usr/bin/", "/usr/lib/", "/usr/sbin/",
    "/bin/", "/sbin/", "/lib/",
    "C:\\Windows\\", "C:\\Program Files\\",
    "C:\\ProgramData\\",
)


class FileGuard:
    """
    Validates file paths and commands against security policies.

    Usage::

        guard = FileGuard(repo_root, clockwork_dir)
        guard.check_path("/etc/passwd")        # raises SecurityViolation
        guard.check_sensitive("credentials.json")  # raises SecurityViolation
        guard.check_command("rm -rf /")        # raises SecurityViolation
    """

    def __init__(
        self,
        repo_root: Path,
        clockwork_dir: Path,
        logger: Optional[SecurityLogger] = None,
        agent: str = "",
    ) -> None:
        self.repo_root    = repo_root.resolve()
        self.clockwork_dir = clockwork_dir.resolve()
        self.logger       = logger
        self.agent        = agent

    # ── path validation (spec §5) ──────────────────────────────────────────

    def is_allowed_path(self, path: str) -> bool:
        """Return True if path is within the allowed scope."""
        try:
            resolved = Path(path).resolve()
        except Exception:
            return False

        # must be under repo root or .clockwork
        if str(resolved).startswith(str(self.repo_root)):
            return True
        if str(resolved).startswith(str(self.clockwork_dir)):
            return True
        return False

    def check_path(self, path: str) -> None:
        """
        Raise SecurityViolation if path is outside allowed scope
        or is a system restricted path.
        """
        # path traversal check
        if ".." in path and not self.is_allowed_path(path):
            if self.logger:
                self.logger.log_path_traversal(path, self.agent)
            raise SecurityViolation(
                f"Path traversal attempt blocked: {path}"
            )

        # system restricted prefixes
        norm = path.replace("\\", "/")
        for prefix in SYSTEM_RESTRICTED_PREFIXES:
            if norm.startswith(prefix.replace("\\", "/")):
                if self.logger:
                    self.logger.log_blocked_file(path, self.agent)
                raise SecurityViolation(
                    f"Access to system path blocked: {path}"
                )

        if not self.is_allowed_path(path):
            if self.logger:
                self.logger.log_blocked_file(path, self.agent)
            raise SecurityViolation(
                f"Path outside allowed scope: {path}"
            )

    # ── sensitive file detection (spec §6) ────────────────────────────────

    def is_sensitive(self, file_path: str) -> bool:
        """Return True if the file is sensitive and should be protected."""
        name = Path(file_path).name.lower()
        ext  = Path(file_path).suffix.lower()

        if name in SENSITIVE_FILENAMES:
            return True
        if ext in SENSITIVE_EXTENSIONS:
            return True
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(name):
                return True
        return False

    def check_sensitive(self, file_path: str) -> None:
        """Raise SecurityViolation if file_path is sensitive."""
        if self.is_sensitive(file_path):
            if self.logger:
                self.logger.log_sensitive_access(file_path, self.agent)
            raise SecurityViolation(
                f"Access to sensitive file blocked: {file_path}"
            )

    # ── protected file detection ───────────────────────────────────────────

    def is_protected(self, file_path: str) -> bool:
        """Return True if file_path is a protected Clockwork core file."""
        norm = file_path.replace("\\", "/")
        return any(norm.endswith(pf) for pf in PROTECTED_CLOCKWORK_FILES)

    def check_protected(self, file_path: str) -> None:
        """Raise SecurityViolation if attempting to modify a protected file."""
        if self.is_protected(file_path):
            if self.logger:
                self.logger.log_protected_file_attempt(file_path, self.agent)
            raise SecurityViolation(
                f"Modification of protected file blocked: {file_path}"
            )

    # ── command validation (spec §8) ──────────────────────────────────────

    def is_dangerous_command(self, command: str) -> bool:
        """Return True if command matches a dangerous pattern."""
        for pattern in DANGEROUS_COMMANDS:
            if pattern.search(command):
                return True
        return False

    def check_command(self, command: str) -> None:
        """Raise SecurityViolation if command is dangerous."""
        if self.is_dangerous_command(command):
            if self.logger:
                self.logger.log_dangerous_command(command, self.agent)
            raise SecurityViolation(
                f"Dangerous command blocked: {command[:80]}"
            )

    # ── permission check (spec §13) ───────────────────────────────────────

    def check_permission(
        self,
        requested: str,
        granted: set[str],
    ) -> None:
        """Raise SecurityViolation if requested permission not in granted set."""
        if requested not in granted:
            if self.logger:
                self.logger.log_permission_denied(requested, self.agent)
            raise SecurityViolation(
                f"Permission '{requested}' not granted to agent '{self.agent}'"
            )


class SecurityViolation(Exception):
    """Raised when a security policy is violated."""


```

### File: `clockwork/security/logger.py`

```python
﻿"""
clockwork/security/logger.py
-----------------------------
Security event logger (spec §11).

All security events are written to .clockwork/security_log.json
so developers can audit what Clockwork blocked or flagged.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import RiskLevel, SecurityEvent, SecurityLogEntry


class SecurityLogger:
    """
    Appends security events to .clockwork/security_log.json.

    Usage::

        logger = SecurityLogger(clockwork_dir)
        logger.log_blocked_file("/etc/passwd", agent="claude")
        logger.log_sensitive_access(".env")
    """

    def __init__(self, clockwork_dir: Path) -> None:
        self.log_path = clockwork_dir / "security_log.json"

    # ── write ──────────────────────────────────────────────────────────────

    def log(self, entry: SecurityLogEntry) -> None:
        """Append one entry to security_log.json."""
        entries = self._read()
        entries.append(entry.to_dict())
        self.log_path.write_text(
            json.dumps(entries, indent=2), encoding="utf-8"
        )

    def log_blocked_file(
        self, file_path: str, agent: str = "", detail: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.BLOCKED_FILE_ACCESS,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=detail or f"Access to restricted path blocked: {file_path}",
        ))

    def log_sensitive_access(
        self, file_path: str, agent: str = "", blocked: bool = True
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.SENSITIVE_FILE_ACCESS,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=f"Attempt to access sensitive file: {file_path}",
            blocked=blocked,
        ))

    def log_dangerous_command(
        self, command: str, agent: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.DANGEROUS_COMMAND,
            risk_level=RiskLevel.CRITICAL,
            detail=f"Dangerous command blocked: {command}",
            agent=agent,
        ))

    def log_protected_file_attempt(
        self, file_path: str, agent: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PROTECTED_FILE_ATTEMPT,
            risk_level=RiskLevel.HIGH,
            file=file_path,
            agent=agent,
            detail=f"Attempt to modify protected file: {file_path}",
        ))

    def log_permission_denied(
        self, permission: str, agent: str = "", detail: str = ""
    ) -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PERMISSION_DENIED,
            risk_level=RiskLevel.MEDIUM,
            agent=agent,
            detail=detail or f"Permission denied: {permission}",
        ))

    def log_path_traversal(self, path: str, agent: str = "") -> None:
        self.log(SecurityLogEntry.now(
            event=SecurityEvent.PATH_TRAVERSAL,
            risk_level=RiskLevel.CRITICAL,
            file=path,
            agent=agent,
            detail=f"Path traversal attempt detected: {path}",
        ))

    # ── read ───────────────────────────────────────────────────────────────

    def read_log(self) -> list[dict[str, Any]]:
        return self._read()

    def recent(self, n: int = 20) -> list[dict[str, Any]]:
        return self._read()[-n:]

    def _read(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            return json.loads(self.log_path.read_text(encoding="utf-8"))
        except Exception:
            return []


```

### File: `clockwork/security/models.py`

```python
﻿"""
clockwork/security/models.py
-----------------------------
Data models for the Security and Sandboxing subsystem (spec §13).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


# ── Permission constants (spec §13) ───────────────────────────────────────

class Permission:
    FILESYSTEM_READ   = "filesystem_read"
    REPOSITORY_WRITE  = "repository_write"
    NETWORK_ACCESS    = "network_access"
    PLUGIN_EXECUTE    = "plugin_execute"
    SYSTEM_COMMAND    = "system_command"

    # safe default set — no write, no network, no system commands
    SAFE_DEFAULT = {FILESYSTEM_READ}
    ALL = {FILESYSTEM_READ, REPOSITORY_WRITE, NETWORK_ACCESS, PLUGIN_EXECUTE, SYSTEM_COMMAND}


# ── Security event types ───────────────────────────────────────────────────

class SecurityEvent:
    BLOCKED_FILE_ACCESS    = "blocked_file_access"
    SENSITIVE_FILE_ACCESS  = "sensitive_file_access"
    DANGEROUS_COMMAND      = "dangerous_command_blocked"
    PERMISSION_DENIED      = "permission_denied"
    PROTECTED_FILE_ATTEMPT = "protected_file_modification_attempt"
    PLUGIN_BLOCKED         = "plugin_blocked"
    PATH_TRAVERSAL         = "path_traversal_attempt"
    SCAN_COMPLETED         = "security_scan_completed"
    AUDIT_COMPLETED        = "security_audit_completed"


# ── Risk levels ────────────────────────────────────────────────────────────

class RiskLevel:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ── Security log entry (spec §11) ──────────────────────────────────────────

@dataclass
class SecurityLogEntry:
    """One record written to .clockwork/security_log.json."""

    timestamp:   str
    event:       str           # SecurityEvent constant
    risk_level:  str           # RiskLevel constant
    file:        str = ""
    agent:       str = ""
    detail:      str = ""
    blocked:     bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp":  self.timestamp,
            "event":      self.event,
            "risk_level": self.risk_level,
            "file":       self.file,
            "agent":      self.agent,
            "detail":     self.detail,
            "blocked":    self.blocked,
        }

    @classmethod
    def now(
        cls,
        event: str,
        risk_level: str = RiskLevel.MEDIUM,
        **kwargs: Any,
    ) -> "SecurityLogEntry":
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            risk_level=risk_level,
            **kwargs,
        )


# ── Security scan result ───────────────────────────────────────────────────

@dataclass
class SecurityScanResult:
    """Result of `clockwork security scan`."""

    passed:        bool
    risk_level:    str                    = RiskLevel.LOW
    issues:        list[str]              = field(default_factory=list)
    warnings:      list[str]              = field(default_factory=list)
    sensitive_files_found: list[str]      = field(default_factory=list)
    protected_files_ok:    bool           = True
    elapsed_ms:    float                  = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed":               self.passed,
            "risk_level":           self.risk_level,
            "issues":               self.issues,
            "warnings":             self.warnings,
            "sensitive_files_found": self.sensitive_files_found,
            "protected_files_ok":   self.protected_files_ok,
            "elapsed_ms":           round(self.elapsed_ms, 1),
        }


# ── Plugin manifest (spec §12) ─────────────────────────────────────────────

@dataclass
class PluginManifest:
    """Declared metadata every plugin must supply."""

    name:               str
    version:            str
    author:             str         = ""
    description:        str         = ""
    requires_clockwork: str         = ">=0.1"
    permissions:        list[str]   = field(default_factory=list)
    checksum:           str         = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":               self.name,
            "version":            self.version,
            "author":             self.author,
            "description":        self.description,
            "requires_clockwork": self.requires_clockwork,
            "permissions":        self.permissions,
            "checksum":           self.checksum,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PluginManifest":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            author=d.get("author", ""),
            description=d.get("description", ""),
            requires_clockwork=d.get("requires_clockwork", ">=0.1"),
            permissions=d.get("permissions", []),
            checksum=d.get("checksum", ""),
        )


```

### File: `clockwork/security/scanner.py`

```python
﻿"""
clockwork/security/scanner.py
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from typing import Any
from .file_guard import FileGuard
from .logger import SecurityLogger
from .models import RiskLevel, SecurityEvent, SecurityLogEntry, SecurityScanResult

_DANGEROUS_CODE_PATTERNS = [
    (r"exec\s*\(", "exec() call detected", RiskLevel.HIGH),
    (r"eval\s*\(", "eval() call detected", RiskLevel.HIGH),
    (r"__import__\s*\(", "Dynamic import detected", RiskLevel.MEDIUM),
    (r"subprocess\.call|subprocess\.run|os\.system", "Shell execution detected", RiskLevel.MEDIUM),
    (r"open\s*\(\s*['\"]\/etc", "Access to /etc in code", RiskLevel.HIGH),
    (r"socket\.connect", "Raw socket connection detected", RiskLevel.MEDIUM),
    (r"pickle\.loads", "Unsafe pickle.loads detected", RiskLevel.HIGH),
    (r"yaml\.load\s*\((?!.*Loader)", "Unsafe yaml.load (no Loader)", RiskLevel.MEDIUM),
]

_CODE_SCAN_SKIP: frozenset[str] = frozenset({
    "clockwork/security/scanner.py",
    "clockwork/security/file_guard.py",
    "tests/test_security.py",
})

def _in_skip_set(rel: str) -> bool:
    """Check skip set normalising separators so it works on Windows too."""
    normalised = rel.replace("\\", "/")
    return normalised in _CODE_SCAN_SKIP

PROTECTED_CLOCKWORK_FILES: frozenset[str] = frozenset({
    ".clockwork/context.yaml",
    ".clockwork/repo_map.json",
    ".clockwork/handoff/handoff.json",
})

def _compute_risk(issues, warnings):
    if len(issues) >= 5: return RiskLevel.CRITICAL
    if len(issues) >= 2: return RiskLevel.HIGH
    if len(issues) == 1: return RiskLevel.MEDIUM
    if warnings:         return RiskLevel.LOW
    return RiskLevel.LOW

class SecurityScanner:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.logger        = SecurityLogger(self.clockwork_dir)
        self.guard         = FileGuard(self.repo_root, self.clockwork_dir, self.logger)

    def scan(self) -> SecurityScanResult:
        t0 = time.perf_counter()
        issues: list[str] = []; warnings: list[str] = []; sensitive_found: list[str] = []
        for root_dir, dirs, files in os.walk(str(self.repo_root)):
            dirs[:] = [d for d in dirs if d not in {".git","__pycache__","node_modules",".venv","venv","dist","build"}]
            for fname in files:
                abs_path = os.path.join(root_dir, fname)
                try:
                    rel = str(Path(abs_path).relative_to(self.repo_root)).replace("\\", "/")
                except ValueError:
                    continue
                if self.guard.is_sensitive(rel):
                    sensitive_found.append(rel)
                    self.logger.log_sensitive_access(rel, blocked=False)
                    issues.append(f"Sensitive file found in repo: {rel}")
                if fname.endswith(".py") and not _in_skip_set(rel):
                    try:
                        content = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
                        for pattern, msg, level in _DANGEROUS_CODE_PATTERNS:
                            if re.search(pattern, content):
                                entry = f"{msg} in {rel}"
                                if level == RiskLevel.HIGH: issues.append(entry)
                                else:                       warnings.append(entry)
                    except OSError:
                        pass
        protected_ok = self._check_protected_files(issues, warnings)
        elapsed = (time.perf_counter() - t0) * 1000
        self.logger.log(SecurityLogEntry.now(
            event=SecurityEvent.SCAN_COMPLETED,
            risk_level=RiskLevel.HIGH if issues else RiskLevel.LOW,
            detail=f"Scan completed: {len(issues)} issues, {len(warnings)} warnings",
            blocked=False,
        ))
        risk = _compute_risk(issues, warnings)
        return SecurityScanResult(passed=len(issues)==0, risk_level=risk, issues=issues,
            warnings=warnings, sensitive_files_found=sensitive_found,
            protected_files_ok=protected_ok, elapsed_ms=elapsed)

    def audit(self) -> dict[str, Any]:
        scan_result  = self.scan()
        recent_log   = self.logger.recent(50)
        plugin_issues = self._audit_plugins()
        agent_issues  = self._audit_agents()
        all_issues    = scan_result.issues + plugin_issues + agent_issues
        self.logger.log(SecurityLogEntry.now(
            event=SecurityEvent.AUDIT_COMPLETED,
            risk_level=RiskLevel.HIGH if all_issues else RiskLevel.LOW,
            detail=f"Audit: {len(all_issues)} total issues", blocked=False,
        ))
        return {"scan": scan_result.to_dict(), "plugin_issues": plugin_issues,
                "agent_issues": agent_issues, "recent_events": recent_log,
                "total_issues": len(all_issues), "risk_level": _compute_risk(all_issues, [])}

    def _audit_plugins(self) -> list[str]:
        issues: list[str] = []
        plugins_dir = self.clockwork_dir / "plugins"
        if not plugins_dir.exists(): return issues
        from .models import Permission
        for plugin_dir in plugins_dir.iterdir():
            if not plugin_dir.is_dir(): continue
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                issues.append(f"Plugin '{plugin_dir.name}' missing plugin.yaml manifest")
                continue
            try:
                import yaml
                data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            except Exception:
                issues.append(f"Plugin '{plugin_dir.name}' has invalid manifest")
                continue
            perms = data.get("permissions", [])
            dangerous = [p for p in perms if p in (Permission.SYSTEM_COMMAND, Permission.NETWORK_ACCESS)]
            if dangerous:
                issues.append(f"Plugin '{plugin_dir.name}' requests dangerous permissions: {', '.join(dangerous)}")
        return issues

    def _audit_agents(self) -> list[str]:
        issues: list[str] = []
        agents_path = self.clockwork_dir / "agents.json"
        if not agents_path.exists(): return issues
        try:
            data   = json.loads(agents_path.read_text(encoding="utf-8"))
            agents = data.get("agents", []) if isinstance(data, dict) else data
        except Exception:
            return issues
        for agent in agents:
            name = agent.get("name", "unknown")
            if "system_command" in agent.get("capabilities", []):
                issues.append(f"Agent '{name}' declares 'system_command' capability")
        return issues

    def _check_protected_files(self, issues, warnings) -> bool:
        ok = True
        for pf in PROTECTED_CLOCKWORK_FILES:
            full = self.repo_root / pf
            if not full.exists():
                warnings.append(f"Protected file missing: {pf}")
                ok = False
            else:
                try: full.read_text(encoding="utf-8")
                except Exception:
                    issues.append(f"Protected file unreadable: {pf}")
                    ok = False
        return ok

```

### File: `clockwork/security/security_engine.py`

```python
﻿"""
clockwork/security/security_engine.py
---------------------------------------
Main entry point for the Security and Sandboxing subsystem (spec §13).

Provides:
  - FileGuard   — path + sensitive file + command validation
  - SecurityScanner — repo scan + audit
  - SecurityLogger  — event logging to security_log.json
  - PluginVerifier  — checksum + manifest validation (spec §12)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from .file_guard import FileGuard, SecurityViolation
from .logger import SecurityLogger
from .models import Permission, PluginManifest, RiskLevel, SecurityScanResult
from .scanner import SecurityScanner


class PluginVerifier:
    """
    Verifies a plugin before installation (spec §12).

    Checks:
      - manifest exists and is valid
      - checksum matches declared value
      - permissions are within acceptable bounds
      - dangerous permissions flagged for confirmation
    """

    DANGEROUS_PERMISSIONS = {Permission.SYSTEM_COMMAND, Permission.NETWORK_ACCESS}
    MAX_ALLOWED_PERMISSIONS = {
        Permission.FILESYSTEM_READ,
        Permission.REPOSITORY_WRITE,
    }

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir
        self.logger        = SecurityLogger(clockwork_dir)

    def verify(self, plugin_dir: Path) -> tuple[bool, list[str]]:
        """
        Verify a plugin directory before installation.

        Returns (ok, [issues]).
        """
        issues: list[str] = []

        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            issues.append("plugin.yaml manifest not found")
            return False, issues

        try:
            import yaml  # type: ignore
            data     = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            manifest = PluginManifest.from_dict(data)
        except Exception as exc:
            issues.append(f"Invalid manifest: {exc}")
            return False, issues

        # name and version required
        if not manifest.name:
            issues.append("Plugin manifest missing 'name'")
        if not manifest.version:
            issues.append("Plugin manifest missing 'version'")

        # permission check
        for perm in manifest.permissions:
            if perm in self.DANGEROUS_PERMISSIONS:
                issues.append(
                    f"Plugin requests dangerous permission: '{perm}' — manual review required"
                )

        # checksum verification if provided
        if manifest.checksum:
            computed = self._checksum_dir(plugin_dir)
            if computed != manifest.checksum:
                issues.append(
                    f"Checksum mismatch — expected {manifest.checksum[:12]}..., "
                    f"got {computed[:12]}..."
                )

        return len(issues) == 0, issues

    def _checksum_dir(self, plugin_dir: Path) -> str:
        """Compute a deterministic SHA-256 over all plugin files."""
        h = hashlib.sha256()
        for fp in sorted(plugin_dir.rglob("*")):
            if fp.is_file() and fp.name != "plugin.yaml":
                try:
                    h.update(fp.read_bytes())
                except OSError:
                    pass
        return h.hexdigest()


class SecurityEngine:
    """
    Top-level facade for the Security subsystem.

    Usage::

        sec = SecurityEngine(repo_root=Path("."))

        # validate a path before accessing it
        sec.guard.check_path("/etc/passwd")   # raises SecurityViolation

        # scan the repo for issues
        result = sec.scan()

        # full audit
        report = sec.audit()

        # verify a plugin
        ok, issues = sec.verify_plugin(Path(".clockwork/plugins/my_plugin"))
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.logger        = SecurityLogger(self.clockwork_dir)
        self.guard         = FileGuard(
            self.repo_root, self.clockwork_dir, self.logger
        )
        self.scanner       = SecurityScanner(self.repo_root)
        self.verifier      = PluginVerifier(self.clockwork_dir)

    def scan(self) -> SecurityScanResult:
        """Run a security scan of the repository."""
        return self.scanner.scan()

    def audit(self) -> dict[str, Any]:
        """Produce a full security audit report."""
        return self.scanner.audit()

    def verify_plugin(self, plugin_dir: Path) -> tuple[bool, list[str]]:
        """Verify a plugin before installation."""
        return self.verifier.verify(plugin_dir)

    def check_proposed_changes(
        self,
        proposed_changes: list[str],
        agent: str = "",
    ) -> tuple[bool, list[str]]:
        """
        Security-filter a list of proposed changes (spec §7, §10).

        Returns (safe, [violations]).
        """
        guard    = FileGuard(self.repo_root, self.clockwork_dir, self.logger, agent)
        safe     = True
        violations: list[str] = []

        for change in proposed_changes:
            # extract file path: strip the first verb token only
            _parts = change.strip().split(" ", 1)
            fp = _parts[1].strip() if len(_parts) == 2 else change.strip()

            try:
                guard.check_sensitive(fp)
            except SecurityViolation as e:
                violations.append(str(e))
                safe = False
                continue

            try:
                guard.check_protected(fp)
            except SecurityViolation as e:
                violations.append(str(e))
                safe = False

        return safe, violations

    def alert(self, message: str) -> str:
        """
        Format a security alert string for CLI display (spec §15).

        Example output:
            WARNING: Attempt to modify protected file .clockwork/context.yaml
        """
        return f"WARNING: {message}"


```


