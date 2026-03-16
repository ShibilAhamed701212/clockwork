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
