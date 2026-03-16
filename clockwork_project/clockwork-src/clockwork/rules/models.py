from __future__ import annotations
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
