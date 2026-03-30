from __future__ import annotations

from pathlib import Path

from clockwork.registry.registry_engine import RegistryEngine


class PluginManager:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.engine = RegistryEngine(self.repo_root)

    def install(self, plugin_name: str) -> bool:
        success, _ = self.engine.install(plugin_name)
        return success

    def list(self) -> list[dict]:
        return [plugin.to_dict() for plugin in self.engine.list_installed()]

