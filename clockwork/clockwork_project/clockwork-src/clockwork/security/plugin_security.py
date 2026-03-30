from __future__ import annotations

import hashlib
import json
from pathlib import Path

PLUGIN_DIR = Path(".clockwork/plugins")
MAX_PLUGIN_SIZE_KB = 100
REQUIRED_FIELDS = ["name", "version", "description", "rules"]
TRUSTED_SOURCES = ["clockwork-official", "local"]


class PluginSecurity:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.plugin_dir = self.repo_root / PLUGIN_DIR
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

    def validate(self, plugin_path: str) -> tuple[bool, list[str]]:
        path = Path(plugin_path)
        errors: list[str] = []
        if not path.exists():
            return False, ["Not found: " + plugin_path]
        size_kb = path.stat().st_size / 1024
        if size_kb > MAX_PLUGIN_SIZE_KB:
            errors.append("Too large: " + str(round(size_kb, 1)) + "KB")
        if path.suffix != ".json":
            errors.append("Only .json plugins supported")
            return False, errors
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for field in REQUIRED_FIELDS:
                if field not in data:
                    errors.append("Missing field: " + field)
            source = data.get("source", "local")
            if source not in TRUSTED_SOURCES:
                errors.append("Untrusted source: " + source)
            if not isinstance(data.get("rules", {}), dict):
                errors.append("'rules' must be a dict")
        except Exception as exc:
            errors.append("Parse error: " + str(exc))
        return len(errors) == 0, errors

    def checksum(self, plugin_path: str) -> str:
        path = Path(plugin_path)
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""

    def load_safe(self, plugin_path: str) -> tuple[bool, dict]:
        ok, errors = self.validate(plugin_path)
        if not ok:
            return False, {"errors": errors}
        try:
            return True, json.loads(Path(plugin_path).read_text(encoding="utf-8"))
        except Exception as exc:
            return False, {"error": str(exc)}

    def list_plugins(self) -> list[dict]:
        plugins: list[dict] = []
        for path in self.plugin_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                valid, _ = self.validate(str(path))
                plugins.append(
                    {
                        "name": data.get("name", path.stem),
                        "version": data.get("version", "?"),
                        "path": str(path),
                        "valid": valid,
                        "checksum": self.checksum(str(path)),
                    }
                )
            except Exception:
                continue
        return plugins

    def install(self, plugin_data: dict, name: str) -> tuple[bool, str]:
        target = self.plugin_dir / (name + ".json")
        ok, errors = self._validate_data(plugin_data)
        if not ok:
            return False, " | ".join(errors)
        target.write_text(json.dumps(plugin_data, indent=2), encoding="utf-8")
        return True, str(target)

    def _validate_data(self, data: dict) -> tuple[bool, list[str]]:
        errors = ["Missing: " + field for field in REQUIRED_FIELDS if field not in data]
        return len(errors) == 0, errors

