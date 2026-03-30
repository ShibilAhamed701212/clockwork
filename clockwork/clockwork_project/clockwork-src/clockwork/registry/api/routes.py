from __future__ import annotations

from pathlib import Path

from clockwork.registry.registry_engine import RegistryEngine


def list_registry_entries(repo_root: Path | None = None) -> list[dict]:
    root = (repo_root or Path.cwd()).resolve()
    return [entry.to_dict() for entry in RegistryEngine(root).search()]


def list_installed_plugins(repo_root: Path | None = None) -> list[dict]:
    root = (repo_root or Path.cwd()).resolve()
    return [entry.to_dict() for entry in RegistryEngine(root).list_installed()]

