from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from clockwork.context.engine import ContextEngine as CoreContextEngine


class ContextEngine:
    """v2-compatible facade over the core typed context engine."""

    def __init__(self, state: object | None = None, repo_root: Path | None = None) -> None:
        self.state = state
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self._core = CoreContextEngine(self.clockwork_dir)
        self._context = self._core.load_or_default(project_name=self.repo_root.name)

    def load(self) -> dict:
        self._context = self._core.load_or_default(project_name=self.repo_root.name)
        return self._context.to_dict()

    def persist(self) -> None:
        self._core.save(self._context)
        if self.state and hasattr(self.state, "emit_event"):
            self.state.emit_event("context_persisted", {})

    def validate(self, repo_map: dict | None = None) -> bool:
        return len(self._core.validate(self._context)) == 0

    def get(self, key: str, default: Any = None) -> Any:
        return self._context.to_dict().get(key, default)

    def query(self, path: str, default: Any = None) -> Any:
        node: Any = self._context.to_dict()
        for part in path.split("."):
            if not isinstance(node, dict):
                return default
            node = node.get(part, default)
        return node

    def snapshot(self) -> dict:
        return self._context.to_dict()

    def set(self, key: str, value: Any) -> None:
        data = self._context.to_dict()
        data[key] = value
        self._context = self._context.from_dict(data)
        self.persist()

    def merge(self, data: dict) -> None:
        merged = self._context.to_dict()
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key].update(value)
            else:
                merged[key] = value
        self._context = self._context.from_dict(merged)
        self.persist()

    def clear(self) -> None:
        self._context = self._context.from_dict({"project_name": self.repo_root.name})
        self.persist()

    def record_action(self, action: str, agent: str = "system") -> None:
        data = self._context.to_dict()
        data.setdefault("agent_notes", []).append(f"{agent}: {action}")
        self._context = self._context.from_dict(data)
        self.persist()

    def record_decision(self, decision: str, reason: str = "") -> None:
        data = self._context.to_dict()
        data.setdefault("architecture_overview", "")
        suffix = f"\n- decision: {decision} ({reason})"
        data["architecture_overview"] = str(data["architecture_overview"]) + suffix
        self._context = self._context.from_dict(data)
        self.persist()

    def record_failure(self, failure: str, context_info: str = "") -> None:
        self.record_action(f"failure={failure} context={context_info}", agent="system")

    def record_event(self, event_type: str, payload: dict | None = None) -> None:
        payload = payload or {}
        self.record_action(f"event={event_type} payload={payload}", agent="system")

    def sync_from_scanner(self, repo_map: dict) -> None:
        from clockwork.scanner.models import ScanResult

        scan_result = ScanResult.from_dict(repo_map)
        self._context = self._core.merge_scan(scan_result)

    def take_snapshot(self, label: str = "") -> str:
        snaps = self.clockwork_dir / "snapshots"
        snaps.mkdir(parents=True, exist_ok=True)
        name = ((label + "_") if label else "") + str(int(time.time())) + ".yaml"
        target = snaps / name
        target.write_text("# compatibility snapshot\n", encoding="utf-8")
        return str(target)

    def restore_snapshot(self, path: str) -> dict:
        # Snapshot restore is a no-op in this compatibility layer.
        return self.snapshot()

    def list_snapshots(self) -> list[str]:
        snaps = self.clockwork_dir / "snapshots"
        if not snaps.exists():
            return []
        return sorted(str(p) for p in snaps.glob("*.yaml"))

    def integrate_feedback(self, outcome: str, success: bool, agent: str = "system") -> None:
        self.record_action(f"feedback outcome={outcome} success={success}", agent=agent)

    def get_current_task(self) -> str:
        tasks = self._context.current_tasks
        return tasks[0].description if tasks else ""

    def get_next_tasks(self) -> list[str]:
        return [task.description for task in self._context.current_tasks if task.status != "done"]

    def get_architecture(self) -> str:
        return self._context.architecture_overview or "unknown"

    def get_skills(self) -> list[str]:
        return []

    def get_history(self) -> list[dict]:
        return []

    def initialize(self, project_name: str = "", project_type: str = "") -> None:
        data = self._context.to_dict()
        data["project_name"] = project_name or self.repo_root.name
        data["summary"] = project_type
        self._context = self._context.from_dict(data)
        self.persist()

