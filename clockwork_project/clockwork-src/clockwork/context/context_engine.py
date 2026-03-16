"""
Clockwork Context Engine
"""
from __future__ import annotations
import json, logging, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import yaml
from .schema import CONTEXT_SCHEMA, validate_context_schema

logger = logging.getLogger(__name__)

CLOCKWORK_DIR = ".clockwork"
CONTEXT_FILE = "context.yaml"
LOCK_FILE = "context.lock"
HISTORY_FILE = "context_history.json"
REQUIRED_TOP_LEVEL_KEYS = {"project", "repository", "current_state"}

class ContextError(Exception): pass
class ContextValidationError(ContextError): pass
class ContextLockError(ContextError): pass
class ContextCorruptionError(ContextError): pass

class ContextEngine:
    def __init__(self, repo_root="."):
        self.repo_root = Path(repo_root).resolve()
        self.clockwork_dir = self.repo_root / CLOCKWORK_DIR
        self.context_path = self.clockwork_dir / CONTEXT_FILE
        self.lock_path = self.clockwork_dir / LOCK_FILE
        self.history_path = self.clockwork_dir / HISTORY_FILE
        self._context: dict[str, Any] = {}

    def load(self):
        if not self.context_path.exists():
            from .initializer import ContextInitializer
            self._context = ContextInitializer(self.repo_root).initialize()
        else:
            raw = self._read_yaml(self.context_path)
            self._validate(raw)
            self._context = raw
        return self._context

    def update(self, scanner_results=None, agent_name="clockwork", change_summary=""):
        self._acquire_lock()
        try:
            existing = self.load()
            merged = self._merge(existing, scanner_results or {})
            self._validate(merged)
            self._write_yaml(self.context_path, merged)
            self._context = merged
            self._record_history(change_summary or "Context updated", agent_name)
            return merged
        finally:
            self._release_lock()

    def get(self, *key_path, default=None):
        node = self._context
        for key in key_path:
            if not isinstance(node, dict): return default
            node = node.get(key, default)
        return node

    def set(self, value, *key_path, agent_name="clockwork"):
        if not key_path: raise ContextError("key_path must have at least one element.")
        self._acquire_lock()
        try:
            node = self._context
            for key in key_path[:-1]:
                node = node.setdefault(key, {})
            node[key_path[-1]] = value
            self._validate(self._context)
            self._write_yaml(self.context_path, self._context)
            self._record_history(f"Field '{'.'.join(key_path)}' updated", agent_name)
        finally:
            self._release_lock()

    def validate(self):
        self._validate(self._context)
        return True

    def integrity_check(self):
        warnings = []
        dep_text = self._collect_dependency_files().lower()
        for fw in (self.get("frameworks") or []):
            if fw.lower() not in dep_text:
                warnings.append(f"Framework '{fw}' listed in context but not found in dependency files.")
        detected_exts = self._detect_language_extensions()
        for lang in (self.get("repository", "languages") or {}):
            if lang.lower() not in detected_exts:
                warnings.append(f"Language '{lang}' claimed in context but no matching files found.")
        if warnings: logger.warning("Context integrity warnings: %s", warnings)
        return warnings

    def history(self):
        if not self.history_path.exists(): return []
        with self.history_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    @property
    def context(self): return dict(self._context)

    def _validate(self, data):
        if not isinstance(data, dict):
            raise ContextValidationError("Context must be a YAML mapping.")
        missing = REQUIRED_TOP_LEVEL_KEYS - data.keys()
        if missing:
            raise ContextValidationError(f"Context is missing required top-level keys: {missing}")
        errors = validate_context_schema(data, CONTEXT_SCHEMA)
        if errors:
            raise ContextValidationError("Context schema validation failed:\n" + "\n".join(errors))

    def _merge(self, base, updates):
        result = dict(base)
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge(result[key], value)
            else:
                result[key] = value
        return result

    def _acquire_lock(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        while self.lock_path.exists():
            if time.monotonic() > deadline:
                raise ContextLockError(f"Could not acquire context lock within {timeout}s.")
            time.sleep(0.05)
        self.lock_path.touch()

    def _release_lock(self):
        try: self.lock_path.unlink(missing_ok=True)
        except OSError as exc: logger.warning("Failed to release context lock: %s", exc)

    def _record_history(self, change, agent):
        entries = self.history()
        entries.append({"timestamp": datetime.now(timezone.utc).isoformat(), "change": change, "agent": agent})
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("w", encoding="utf-8") as fh:
            json.dump(entries, fh, indent=2)

    def _collect_dependency_files(self):
        parts = []
        for name in ["requirements.txt", "pyproject.toml", "package.json", "Pipfile"]:
            path = self.repo_root / name
            if path.exists():
                try: parts.append(path.read_text(encoding="utf-8"))
                except OSError: pass
        return "\n".join(parts)

    def _detect_language_extensions(self):
        ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rb": "ruby"}
        found = set()
        try:
            for path in self.repo_root.rglob("*"):
                if path.suffix in ext_map: found.add(ext_map[path.suffix])
        except OSError: pass
        return found

    @staticmethod
    def _read_yaml(path):
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as exc:
            raise ContextValidationError(f"YAML parse error in {path}: {exc}") from exc

    @staticmethod
    def _write_yaml(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".yaml.tmp")
        try:
            with tmp.open("w", encoding="utf-8") as fh:
                yaml.dump(data, fh, default_flow_style=False, allow_unicode=True)
            tmp.replace(path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise ContextError(f"Cannot write {path}: {exc}") from exc
