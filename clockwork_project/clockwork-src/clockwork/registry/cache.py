"""
clockwork/registry/cache.py
----------------------------
Local registry cache manager (spec §14, §15).

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

from .models import ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry


# ── Built-in seed entries (offline catalogue) ──────────────────────────────

_SEED_ENTRIES: list[dict] = [
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
        "name": "api_security_checker",
        "version": "0.1.1",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Checks REST API endpoints for common security misconfigurations",
        "tags": ["security", "api", "rest"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": False,
    },
    {
        "name": "doc_generator",
        "version": "0.1.0",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "community",
        "description": "Generates markdown documentation from code symbols and docstrings",
        "tags": ["documentation", "codegen", "markdown"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read", "repository_write"],
        "trusted": False,
    },
    {
        "name": "ci_analyzer",
        "version": "0.1.2",
        "artifact_type": ArtifactType.PLUGIN,
        "author": "clockwork-team",
        "description": "Analyses CI/CD pipeline configurations for best practices",
        "tags": ["ci", "devops", "github-actions", "analysis"],
        "requires_clockwork": ">=0.1",
        "permissions": ["filesystem_read"],
        "trusted": True,
    },
]


class RegistryCacheManager:
    """
    Manages the local registry cache at .clockwork/registry_cache.json.

    Supports offline mode — falls back to seed entries when the cache
    is empty or the registry server is unreachable (spec §15).

    Usage::

        mgr = RegistryCacheManager(clockwork_dir)
        mgr.ensure_populated()
        results = mgr.search("security")
        entry   = mgr.get("security_scanner")
    """

    CACHE_TTL = 3600.0    # 1 hour

    def __init__(self, clockwork_dir: Path) -> None:
        self.clockwork_dir = clockwork_dir
        self.cache_path    = clockwork_dir / "registry_cache.json"
        self.installed_path = clockwork_dir / "installed_plugins.json"

    # ── cache lifecycle ────────────────────────────────────────────────────

    def load(self) -> RegistryCache:
        """Load cache from disk, returning empty cache if not found."""
        import logging as _logging
        _log = _logging.getLogger("clockwork.registry.cache")
        if not self.cache_path.exists():
            return RegistryCache()
        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))
            return RegistryCache.from_dict(data)
        except json.JSONDecodeError as exc:
            _log.warning("Registry cache corrupted (%s); returning empty cache. Original preserved at %s.bak", exc, self.cache_path)
            try:
                import shutil as _shutil
                _shutil.copy2(self.cache_path, str(self.cache_path) + ".bak")
            except OSError:
                pass
            return RegistryCache()
        except Exception as exc:
            _log.warning("Failed to load registry cache: %s", exc)
            return RegistryCache()

    def save(self, cache: RegistryCache) -> None:
        """Persist cache to disk."""
        self.clockwork_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(cache.to_dict(), indent=2), encoding="utf-8"
        )

    def ensure_populated(self) -> RegistryCache:
        """
        Load cache; if empty or missing, seed with built-in entries.
        Returns the populated cache.
        """
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

    def search(self, query: str = "", artifact_type: str = "") -> list[RegistryEntry]:
        """Search the local cache. Works offline."""
        cache = self.ensure_populated()
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
        cache = self.ensure_populated()
        cache.entries = [e for e in cache.entries if e.name != entry.name]
        cache.entries.append(entry)
        cache.last_updated = time.time()
        self.save(cache)

    def remove_entry(self, name: str) -> bool:
        cache = self.ensure_populated()
        before = len(cache.entries)
        cache.entries = [e for e in cache.entries if e.name != name]
        if len(cache.entries) < before:
            self.save(cache)
            return True
        return False

    # ── installed plugins ──────────────────────────────────────────────────

    def list_installed(self) -> list[InstalledPlugin]:
        if not self.installed_path.exists():
            return []
        try:
            data = json.loads(self.installed_path.read_text(encoding="utf-8"))
            return [InstalledPlugin.from_dict(p) for p in data]
        except Exception:
            return []

    def record_install(self, plugin: InstalledPlugin) -> None:
        installed = self.list_installed()
        installed = [p for p in installed if p.name != plugin.name]
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

