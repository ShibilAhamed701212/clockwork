import json
import time
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Optional

from packaging.serializer import Serializer

PACKAGES_DIR = Path(".clockwork/packages")
PACKAGE_EXT  = ".clockwork"

SOURCE_FILES = {
    "context.yaml":       Path(".clockwork/context.yaml"),
    "repo_map.json":      Path(".clockwork/repo_map.json"),
    "rules.md":           Path("rules/rules.md"),
    "tasks.json":         Path(".clockwork/tasks.json"),
    "agents.json":        Path(".clockwork/agents.json"),
    "handoff.json":       Path(".clockwork/handoff/handoff.json"),
    "rule_log.json":      Path(".clockwork/rule_log.json"),
    "context_history.json": Path(".clockwork/context_history.json"),
}

class Packer:
    def __init__(self):
        self.serializer = Serializer()
        PACKAGES_DIR.mkdir(parents=True, exist_ok=True)

    def pack(self, project_name: str = "", label: str = "") -> Path:
        print("[Packer] Assembling package...")
        t0 = time.time()

        version   = self._next_version(project_name)
        slug      = (project_name or "project").replace(" ", "_").lower()
        lbl       = ("_" + label) if label else ""
        filename  = slug + "_v" + str(version) + lbl + PACKAGE_EXT
        out_path  = PACKAGES_DIR / filename

        metadata  = self.serializer.build_metadata(project_name, version)
        contents: Dict[str, str] = {}
        checksums: Dict[str, str] = {}

        for name, path in SOURCE_FILES.items():
            if path.exists():
                raw = path.read_text(encoding="utf-8", errors="ignore")
                if name.endswith(".json"):
                    try:
                        data    = json.loads(raw)
                        cleaned = self.serializer.filter_secrets(data)
                        raw     = self.serializer.to_json(cleaned)
                    except Exception:
                        pass
                elif name.endswith(".yaml"):
                    try:
                        data    = self.serializer.from_yaml(raw)
                        cleaned = self.serializer.filter_secrets(data)
                        raw     = self.serializer.to_yaml(cleaned)
                    except Exception:
                        pass
                contents[name]  = raw
                checksums[name] = self.serializer.checksum(raw)
            else:
                print("[Packer] Optional file missing: " + str(path))

        contents["metadata.json"]  = self.serializer.to_json(metadata)
        contents["checksums.json"] = self.serializer.to_json(checksums)

        self._write_zip(out_path, contents)
        elapsed = round(time.time() - t0, 3)
        size_kb = round(out_path.stat().st_size / 1024, 1)
        print("[Packer] Package created: " + filename)
        print("[Packer] Size: " + str(size_kb) + " KB | Time: " + str(elapsed) + "s")
        return out_path

    def _write_zip(self, out_path: Path, contents: Dict[str, str]):
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, text in contents.items():
                zf.writestr("clockwork/" + name, text)

    def _next_version(self, project_name: str) -> int:
        slug = (project_name or "project").replace(" ", "_").lower()
        existing = list(PACKAGES_DIR.glob(slug + "_v*.clockwork"))
        if not existing:
            return 1
        versions = []
        for p in existing:
            parts = p.stem.split("_v")
            if len(parts) >= 2:
                try:
                    versions.append(int(parts[-1].split("_")[0]))
                except ValueError:
                    pass
        return max(versions, default=0) + 1

    def list_packages(self):
        pkgs = sorted(PACKAGES_DIR.glob("*" + PACKAGE_EXT))
        return [
            {
                "name":    p.name,
                "path":    str(p),
                "size_kb": round(p.stat().st_size / 1024, 1),
                "modified": p.stat().st_mtime,
            }
            for p in pkgs
        ]

    def format_schema(self) -> Dict:
        return {
            "format":   "clockwork-package",
            "version":  "2.0",
            "contents": list(SOURCE_FILES.keys()) + ["metadata.json", "checksums.json"],
            "extension": PACKAGE_EXT,
        }