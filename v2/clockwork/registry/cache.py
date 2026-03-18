"""
clockwork/registry/cache.py
----------------------------
Local registry cache manager (spec 14, 15).

Manages .clockwork/registry_cache.json so users can search and
discover plugins even when the registry server is offline.

On first use (empty cache) a set of built-in example entries is
seeded so the tool works immediately without a live server.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional

from registry.models import ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry


# ── Built-in seed entries (offline catalogue) ──────────────────────────────

_SEED_ENTRIES = [
    {
        "name": "security_scanner",
        "version": "0.2.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Advanced security scanning — secrets detection, CVE checks, SAST rules",
        "tags": ["security", "scanner", "sast"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "dependency_audit",
        "version": "0.1.3",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Audits third-party dependencies for known vulnerabilities",
        "tags": ["security", "dependencies", "audit"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "network_access"],
        "trusted": True,
    },
    {
        "name": "architecture_analyzer",
        "version": "0.3.1",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Detects architectural anti-patterns and layer violations",
        "tags": ["architecture", "analysis", "patterns"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "test_generator",
        "version": "0.1.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Auto-generates unit test scaffolding for Python modules",
        "tags": ["testing", "codegen", "python"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "repository_write"],
        "trusted": False,
    },
    {
        "name": "ollama_brain",
        "version": "0.2.0",
        "artifact_type": ArtifactType.BRAIN,
        "author": "clockwork-team",
        "description": "Local LLM reasoning engine powered by Ollama",
        "tags": ["brain", "llm", "local", "ollama"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "performance_optimizer",
        "version": "0.1.2",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Profiles hotspots and suggests algorithmic improvements",
        "tags": ["performance", "profiling", "optimization"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
    {
        "name": "cross_project_package",
        "version": "0.1.0",
        "artifact_type": ArtifactType.PACKAGE,
        "author": "clockwork-team",
        "description": "Portable project intelligence for cross-project knowledge sharing",
        "tags": ["knowledge", "sharing", "cross-project"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
]


class RegistryCacheManager:
    """Manages the local registry cache file."""

    CACHE_TTL = 3600.0  # 1 hour

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir  = clockwork_dir
        self.cache_path     = clockwork_dir / "registry_cache.json"
        self.installed_path = clockwork_dir / "installed_plugins.json"

    # ── load / save ────────────────────────────────────────────────────────

    def load(self) -> RegistryCache:
        if not self.cache_path.exists():
            return RegistryCache()
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return RegistryCache.from_dict(data)
        except Exception:
            return RegistryCache()

    def save(self, cache: RegistryCache) -> None:
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(cache.to_dict(), indent=2), encoding="utf-8"
        )

    def ensure_populated(self) -> RegistryCache:
        """Load cache; if empty seed with built-in entries."""
        cache = self.load()
        if not cache.entries:
            cache = self._seed()
            self.save(cache)
        return cache

    def _seed(self) -> RegistryCache:
        entries = [RegistryEntry.from_dict(e) for e in _SEED_ENTRIES]
        return RegistryCache(
            entries=entries,
            last_updated=time.time(),
            registry_url="https://registry.clockwork.dev",
        )

    # ── search + lookup ────────────────────────────────────────────────────

    def search(self, query: str = "", artifact_type: str = "") -> list:
        """Search the local cache. Works offline."""
        cache   = self.ensure_populated()
        results = cache.search(query)
        if artifact_type:
            results = [r for r in results if r.artifact_type == artifact_type]
        return results

    def get(self, name: str) -> Optional[RegistryEntry]:
        """Look up one entry by name."""
        cache = self.ensure_populated()
        return cache.get(name)

    def add_entry(self, entry: RegistryEntry) -> None:
        """Add or update an entry in the cache (used by publish)."""
        cache         = self.ensure_populated()
        cache.entries = [e for e in cache.entries if e.name != entry.name]
        cache.entries.append(entry)
        cache.last_updated = time.time()
        self.save(cache)

    def remove_entry(self, name: str) -> bool:
        cache  = self.ensure_populated()
        before = len(cache.entries)
        cache.entries = [e for e in cache.entries if e.name != name]
        if len(cache.entries) < before:
            self.save(cache)
            return True
        return False

    # ── installed plugins ──────────────────────────────────────────────────

    def list_installed(self) -> list:
        if not self.installed_path.exists():
            return []
        try:
            data = json.loads(self.installed_path.read_text(encoding="utf-8"))
            return [InstalledPlugin.from_dict(p) for p in data]
        except Exception:
            return []

    def record_install(self, plugin: InstalledPlugin) -> None:
        installed  = self.list_installed()
        installed  = [p for p in installed if p.name != plugin.name]
        installed.append(plugin)
        self.installed_path.write_text(
            json.dumps([p.to_dict() for p in installed], indent=2),
            encoding="utf-8",
        )

    def record_uninstall(self, name: str) -> bool:
        installed = self.list_installed()
        before    = len(installed)
        installed = [p for p in installed if p.name != name]
        if len(installed) < before:
            self.installed_path.write_text(
                json.dumps([p.to_dict() for p in installed], indent=2),
                encoding="utf-8",
            )
            return True
        return False

    def get_installed(self, name: str) -> Optional[InstalledPlugin]:
        for p in self.list_installed():
            if p.name == name:
                return p
        return None

    def cache_info(self) -> dict:
        cache = self.load()
        return {
            "entries":      len(cache.entries),
            "last_updated": cache.last_updated,
            "registry_url": cache.registry_url,
            "is_stale":     cache.is_stale(self.CACHE_TTL),
            "installed":    len(self.list_installed()),
        }