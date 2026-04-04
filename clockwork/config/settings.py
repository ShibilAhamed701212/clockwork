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
    integration_output_dir: str = ".clockwork/integrations"
    legacy_root_integrations: bool = False
    auto_generate_ide_files: bool = False
    ide_formats: tuple[str, ...] = ()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return content if isinstance(content, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _as_format_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(v) for v in value if str(v).strip())
    return ()


def load_settings(repo_root: Path | None = None) -> Settings:
    root = (repo_root or Path.cwd()).resolve()
    config_path = root / ".clockwork" / "config.yaml"
    data = _read_yaml(config_path)

    runtime = data.get("runtime", {}) if isinstance(data.get("runtime"), dict) else {}

    mode = str(runtime.get("mode", data.get("mode", "safe")))
    autonomy = str(runtime.get("autonomy", data.get("autonomy", "restricted")))
    validation = str(runtime.get("validation", data.get("validation", "strict")))

    return Settings(
        mode=mode,
        autonomy=autonomy,
        validation=validation,
        integration_output_dir=str(data.get("integration_output_dir", ".clockwork/integrations")),
        legacy_root_integrations=_as_bool(data.get("legacy_root_integrations", False), False),
        auto_generate_ide_files=_as_bool(data.get("auto_generate_ide_files", False), False),
        ide_formats=_as_format_tuple(data.get("ide_formats", [])),
    )
