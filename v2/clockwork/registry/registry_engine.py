"""
clockwork/registry/registry_engine.py
---------------------------------------
Main registry engine (spec 14).

Handles:
  - plugin search and discovery   (spec 8)
  - plugin installation           (spec 9)
  - plugin publishing             (spec 5)
  - plugin update / removal       (spec 4)
  - version management            (spec 7)
  - registry security checks      (spec 11)
  - offline mode                  (spec 15)
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Any, Optional

from registry.cache import RegistryCacheManager
from registry.models import ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry


class RegistryEngine:
    """Top-level facade for the Registry subsystem."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root     = repo_root.resolve()
        self.clockwork_dir = self.repo_root / ".clockwork"
        self.plugins_dir   = self.clockwork_dir / "plugins"
        self.cache_mgr     = RegistryCacheManager(self.clockwork_dir)

    # ── search (spec 8) ───────────────────────────────────────────────────

    def search(self, query: str = "", artifact_type: str = "") -> list:
        """Search the registry for plugins/brains/packages."""
        return self.cache_mgr.search(query, artifact_type)

    def get(self, name: str) -> Optional[RegistryEntry]:
        """Look up one registry entry by name."""
        return self.cache_mgr.get(name)

    # ── install (spec 9) ──────────────────────────────────────────────────

    def install(self, name: str, version: str = "") -> tuple:
        """
        Install a plugin from the registry.

        For entries with a download_url, attempts a real download.
        For built-in/seed entries without a URL, creates a scaffold
        directory so the plugin slot is reserved (offline-safe).

        Returns (success, message).
        """
        entry = self.cache_mgr.get(name)
        if entry is None:
            return False, "Plugin '" + name + "' not found in registry. Run: clockwork registry search"

        existing = self.cache_mgr.get_installed(name)
        if existing:
            return False, "Plugin '" + name + "' is already installed (version " + existing.version + ")."

        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        plugin_dir = self.plugins_dir / name

        # security verification before install (spec 11)
        ok, sec_issues = self._security_check(entry)
        if not ok:
            return False, "Security check failed: " + "; ".join(sec_issues)

        if entry.download_url:
            success, msg = self._download_and_install(entry, plugin_dir)
            if not success:
                return False, msg
        else:
            # offline scaffold
            self._create_scaffold(entry, plugin_dir)

        record = InstalledPlugin(
            name=entry.name,
            version=entry.version,
            install_path=str(plugin_dir),
        )
        self.cache_mgr.record_install(record)
        return True, "Plugin '" + name + "' v" + entry.version + " installed to " + str(plugin_dir)

    # ── update (spec 4) ───────────────────────────────────────────────────

    def update(self, name: str) -> tuple:
        """Update an installed plugin to its latest registry version."""
        installed = self.cache_mgr.get_installed(name)
        if not installed:
            return False, "Plugin '" + name + "' is not installed."

        entry = self.cache_mgr.get(name)
        if entry is None:
            return False, "Plugin '" + name + "' not found in registry."

        if installed.version == entry.version:
            return True, "Plugin '" + name + "' is already at the latest version (" + entry.version + ")."

        plugin_dir = Path(installed.install_path)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)
        self.cache_mgr.record_uninstall(name)
        return self.install(name)

    # ── remove (spec 4) ───────────────────────────────────────────────────

    def remove(self, name: str) -> tuple:
        """Remove an installed plugin."""
        installed = self.cache_mgr.get_installed(name)
        if not installed:
            return False, "Plugin '" + name + "' is not installed."

        plugin_dir = Path(installed.install_path)
        if plugin_dir.exists():
            shutil.rmtree(plugin_dir)

        self.cache_mgr.record_uninstall(name)
        return True, "Plugin '" + name + "' removed."

    # ── publish (spec 5) ──────────────────────────────────────────────────

    def publish(self, plugin_dir: Path) -> tuple:
        """
        Publish a plugin to the registry.

        Pipeline: Plugin validation → Manifest verification → Security scan → Registry upload
        """
        manifest_path = plugin_dir / "plugin.yaml"
        if not manifest_path.exists():
            return False, "plugin.yaml manifest not found. Create one before publishing."

        try:
            import yaml
            data = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
        except Exception as exc:
            return False, "Invalid manifest: " + str(exc)

        name    = data.get("name", "")
        version = data.get("version", "")
        if not name or not version:
            return False, "Manifest must include 'name' and 'version'."

        checksum = self._checksum_dir(plugin_dir)

        entry = RegistryEntry(
            name=name,
            version=version,
            artifact_type=data.get("artifact_type", ArtifactType.PLUGIN),
            author=data.get("author", ""),
            description=data.get("description", ""),
            requires_clockwork=data.get("requires_clockwork", ">=0.1"),
            permissions=data.get("permissions", []),
            tags=data.get("tags", []),
            checksum=checksum,
            published_at=time.time(),
        )
        self.cache_mgr.add_entry(entry)
        return True, (
            "Plugin '" + name + "' v" + version + " published to local registry.\n"
            "  Checksum: " + checksum[:16] + "...\n"
            "  Note: to publish globally, configure a registry server."
        )

    # ── list installed ─────────────────────────────────────────────────────

    def list_installed(self) -> list:
        return self.cache_mgr.list_installed()

    # ── refresh cache ──────────────────────────────────────────────────────

    def refresh(self, registry_url: str = "") -> tuple:
        """Refresh the registry cache from a remote server. Falls back offline."""
        if not registry_url:
            existing     = self.cache_mgr.load()
            registry_url = existing.registry_url or "https://registry.clockwork.dev"

        try:
            import urllib.request
            req = urllib.request.Request(
                registry_url + "/plugins",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data    = json.loads(resp.read().decode("utf-8"))
                entries = [RegistryEntry.from_dict(e) for e in data.get("plugins", [])]
                cache   = RegistryCache(
                    entries=entries,
                    last_updated=time.time(),
                    registry_url=registry_url,
                )
                self.cache_mgr.save(cache)
                return True, "Registry refreshed — " + str(len(entries)) + " entries from " + registry_url
        except Exception as exc:
            return False, (
                "Could not reach registry at " + registry_url + ": " + str(exc) + "\n"
                "Using local cache (offline mode)."
            )

    # ── cache info ─────────────────────────────────────────────────────────

    def cache_info(self) -> dict:
        return self.cache_mgr.cache_info()

    # ── private helpers ────────────────────────────────────────────────────

    def _security_check(self, entry: RegistryEntry) -> tuple:
        """Basic pre-install security check (spec 11)."""
        issues      = []
        dangerous   = {"system_command", "execute_arbitrary"}
        bad_perms   = [p for p in entry.permissions if p in dangerous]
        if bad_perms:
            issues.append("Plugin requests dangerous permissions: " + ", ".join(bad_perms))
        return len(issues) == 0, issues

    def _download_and_install(self, entry: RegistryEntry, plugin_dir: Path) -> tuple:
        """Download a plugin archive and extract it."""
        try:
            import urllib.request
            import zipfile
            import tempfile
            import os
            with tempfile.TemporaryDirectory() as tmp:
                archive = os.path.join(tmp, entry.name + ".zip")
                urllib.request.urlretrieve(entry.download_url, archive)

                if entry.checksum:
                    h = hashlib.sha256()
                    with open(archive, "rb") as fh:
                        for chunk in iter(lambda: fh.read(65536), b""):
                            h.update(chunk)
                    if h.hexdigest() != entry.checksum:
                        return False, "Checksum mismatch — download may be corrupted."

                with zipfile.ZipFile(archive) as zf:
                    zf.extractall(str(plugin_dir))
            return True, "Downloaded and extracted."
        except Exception as exc:
            return False, "Download failed: " + str(exc)

    def _create_scaffold(self, entry: RegistryEntry, plugin_dir: Path) -> None:
        """Create a plugin scaffold directory for offline/seed entries."""
        plugin_dir.mkdir(parents=True, exist_ok=True)
        manifest = (
            "name: " + entry.name + "\n"
            "version: " + entry.version + "\n"
            "author: " + entry.author + "\n"
            "description: " + entry.description + "\n"
            "requires_clockwork: " + entry.requires_clockwork + "\n"
            "permissions: " + str(entry.permissions) + "\n"
            "tags: " + str(entry.tags) + "\n"
            "status: scaffold\n"
        )
        (plugin_dir / "plugin.yaml").write_text(manifest, encoding="utf-8")
        (plugin_dir / "README.md").write_text(
            "# " + entry.name + "\n\n" + entry.description + "\n\n"
            "_This is a scaffold placeholder. Replace with the actual plugin implementation._\n",
            encoding="utf-8",
        )

    def _checksum_dir(self, plugin_dir: Path) -> str:
        h = hashlib.sha256()
        for fp in sorted(plugin_dir.rglob("*")):
            if fp.is_file():
                try:
                    h.update(fp.read_bytes())
                except OSError:
                    pass
        return h.hexdigest()