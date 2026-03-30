from __future__ import annotations

import json
import time
from pathlib import Path

FAILURE_LOG = Path(".clockwork/recovery_failure_log.json")


class SelfHealing:
    def __init__(
        self,
        context: object | None = None,
        state: object | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.context = context
        self.state = state
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.failure_log = self.repo_root / FAILURE_LOG
        self.failure_log.parent.mkdir(parents=True, exist_ok=True)
        if not self.failure_log.exists():
            self.failure_log.write_text("[]", encoding="utf-8")

    def heal(self, failure: dict) -> bool:
        failure_type = str(failure.get("type", ""))
        self._log_failure(failure)

        healers = {
            "missing_file": self._heal_missing_file,
            "invalid_context": self._heal_invalid_context,
            "graph_corruption": self._heal_graph,
            "index_corruption": self._heal_index,
            "state_inconsistency": self._heal_state,
        }
        healer = healers.get(failure_type, self._heal_generic)
        try:
            return bool(healer(failure))
        except Exception:
            return False

    def _heal_missing_file(self, failure: dict) -> bool:
        path = str(failure.get("path", ""))
        if not path:
            return False
        target = Path(path)
        if not target.is_absolute():
            target = self.repo_root / target
        target.parent.mkdir(parents=True, exist_ok=True)
        defaults = {".json": "{}", ".yaml": "", ".txt": "", ".py": "", ".md": ""}
        target.write_text(defaults.get(target.suffix, ""), encoding="utf-8")
        return True

    def _heal_invalid_context(self, failure: dict) -> bool:
        context_path = self.clockwork_dir / "context.yaml"
        if not context_path.exists():
            context_path.write_text("", encoding="utf-8")
        return True

    def _heal_graph(self, failure: dict) -> bool:
        graph_db = self.clockwork_dir / "knowledge_graph.db"
        if graph_db.exists():
            graph_db.unlink()
        return True

    def _heal_index(self, failure: dict) -> bool:
        index_db = self.clockwork_dir / "index.db"
        if index_db.exists():
            index_db.unlink()
        return True

    def _heal_state(self, failure: dict) -> bool:
        if self.state and hasattr(self.state, "reset"):
            self.state.reset()
        return True

    def _heal_generic(self, failure: dict) -> bool:
        return False

    def _log_failure(self, failure: dict) -> None:
        entry = {**failure, "timestamp": time.time(), "healed": False}
        log = json.loads(self.failure_log.read_text(encoding="utf-8"))
        log.append(entry)
        self.failure_log.write_text(json.dumps(log[-200:], indent=2), encoding="utf-8")

    def get_failure_log(self) -> list[dict]:
        return json.loads(self.failure_log.read_text(encoding="utf-8"))

    def failure_rate(self) -> float:
        log = self.get_failure_log()
        if not log:
            return 0.0
        recent = [item for item in log if time.time() - item.get("timestamp", 0) < 3600]
        return round(len(recent) / max(1, len(log)), 3)

