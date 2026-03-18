"""
clockwork/registry/models.py
-----------------------------
Data models for the Registry & Ecosystem subsystem (spec §14).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


# ── Artifact types (spec §2) ───────────────────────────────────────────────

class ArtifactType:
    PLUGIN  = "plugin"
    BRAIN   = "brain"
    PACKAGE = "package"


# ── Registry entry ─────────────────────────────────────────────────────────

@dataclass
class RegistryEntry:
    """
    One record in the registry index.

    Represents a published plugin, brain, or package.
    """

    name:               str
    version:            str
    artifact_type:      str             = ArtifactType.PLUGIN
    author:             str             = ""
    description:        str             = ""
    requires_clockwork: str             = ">=0.1"
    permissions:        list[str]       = field(default_factory=list)
    tags:               list[str]       = field(default_factory=list)
    checksum:           str             = ""
    download_url:       str             = ""
    published_at:       float           = field(default_factory=time.time)
    trusted:            bool            = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":               self.name,
            "version":            self.version,
            "artifact_type":      self.artifact_type,
            "author":             self.author,
            "description":        self.description,
            "requires_clockwork": self.requires_clockwork,
            "permissions":        self.permissions,
            "tags":               self.tags,
            "checksum":           self.checksum,
            "download_url":       self.download_url,
            "published_at":       self.published_at,
            "trusted":            self.trusted,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RegistryEntry":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            artifact_type=d.get("artifact_type", ArtifactType.PLUGIN),
            author=d.get("author", ""),
            description=d.get("description", ""),
            requires_clockwork=d.get("requires_clockwork", ">=0.1"),
            permissions=d.get("permissions", []),
            tags=d.get("tags", []),
            checksum=d.get("checksum", ""),
            download_url=d.get("download_url", ""),
            published_at=d.get("published_at", time.time()),
            trusted=d.get("trusted", False),
        )

    def matches_query(self, query: str) -> bool:
        """Return True if this entry matches a search query string."""
        q = query.lower()
        return (
            q in self.name.lower()
            or q in self.description.lower()
            or any(q in t.lower() for t in self.tags)
            or q in self.author.lower()
        )


# ── Registry cache (spec §14) ──────────────────────────────────────────────

@dataclass
class RegistryCache:
    """
    Local cache of registry metadata stored at
    .clockwork/registry_cache.json
    """

    entries:      list[RegistryEntry]   = field(default_factory=list)
    last_updated: float                 = 0.0
    registry_url: str                   = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "entries":      [e.to_dict() for e in self.entries],
            "last_updated": self.last_updated,
            "registry_url": self.registry_url,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RegistryCache":
        return cls(
            entries=[RegistryEntry.from_dict(e) for e in d.get("entries", [])],
            last_updated=d.get("last_updated", 0.0),
            registry_url=d.get("registry_url", ""),
        )

    def is_stale(self, ttl_seconds: float = 3600.0) -> bool:
        return (time.time() - self.last_updated) > ttl_seconds

    def search(self, query: str) -> list[RegistryEntry]:
        if not query:
            return list(self.entries)
        return [e for e in self.entries if e.matches_query(query)]

    def get(self, name: str) -> Optional[RegistryEntry]:
        for e in self.entries:
            if e.name == name:
                return e
        return None


# ── Install record ─────────────────────────────────────────────────────────

@dataclass
class InstalledPlugin:
    """Record of a locally installed plugin."""

    name:          str
    version:       str
    install_path:  str
    installed_at:  float = field(default_factory=time.time)
    enabled:       bool  = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "name":         self.name,
            "version":      self.version,
            "install_path": self.install_path,
            "installed_at": self.installed_at,
            "enabled":      self.enabled,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "InstalledPlugin":
        return cls(
            name=d.get("name", ""),
            version=d.get("version", "0.1"),
            install_path=d.get("install_path", ""),
            installed_at=d.get("installed_at", time.time()),
            enabled=d.get("enabled", True),
        )

