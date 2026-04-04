from __future__ import annotations

from pathlib import Path

from clockwork.registry.registry_engine import RegistryEngine


def search_plugins(term: str, repo_root: Path | None = None) -> list[dict]:
    root = (repo_root or Path.cwd()).resolve()
    engine = RegistryEngine(root)
    return [entry.to_dict() for entry in engine.search(term)]

