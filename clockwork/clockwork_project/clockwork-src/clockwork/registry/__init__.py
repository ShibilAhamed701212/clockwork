"""
clockwork/registry/__init__.py
--------------------------------
Registry & Ecosystem subsystem (spec §14).

Transforms Clockwork from a standalone tool into a platform by
providing plugin discovery, installation, publishing, and versioning.

Supports offline mode — the local cache works without a live server.

Public API::

    from clockwork.registry import RegistryEngine

    reg = RegistryEngine(repo_root=Path("."))

    results = reg.search("security")
    reg.install("security_scanner")
    reg.list_installed()
    reg.publish(Path(".clockwork/plugins/my_plugin"))

CLI commands added:
    clockwork registry search [query]
    clockwork registry info <n>
    clockwork registry refresh
    clockwork registry status

    clockwork plugin install <n>
    clockwork plugin list
    clockwork plugin update <n>
    clockwork plugin remove <n>
    clockwork plugin publish [path]
"""

from clockwork.registry.registry_engine import RegistryEngine
from clockwork.registry.cache import RegistryCacheManager
from clockwork.registry.models import (
    ArtifactType,
    InstalledPlugin,
    RegistryCache,
    RegistryEntry,
)

__all__ = [
    "RegistryEngine",
    "RegistryCacheManager",
    "ArtifactType",
    "InstalledPlugin",
    "RegistryCache",
    "RegistryEntry",
]

