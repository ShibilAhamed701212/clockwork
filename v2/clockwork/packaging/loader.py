import json
import zipfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from packaging.serializer import Serializer

RESTORE_TARGETS = {
    "context.yaml":    Path(".clockwork/context.yaml"),
    "repo_map.json":   Path(".clockwork/repo_map.json"),
    "rules.md":        Path("rules/rules.md"),
    "tasks.json":      Path(".clockwork/tasks.json"),
    "agents.json":     Path(".clockwork/agents.json"),
}

MIN_CLOCKWORK_VERSION = (2, 0)

class Loader:
    def __init__(self):
        self.serializer = Serializer()

    def load(self, package_path: str, merge: bool = False) -> Dict:
        p = Path(package_path)
        if not p.exists():
            raise FileNotFoundError("Package not found: " + package_path)

        print("[Loader] Loading package: " + p.name)
        contents = self._extract(p)

        ok, errors = self._validate(contents)
        if not ok:
            raise ValueError("Package validation failed: " + " | ".join(errors))

        metadata = json.loads(contents.get("metadata.json", "{}"))
        self._check_compatibility(metadata)

        print("[Loader] Restoring system state...")
        restored = self._restore(contents, merge=merge)

        print("[Loader] Package loaded successfully.")
        print("[Loader] Project: " + metadata.get("project_name", "unknown"))
        print("[Loader] Generated: " + str(round(metadata.get("generated_at", 0))))
        return {
            "metadata":  metadata,
            "restored":  restored,
            "timestamp": time.time(),
        }

    def _extract(self, path: Path) -> Dict[str, str]:
        contents = {}
        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                key = name.replace("clockwork/", "")
                contents[key] = zf.read(name).decode("utf-8", errors="ignore")
        return contents

    def _validate(self, contents: Dict[str, str]) -> Tuple[bool, list]:
        errors = []
        required = ["metadata.json", "checksums.json"]
        for r in required:
            if r not in contents:
                errors.append("Missing required file: " + r)

        if "checksums.json" in contents and errors == []:
            try:
                checksums = json.loads(contents["checksums.json"])
                for fname, expected in checksums.items():
                    if fname in contents:
                        actual = self.serializer.checksum(contents[fname])
                        if actual != expected:
                            errors.append("Checksum mismatch: " + fname)
            except Exception as e:
                errors.append("Checksum parse error: " + str(e))

        if "metadata.json" in contents:
            try:
                meta = json.loads(contents["metadata.json"])
                if "clockwork_version" not in meta:
                    errors.append("Missing clockwork_version in metadata")
            except Exception:
                errors.append("Invalid metadata.json")

        return len(errors) == 0, errors

    def _check_compatibility(self, metadata: Dict):
        req = metadata.get("clockwork_required", ">=2.0")
        current = (2, 0)
        try:
            ver_str = req.replace(">=", "").strip()
            parts   = tuple(int(x) for x in ver_str.split("."))
            if parts > current:
                raise RuntimeError(
                    "Package requires Clockwork " + req +
                    " but current is " + ".".join(str(x) for x in current)
                )
        except ValueError:
            pass
        print("[Loader] Compatibility check passed.")

    def _restore(self, contents: Dict[str, str], merge: bool) -> Dict:
        restored = {}
        for fname, target_path in RESTORE_TARGETS.items():
            if fname not in contents:
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if merge and target_path.exists():
                restored[fname] = self._merge_file(fname, target_path, contents[fname])
            else:
                target_path.write_text(contents[fname], encoding="utf-8")
                restored[fname] = "restored"
                print("[Loader] Restored: " + str(target_path))
        return restored

    def _merge_file(self, fname: str, target: Path, new_content: str) -> str:
        if fname.endswith(".json"):
            try:
                existing = json.loads(target.read_text())
                incoming = json.loads(new_content)
                if isinstance(existing, dict) and isinstance(incoming, dict):
                    merged = {**existing, **incoming}
                    target.write_text(json.dumps(merged, indent=2), encoding="utf-8")
                    return "merged"
            except Exception:
                pass
        target.write_text(new_content, encoding="utf-8")
        return "overwritten"

    def inspect(self, package_path: str) -> Dict:
        p = Path(package_path)
        if not p.exists():
            return {"error": "Package not found"}
        contents = self._extract(p)
        meta     = json.loads(contents.get("metadata.json", "{}"))
        ok, errs = self._validate(contents)
        return {
            "name":    p.name,
            "valid":   ok,
            "errors":  errs,
            "files":   list(contents.keys()),
            "metadata": meta,
            "size_kb": round(p.stat().st_size / 1024, 1),
        }