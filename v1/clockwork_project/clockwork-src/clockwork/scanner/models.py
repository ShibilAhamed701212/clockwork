"""
clockwork/scanner/models.py
-----------------------------
Data models for the Repository Scanner subsystem.

These models are the contract between the scanner and all downstream
subsystems (Context Engine, Rule Engine, Graph, Packaging).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── File-level model ───────────────────────────────────────────────────────

@dataclass
class SymbolInfo:
    """A named symbol (class, function, variable) found in a source file."""

    name: str
    kind: str           # "class" | "function" | "method" | "variable" | "import"
    line: int
    parent: Optional[str] = None   # enclosing class name, if any


@dataclass
class FileEntry:
    """
    Complete metadata for a single repository file.

    All fields except *path* are optional — a file may be unreadable
    or its language unsupported.
    """

    path: str                           # relative to repo root
    extension: str
    language: str
    size_bytes: int
    lines: int = 0
    is_entry_point: bool = False
    is_test: bool = False
    is_config: bool = False
    symbols: list[SymbolInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    last_modified: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ── Directory-level model ──────────────────────────────────────────────────

@dataclass
class DirectoryEntry:
    """Metadata for a directory node in the repository tree."""

    path: str           # relative to repo root  ("." = root)
    file_count: int = 0
    subdirectory_count: int = 0
    languages: list[str] = field(default_factory=list)
    has_init: bool = False          # Python package?
    has_tests: bool = False


# ── Language summary ───────────────────────────────────────────────────────

@dataclass
class LanguageSummary:
    """Aggregated statistics for a single detected language."""

    name: str
    file_count: int = 0
    total_lines: int = 0
    total_bytes: int = 0
    extensions: list[str] = field(default_factory=list)

    @property
    def average_file_size(self) -> float:
        if self.file_count == 0:
            return 0.0
        return self.total_bytes / self.file_count


# ── Top-level scan result ──────────────────────────────────────────────────

@dataclass
class ScanResult:
    """
    Complete result of a full repository scan.

    This is the canonical data structure written to .clockwork/repo_map.json
    and consumed by all downstream Clockwork subsystems.
    """

    # Identity
    scanned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    root: str = ""
    project_name: str = ""
    clockwork_version: str = "0.1"

    # Counts
    total_files: int = 0
    total_lines: int = 0
    total_bytes: int = 0

    # Languages
    primary_language: str = ""
    languages: dict[str, int] = field(default_factory=dict)
    language_details: list[LanguageSummary] = field(default_factory=list)

    # Structure
    files: list[FileEntry] = field(default_factory=list)
    directories: list[DirectoryEntry] = field(default_factory=list)
    directory_tree: dict[str, list[str]] = field(default_factory=dict)

    # Key items
    entry_points: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)

    # Framework / dependency hints
    frameworks: list[str] = field(default_factory=list)
    dependency_files: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Serialisation
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> "ScanResult":
        """Reconstruct from a plain dict (e.g. loaded from repo_map.json)."""
        # Rebuild nested models
        files = [
            FileEntry(
                **{k: v for k, v in f.items()
                   if k != "symbols"},
                symbols=[SymbolInfo(**s) for s in f.get("symbols", [])],
            )
            for f in data.get("files", [])
        ]
        dirs = [DirectoryEntry(**d) for d in data.get("directories", [])]
        lang_details = [
            LanguageSummary(**l) for l in data.get("language_details", [])
        ]
        import dataclasses as _dc
        _known = {f.name for f in _dc.fields(cls)}
        top = {
            k: v for k, v in data.items()
            if k not in ("files", "directories", "language_details") and k in _known
        }
        return cls(**top, files=files, directories=dirs, language_details=lang_details)

    @classmethod
    def from_json(cls, raw: str) -> "ScanResult":
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, clockwork_dir: Path) -> Path:
        """Write repo_map.json into *clockwork_dir*."""
        out = clockwork_dir / "repo_map.json"
        out.write_text(self.to_json(), encoding="utf-8")
        return out

    @classmethod
    def load(cls, clockwork_dir: Path) -> "ScanResult":
        """Load repo_map.json from *clockwork_dir*."""
        path = clockwork_dir / "repo_map.json"
        return cls.from_json(path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ #
    # Derived queries
    # ------------------------------------------------------------------ #

    def files_by_language(self, language: str) -> list[FileEntry]:
        return [f for f in self.files if f.language == language]

    def entry_point_files(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_entry_point]

    def test_file_entries(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_test]

    def config_file_entries(self) -> list[FileEntry]:
        return [f for f in self.files if f.is_config]
