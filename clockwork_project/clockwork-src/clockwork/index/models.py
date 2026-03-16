"""
clockwork/index/models.py
--------------------------
Data models for the Live Context Index subsystem.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EventType(str, Enum):
    CREATED  = "created"
    MODIFIED = "modified"
    DELETED  = "deleted"
    RENAMED  = "renamed"


@dataclass
class ChangeEvent:
    """A single filesystem change event placed into the queue."""

    event_type: str          # EventType value
    file_path:  str          # absolute or repo-relative path
    timestamp:  float        # unix timestamp
    src_path:   str = ""     # for renames: original path

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "file_path":  self.file_path,
            "timestamp":  self.timestamp,
            "src_path":   self.src_path,
        }


@dataclass
class IndexEntry:
    """
    Cached metadata for a single file in the index.

    Stored in .clockwork/index.db — fields match spec §11.
    """

    file_path:     str
    last_modified: float
    file_hash:     str
    size_bytes:    int    = 0
    language:      str    = ""
    module_type:   str    = ""      # "source" | "test" | "config" | "other"
    dependencies:  str    = "[]"    # JSON list of import strings
    layer:         str    = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path":     self.file_path,
            "last_modified": self.last_modified,
            "file_hash":     self.file_hash,
            "size_bytes":    self.size_bytes,
            "language":      self.language,
            "module_type":   self.module_type,
            "dependencies":  self.dependencies,
            "layer":         self.layer,
        }


@dataclass
class IndexStats:
    """Summary returned after a full index build or repair."""

    total_files:    int   = 0
    indexed_files:  int   = 0
    skipped_files:  int   = 0
    elapsed_ms:     float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_files":   self.total_files,
            "indexed_files": self.indexed_files,
            "skipped_files": self.skipped_files,
            "elapsed_ms":    round(self.elapsed_ms, 1),
        }


def compute_file_hash(path_str: str) -> str:
    """Return the SHA-256 hex digest of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(path_str, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""

