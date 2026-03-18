"""
tests/test_registry.py
------------------------
Unit tests for the Registry & Ecosystem subsystem (spec 14).

Run with:
    pytest tests/test_registry.py -v
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from registry.models import (
    ArtifactType, InstalledPlugin, RegistryCache, RegistryEntry
)
from registry.cache import RegistryCacheManager
from registry.registry_engine import RegistryEngine


# ── Fixtures ───────────────────────────────────────────────────────────────

def _make_cw(tmp_path: Path) -> Path:
    cw = tmp_path / ".clockwork"
    cw.mkdir(parents=True, exist_ok=True)
    return cw


def _make_engine(tmp_path: Path) -> RegistryEngine:
    _make_cw(tmp_path)
    return RegistryEngine(tmp_path)


def _make_entry(name: str = "my_plugin", trusted: bool = False) -> RegistryEntry:
    return RegistryEntry(
        name=name,
        version="0.1.0",
        artifact_type=ArtifactType.PLUGIN,
        author="test_author",
        description="Test plugin " + name,
        tags=["test", "example"],
        permissions=["filesystem_read"],
        trusted=trusted,
    )


def _make_plugin_dir(tmp_path: Path, name: str = "my_plugin") -> Path:
    """Create a minimal plugin directory with a valid manifest."""
    plugin_dir = tmp_path / name
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest = (
        "name: " + name + "\n"
        "version: 0.1.0\n"
        "author: test\n"
        "description: A test plugin\n"
        "requires_clockwork: '>=0.1'\n"
        "permissions: []\n"
        "tags: [test]\n"
    )
    (plugin_dir / "plugin.yaml").write_text(manifest, encoding="utf-8")
    (plugin_dir / "main.py").write_text("# plugin entry\n", encoding="utf-8")
    return plugin_dir


# ── RegistryEntry ──────────────────────────────────────────────────────────

class TestRegistryEntry:
    def test_to_dict_round_trip(self):
        e  = _make_entry("test")
        d  = e.to_dict()
        e2 = RegistryEntry.from_dict(d)
        assert e2.name    == "test"
        assert e2.version == "0.1.0"

    def test_matches_query_by_name(self):
        e = _make_entry("security_scanner")
        assert e.matches_query("security") is True
        assert e.matches_query("docker")   is False

    def test_matches_query_empty_returns_true(self):
        assert _make_entry("anything").matches_query("") is True

    def test_matches_query_by_tag(self):
        e = RegistryEntry(name="x", version="1.0", tags=["linting", "style"])
        assert e.matches_query("linting") is True

    def test_matches_query_by_description(self):
        e = RegistryEntry(name="x", version="1.0", description="Audits dependencies for CVEs")
        assert e.matches_query("CVE") is True


# ── RegistryCache ──────────────────────────────────────────────────────────

class TestRegistryCache:
    def test_to_dict_round_trip(self):
        cache = RegistryCache(entries=[_make_entry("a"), _make_entry("b")])
        d     = cache.to_dict()
        c2    = RegistryCache.from_dict(d)
        assert len(c2.entries) == 2

    def test_search_returns_matches(self):
        cache = RegistryCache(entries=[
            _make_entry("security_scanner"),
            _make_entry("doc_generator"),
        ])
        results = cache.search("security")
        assert len(results) == 1
        assert results[0].name == "security_scanner"

    def test_search_empty_returns_all(self):
        cache = RegistryCache(entries=[_make_entry("a"), _make_entry("b")])
        assert len(cache.search("")) == 2

    def test_get_by_name(self):
        cache = RegistryCache(entries=[_make_entry("plugin_x")])
        assert cache.get("plugin_x") is not None
        assert cache.get("missing")  is None

    def test_is_stale_fresh(self):
        cache = RegistryCache(last_updated=time.time())
        assert cache.is_stale(ttl_seconds=3600) is False

    def test_is_stale_old(self):
        cache = RegistryCache(last_updated=time.time() - 7200)
        assert cache.is_stale(ttl_seconds=3600) is True


# ── RegistryCacheManager ───────────────────────────────────────────────────

class TestRegistryCacheManager:
    def test_ensure_populated_seeds_entries(self, tmp_path):
        cw    = _make_cw(tmp_path)
        mgr   = RegistryCacheManager(cw)
        cache = mgr.ensure_populated()
        assert len(cache.entries) > 0

    def test_save_and_load(self, tmp_path):
        cw    = _make_cw(tmp_path)
        mgr   = RegistryCacheManager(cw)
        cache = RegistryCache(entries=[_make_entry("test_plugin")])
        mgr.save(cache)
        loaded = mgr.load()
        assert any(e.name == "test_plugin" for e in loaded.entries)

    def test_search_delegates_to_cache(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        mgr.ensure_populated()
        results = mgr.search("security")
        assert isinstance(results, list)

    def test_add_and_get_entry(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        mgr.ensure_populated()
        mgr.add_entry(_make_entry("new_plugin"))
        assert mgr.get("new_plugin") is not None

    def test_remove_entry(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        mgr.add_entry(_make_entry("to_remove"))
        assert mgr.remove_entry("to_remove") is True
        assert mgr.get("to_remove")          is None

    def test_record_and_list_installed(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        p   = InstalledPlugin(
            name="my_plugin", version="0.1.0",
            install_path=str(tmp_path / "my_plugin")
        )
        mgr.record_install(p)
        installed = mgr.list_installed()
        assert any(x.name == "my_plugin" for x in installed)

    def test_record_uninstall(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        p   = InstalledPlugin("test", "0.1", str(tmp_path / "test"))
        mgr.record_install(p)
        assert mgr.record_uninstall("test") is True
        assert mgr.get_installed("test")    is None

    def test_cache_info_keys(self, tmp_path):
        cw  = _make_cw(tmp_path)
        mgr = RegistryCacheManager(cw)
        mgr.ensure_populated()
        info = mgr.cache_info()
        assert "entries"      in info
        assert "installed"    in info
        assert "is_stale"     in info
        assert "registry_url" in info


# ── RegistryEngine ─────────────────────────────────────────────────────────

class TestRegistryEngine:
    def test_search_returns_results(self, tmp_path):
        reg     = _make_engine(tmp_path)
        results = reg.search()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_with_query(self, tmp_path):
        reg     = _make_engine(tmp_path)
        results = reg.search("security")
        assert all("security" in e.name.lower()
                   or "security" in e.description.lower()
                   or any("security" in t for t in e.tags)
                   for e in results)

    def test_get_known_plugin(self, tmp_path):
        reg   = _make_engine(tmp_path)
        entry = reg.get("security_scanner")
        assert entry is not None
        assert entry.version != ""

    def test_get_missing_returns_none(self, tmp_path):
        reg = _make_engine(tmp_path)
        assert reg.get("does_not_exist_xyz") is None

    def test_install_known_plugin(self, tmp_path):
        reg    = _make_engine(tmp_path)
        ok, msg = reg.install("security_scanner")
        assert ok is True
        assert "installed" in msg.lower()

    def test_install_already_installed(self, tmp_path):
        reg = _make_engine(tmp_path)
        reg.install("security_scanner")
        ok, msg = reg.install("security_scanner")
        assert ok is False
        assert "already installed" in msg.lower()

    def test_install_unknown_plugin(self, tmp_path):
        reg    = _make_engine(tmp_path)
        ok, msg = reg.install("totally_unknown_xyz")
        assert ok is False
        assert "not found" in msg.lower()

    def test_list_installed_after_install(self, tmp_path):
        reg = _make_engine(tmp_path)
        reg.install("security_scanner")
        installed = reg.list_installed()
        assert any(p.name == "security_scanner" for p in installed)

    def test_remove_installed_plugin(self, tmp_path):
        reg = _make_engine(tmp_path)
        reg.install("dependency_audit")
        ok, msg = reg.remove("dependency_audit")
        assert ok is True
        assert "removed" in msg.lower()

    def test_remove_not_installed(self, tmp_path):
        reg    = _make_engine(tmp_path)
        ok, msg = reg.remove("never_installed")
        assert ok is False

    def test_update_not_installed(self, tmp_path):
        reg    = _make_engine(tmp_path)
        ok, msg = reg.update("not_there")
        assert ok is False

    def test_update_already_latest(self, tmp_path):
        reg = _make_engine(tmp_path)
        reg.install("security_scanner")
        ok, msg = reg.update("security_scanner")
        assert ok is True
        assert "latest" in msg.lower()

    def test_publish_creates_entry(self, tmp_path):
        reg        = _make_engine(tmp_path)
        plugin_dir = _make_plugin_dir(tmp_path, "my_new_plugin")
        ok, msg    = reg.publish(plugin_dir)
        assert ok is True
        assert reg.get("my_new_plugin") is not None

    def test_publish_missing_manifest(self, tmp_path):
        reg = _make_engine(tmp_path)
        d   = tmp_path / "bad_plugin"
        d.mkdir()
        ok, msg = reg.publish(d)
        assert ok is False
        assert "manifest" in msg.lower()

    def test_cache_info_structure(self, tmp_path):
        reg  = _make_engine(tmp_path)
        info = reg.cache_info()
        assert "entries"   in info
        assert "installed" in info
        assert "is_stale"  in info

    def test_refresh_offline_fallback(self, tmp_path):
        reg    = _make_engine(tmp_path)
        ok, msg = reg.refresh("http://localhost:19999")  # unreachable
        assert ok is False
        assert "offline" in msg.lower() or "could not reach" in msg.lower()