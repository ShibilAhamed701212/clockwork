import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from context.context_store import ContextStore
from context.context_validator import ContextValidator

class ContextEngine:
    def __init__(self, state=None):
        self.state = state
        self.store = ContextStore()
        self._context = self.store.load()
        self.validator = ContextValidator()

    # ── Lifecycle ────────────────────────────────────────────────
    def load(self) -> Dict:
        self._context = self.store.load()
        return self._context

    def validate(self, repo_map: Dict = {}) -> bool:
        self.validator = ContextValidator(repo_map)
        ok, errors = self.validator.validate(self._context)
        if not ok:
            for e in errors:
                print("[ContextEngine] Validation error: " + e)
        return ok

    def persist(self):
        self.store.persist(self._context)
        if self.state:
            self.state.emit_event("context_persisted", {})

    # ── Read ─────────────────────────────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        return self._context.get(key, default)

    def query(self, path: str, default: Any = None) -> Any:
        parts = path.split(".")
        node = self._context
        for p in parts:
            if not isinstance(node, dict):
                return default
            node = node.get(p, default)
        return node

    def snapshot(self) -> Dict:
        return dict(self._context)

    # ── Write ────────────────────────────────────────────────────
    def set(self, key: str, value: Any):
        self._context[key] = value
        self._context.setdefault("meta", {})["last_updated"] = time.time()
        self.store.record_change("set:" + key)
        self.persist()
        if self.state:
            self.state.emit_event("context_updated", {"key": key})

    def merge(self, data: Dict):
        for k, v in data.items():
            if isinstance(v, dict) and isinstance(self._context.get(k), dict):
                self._context[k].update(v)
            else:
                self._context[k] = v
        self.store.record_change("merge:" + str(list(data.keys())))
        self.persist()

    def clear(self):
        self._context = {}
        self.persist()

    # ── Memory operations ────────────────────────────────────────
    def record_action(self, action: str, agent: str = "system"):
        mem = self._context.setdefault("memory", {})
        mem.setdefault("past_actions", []).append({
            "action": action, "agent": agent, "timestamp": time.time()
        })
        self.store.record_change("action:" + action, agent)
        self.persist()

    def record_decision(self, decision: str, reason: str = ""):
        mem = self._context.setdefault("memory", {})
        mem.setdefault("decisions", []).append({
            "decision": decision, "reason": reason, "timestamp": time.time()
        })
        self.persist()

    def record_failure(self, failure: str, context_info: str = ""):
        mem = self._context.setdefault("memory", {})
        mem.setdefault("failures", []).append({
            "failure": failure, "context": context_info, "timestamp": time.time()
        })
        self.persist()

    def record_event(self, event_type: str, payload: Dict = {}):
        self._context.setdefault("events", []).append({
            "type": event_type, "timestamp": time.time(), "payload": payload
        })
        self.persist()

    # ── Scanner sync ─────────────────────────────────────────────
    def sync_from_scanner(self, repo_map: Dict):
        print("[ContextEngine] Syncing from scanner output...")
        repo_section = {
            "architecture": repo_map.get("architecture", {}).get("type", ""),
            "languages": repo_map.get("languages", {}).get("languages", {}),
            "frameworks": list(repo_map.get("frameworks", {}).keys()),
            "dependencies": repo_map.get("dependencies", {}).get("dependencies", []),
            "components": repo_map.get("components", {}),
        }
        self._context["repository"] = repo_section
        self._context.setdefault("skills", {})["required"] = repo_map.get("skills", [])
        if not self._context.get("context_state", {}).get("summary"):
            self._context.setdefault("context_state", {})["summary"] = "Initial scan complete"
            self._context["context_state"]["next_tasks"] = ["Define first task"]
        self.store.record_change("sync_from_scanner")
        self.persist()

        drift = self.validator.detect_drift(self._context, repo_map)
        if drift:
            print("[ContextEngine] DRIFT DETECTED:")
            for d in drift:
                print("  - " + d)
            if self.state:
                self.state.mark_unhealthy("Context drift: " + str(drift))
        else:
            print("[ContextEngine] No drift detected.")

    # ── Snapshot ─────────────────────────────────────────────────
    def take_snapshot(self, label: str = "") -> str:
        return self.store.snapshot(label)

    def restore_snapshot(self, path: str) -> Dict:
        self._context = self.store.restore_snapshot(path)
        return self._context

    def list_snapshots(self) -> List[str]:
        return self.store.list_snapshots()

    # ── Feedback loop ────────────────────────────────────────────
    def integrate_feedback(self, outcome: str, success: bool, agent: str = "system"):
        mem = self._context.setdefault("memory", {})
        if success:
            mem.setdefault("patterns", []).append({
                "type": "success", "outcome": outcome,
                "agent": agent, "timestamp": time.time()
            })
        else:
            mem.setdefault("failures", []).append({
                "failure": outcome, "context": "feedback",
                "timestamp": time.time()
            })
        self.store.record_change("feedback:" + outcome, agent)
        self.persist()

    # ── Retrieval helpers ─────────────────────────────────────────
    def get_current_task(self) -> str:
        return self.query("context_state.current_task", "")

    def get_next_tasks(self) -> List[str]:
        return self.query("context_state.next_tasks", [])

    def get_architecture(self) -> str:
        return self.query("repository.architecture", "unknown")

    def get_skills(self) -> List[str]:
        return self.query("skills.required", [])

    def get_history(self) -> List[Dict]:
        return self.store.get_history()

    def initialize(self, project_name: str = "", project_type: str = ""):
        self._context.setdefault("project", {}).update({
            "name": project_name, "type": project_type, "version": "1.0"
        })
        self._context.setdefault("meta", {})["initialized"] = True
        self.store.record_change("initialized")
        self.persist()
        print("[ContextEngine] Initialized for project: " + (project_name or "unknown"))