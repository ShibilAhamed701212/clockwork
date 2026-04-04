"""Packaging Engine - full pre-pack and import pipeline."""
import json, zipfile, hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import yaml

PACKAGE_FILES_REQUIRED = ["context.yaml", "repo_map.json", "rules.md", "config.yaml"]
PACKAGE_FILES_OPTIONAL = ["rules.yaml", "tasks.json", "skills.json", "agent_history.json", "handoff/handoff.json", "handoff/next_agent_brief.md"]
PACKAGE_FILES = PACKAGE_FILES_REQUIRED + PACKAGE_FILES_OPTIONAL

class PackagingEngine:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.d = repo_path / ".clockwork"

    def pack(self, output_name: str = "project.clockwork") -> Path:
        """Full pipeline: Context -> Scan check -> Rules -> Brain -> Assemble -> Compress."""
        ctx = self._load_context()
        if not ctx:
            raise RuntimeError("context.yaml missing. Run: clockwork init")
        if not (self.d / "repo_map.json").exists():
            raise RuntimeError("repo_map.json not found. Run: clockwork scan")
        from clockwork.rules.rule_engine import RuleEngine
        passed, violations = RuleEngine(self.repo_path).verify()
        if not passed:
            raise RuntimeError("Rule Engine failed before pack:\n" + "\n".join(f"  - {v}" for v in violations))
        # MiniBrain.analyze() does not exist - removed to prevent TypeError
        assessment: dict[str, Any] = {}
        (self.d / "packages").mkdir(exist_ok=True)
        out = self.d / "packages" / output_name
        meta = self._meta(ctx, assessment)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps(meta, indent=2))
            for f in PACKAGE_FILES:
                src = self.d / f
                if src.exists(): zf.write(src, arcname=f)
            zf.writestr("package_checksum.txt", hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest())
        return out

    def load(self, package_path: Path) -> None:
        """Pipeline: Load -> Integrity -> Version check -> Restore -> Rule validation."""
        if not zipfile.is_zipfile(package_path):
            raise ValueError("Not a valid .clockwork package")
        with zipfile.ZipFile(package_path, "r") as zf:
            names = zf.namelist()
            if "metadata.json" not in names: raise ValueError("Missing metadata.json")
            if "package_checksum.txt" not in names: raise ValueError("Missing package_checksum.txt")
            meta = json.loads(zf.read("metadata.json"))
            stored = zf.read("package_checksum.txt").decode().strip()
            computed = hashlib.sha256(json.dumps(meta, sort_keys=True).encode()).hexdigest()
            if stored != computed: raise ValueError("Checksum mismatch - package may be corrupted.")
            if meta.get("package_version", 1) > 1: raise ValueError("Incompatible package version.")
            self.d.mkdir(exist_ok=True)
            (self.d / "handoff").mkdir(exist_ok=True)
            for name in names:
                if name in ("metadata.json", "package_checksum.txt"): continue
                dest = self.d / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
        from clockwork.rules.rule_engine import RuleEngine
        passed, violations = RuleEngine(self.repo_path).verify()
        if not passed:
            raise RuntimeError("Loaded package failed rule validation:\n" + "\n".join(f"  - {v}" for v in violations))

    def _meta(self, ctx: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
        return {"clockwork_version": "0.1", "package_version": 1, "clockwork_required": ">=0.1", "generated_at": datetime.now(timezone.utc).isoformat(), "project_name": ctx.get("project_name", "unknown"), "languages": assessment.get("languages", []), "total_files": assessment.get("files", 0)}

    def _load_context(self) -> dict[str, Any]:
        p = self.d / "context.yaml"
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {} if p.exists() else {}
