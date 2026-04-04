"""
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