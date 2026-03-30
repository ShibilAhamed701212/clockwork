from __future__ import annotations

from pathlib import Path

from clockwork.registry.registry_engine import RegistryEngine


class RegistryClient:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.engine = RegistryEngine(self.repo_root)

    def list(self) -> list[dict]:
        return [item.to_dict() for item in self.engine.search()]

