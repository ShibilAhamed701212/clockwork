"""
clockwork/state/history.py
--------------------------
Unified activity history writer for agent and automation events.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def append_activity(
    clockwork_dir: Path,
    *,
    actor: str,
    action: str,
    status: str,
    details: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Append one event to .clockwork/logs/activity_history.jsonl.

    A compact compatibility entry is also mirrored to agent_history.json
    to preserve existing tooling expectations.
    """
    logs_dir = clockwork_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "action": action,
        "status": status,
        "details": details or {},
    }

    history_jsonl = logs_dir / "activity_history.jsonl"
    with history_jsonl.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=True) + "\n")

    _append_compat_agent_history(clockwork_dir, event)
    return event


def _append_compat_agent_history(clockwork_dir: Path, event: dict[str, Any]) -> None:
    """Keep legacy .clockwork/agent_history.json populated for compatibility."""
    history_path = clockwork_dir / "agent_history.json"
    try:
        history: list[Any] = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(history, list):
            history = []
    except (OSError, json.JSONDecodeError):
        history = []

    history.append(
        {
            "timestamp": event.get("timestamp", ""),
            "agent": event.get("actor", "unknown"),
            "action": event.get("action", ""),
            "result": event.get("status", ""),
            "details": event.get("details", {}),
        }
    )

    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")

