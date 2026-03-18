"""
clockwork/registry/api/routes.py
----------------------------------
Registry API route definitions (spec 14, 18).

Endpoints:
    GET  /plugins               — list all plugins
    GET  /plugins/{name}        — get plugin info
    POST /plugins               — publish a plugin
    GET  /packages              — list all packages
    GET  /packages/{name}       — get package info

These are definitions only. Mount with a compatible WSGI/ASGI
server (e.g. FastAPI, Flask) when running a registry server.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from registry.cache import RegistryCacheManager
from registry.models import ArtifactType, RegistryEntry

# Registry data dir (server-side)
_REGISTRY_DIR = Path(".clockwork")


def _get_manager() -> RegistryCacheManager:
    return RegistryCacheManager(_REGISTRY_DIR)


# ── GET /plugins ──────────────────────────────────────────────────────────

def get_plugins(query: str = "", artifact_type: str = "") -> Dict[str, Any]:
    """Return all plugins matching an optional query."""
    mgr     = _get_manager()
    results = mgr.search(query, artifact_type)
    return {
        "plugins": [e.to_dict() for e in results],
        "count":   len(results),
        "ts":      time.time(),
    }


# ── GET /plugins/{name} ───────────────────────────────────────────────────

def get_plugin(name: str) -> Dict[str, Any]:
    """Return a single plugin by name."""
    mgr   = _get_manager()
    entry = mgr.get(name)
    if entry is None:
        return {"error": "Plugin '" + name + "' not found.", "status": 404}
    return {"plugin": entry.to_dict(), "status": 200}


# ── POST /plugins ─────────────────────────────────────────────────────────

def publish_plugin(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Publish a new plugin or update an existing one.

    payload must include: name, version, artifact_type, author, description.
    """
    required = ["name", "version"]
    for field in required:
        if field not in payload:
            return {"error": "Missing required field: " + field, "status": 400}

    try:
        entry = RegistryEntry.from_dict(payload)
        entry.published_at = time.time()
        mgr = _get_manager()
        mgr.add_entry(entry)
        return {"message": "Plugin '" + entry.name + "' published.", "status": 201}
    except Exception as exc:
        return {"error": "Publish failed: " + str(exc), "status": 500}


# ── GET /packages ─────────────────────────────────────────────────────────

def get_packages() -> Dict[str, Any]:
    """Return all knowledge packages."""
    mgr     = _get_manager()
    results = mgr.search(artifact_type=ArtifactType.PACKAGE)
    return {
        "packages": [e.to_dict() for e in results],
        "count":    len(results),
    }


# ── GET /packages/{name} ──────────────────────────────────────────────────

def get_package(name: str) -> Dict[str, Any]:
    """Return a single knowledge package by name."""
    mgr   = _get_manager()
    entry = mgr.get(name)
    if entry is None or entry.artifact_type != ArtifactType.PACKAGE:
        return {"error": "Package '" + name + "' not found.", "status": 404}
    return {"package": entry.to_dict(), "status": 200}


# ── Route map (for wiring into a web framework) ───────────────────────────

ROUTES = [
    ("GET",  "/plugins",         get_plugins),
    ("GET",  "/plugins/{name}",  get_plugin),
    ("POST", "/plugins",         publish_plugin),
    ("GET",  "/packages",        get_packages),
    ("GET",  "/packages/{name}", get_package),
]