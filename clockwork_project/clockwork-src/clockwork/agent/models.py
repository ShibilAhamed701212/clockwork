"""
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

