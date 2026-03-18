"""
clockwork/registry/__init__.py
--------------------------------
Registry & Ecosystem subsystem (spec 14).

Transforms Clockwork from a standalone tool into a platform by
providing plugin discovery, installation, publishing, and versioning.

CLI commands:
    clockwork registry search [query]
    clockwork registry info <name>
    clockwork registry refresh
    clockwork registry status
    clockwork plugin install <name>
    clockwork plugin list
    clockwork plugin update <name>
    clockwork plugin remove <name>
    clockwork plugin publish [path]
"""

from registry.registry_engine import RegistryEngine
from registry.cache import RegistryCacheManager
from registry.models import (
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