import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

PLUGIN_DIR          = Path(".clockwork/plugins")
MAX_PLUGIN_SIZE_KB  = 100
REQUIRED_FIELDS     = ["name","version","description","rules"]
TRUSTED_SOURCES     = ["clockwork-official","local"]

class PluginSecurity:
    def __init__(self):
        PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    def validate(self, plugin_path: str) -> Tuple[bool, List[str]]:
        p      = Path(plugin_path)
        errors = []
        if not p.exists():
            return False, ["Not found: " + plugin_path]
        size_kb = p.stat().st_size / 1024
        if size_kb > MAX_PLUGIN_SIZE_KB:
            errors.append("Too large: " + str(round(size_kb,1)) + "KB")
        if p.suffix != ".json":
            errors.append("Only .json plugins supported")
            return False, errors
        try:
            data = json.loads(p.read_text())
            for field in REQUIRED_FIELDS:
                if field not in data:
                    errors.append("Missing field: " + field)
            source = data.get("source","local")
            if source not in TRUSTED_SOURCES:
                errors.append("Untrusted source: " + source)
            rules = data.get("rules",{})
            if not isinstance(rules, dict):
                errors.append("'rules' must be a dict")
        except Exception as e:
            errors.append("Parse error: " + str(e))
        return len(errors) == 0, errors

    def checksum(self, plugin_path: str) -> str:
        p = Path(plugin_path)
        return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""

    def load_safe(self, plugin_path: str) -> Tuple[bool, Dict]:
        ok, errors = self.validate(plugin_path)
        if not ok:
            return False, {"errors": errors}
        try:
            data = json.loads(Path(plugin_path).read_text())
            return True, data
        except Exception as e:
            return False, {"error": str(e)}

    def list_plugins(self) -> List[Dict]:
        plugins = []
        for p in PLUGIN_DIR.glob("*.json"):
            try:
                data = json.loads(p.read_text())
                ok, errs = self.validate(str(p))
                plugins.append({
                    "name":     data.get("name", p.stem),
                    "version":  data.get("version","?"),
                    "path":     str(p),
                    "valid":    ok,
                    "checksum": self.checksum(str(p)),
                })
            except Exception:
                pass
        return plugins

    def install(self, plugin_data: Dict, name: str) -> Tuple[bool, str]:
        target = PLUGIN_DIR / (name + ".json")
        ok, errors = self._validate_data(plugin_data)
        if not ok:
            return False, " | ".join(errors)
        with open(target,"w") as f:
            json.dump(plugin_data, f, indent=2)
        print("[PluginSecurity] Installed: " + name)
        return True, str(target)

    def _validate_data(self, data: Dict) -> Tuple[bool, List[str]]:
        errors = []
        for field in REQUIRED_FIELDS:
            if field not in data:
                errors.append("Missing: " + field)
        return len(errors) == 0, errors