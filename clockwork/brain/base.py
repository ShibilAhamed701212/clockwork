"""
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
