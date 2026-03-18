"""
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