"""Repository Scanner."""
import json, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

IGNORED_DIRS = {".git",".clockwork","__pycache__","node_modules",".venv","venv"}
IGNORED_FILES = {".env","credentials.json","secrets.json"}
LANGUAGE_MAP: dict[str,str] = {".py":"Python",".js":"JavaScript",".ts":"TypeScript",".java":"Java",".go":"Go",".rs":"Rust",".cs":"C#",".cpp":"C++",".c":"C",".rb":"Ruby",".php":"PHP",".html":"HTML",".css":"CSS",".json":"JSON",".yaml":"YAML",".yml":"YAML",".md":"Markdown",".sh":"Shell",".ps1":"PowerShell",".sql":"SQL"}

class RepositoryScanner:
    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.clockwork_dir = repo_path / ".clockwork"

    def scan(self) -> dict[str, Any]:
        files: list[dict[str,Any]] = []
        lang_counts: dict[str,int] = {}
        for root, dirs, filenames in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for fn in filenames:
                if fn in IGNORED_FILES: continue
                fp = Path(root) / fn
                rel = fp.relative_to(self.repo_path)
                lang = LANGUAGE_MAP.get(fp.suffix.lower(), "Unknown")
                try:
                    import hashlib as _hl
                    _fhash = _hl.sha256(fp.read_bytes()).hexdigest()
                    _fsize = fp.stat().st_size
                except OSError:
                    _fhash = ""
                    _fsize = 0
                files.append({"path": str(rel), "language": lang, "size_bytes": _fsize, "file_hash": _fhash})
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        languages: dict[str, int] = {l: c for l, c in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True) if l != "Unknown"}
        result: dict[str,Any] = {"generated_at": datetime.now(timezone.utc).isoformat(), "total_files": len(files), "languages": languages, "files": files}
        (self.clockwork_dir / "repo_map.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
