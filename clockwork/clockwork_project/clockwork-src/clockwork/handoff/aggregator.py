"""
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