from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from .clockwork/config.yaml."""

    mode: str = "safe"
    autonomy: str = "restricted"
    validation: str = "strict"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return content if isinstance(content, dict) else {}


def load_settings(repo_root: Path | None = None) -> Settings:
    root = (repo_root or Path.cwd()).resolve()
    config_path = root / ".clockwork" / "config.yaml"
    data = _read_yaml(config_path)
    return Settings(
        mode=str(data.get("mode", "safe")),
        autonomy=str(data.get("autonomy", "restricted")),
        validation=str(data.get("validation", "strict")),
    )

