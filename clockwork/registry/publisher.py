from __future__ import annotations

from pathlib import Path

from clockwork.registry.registry_engine import RegistryEngine


def publish_plugin(plugin_dir: str | Path, repo_root: Path | None = None) -> tuple[bool, str]:
    root = (repo_root or Path.cwd()).resolve()
    engine = RegistryEngine(root)
    return engine.publish(Path(plugin_dir))

