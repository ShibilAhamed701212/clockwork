from __future__ import annotations
import logging
from pathlib import Path
import yaml
from clockwork.rules.models import RuleConfig

logger = logging.getLogger(__name__)

_DEFAULT_RULES_YAML = """
rules:
  forbid_core_file_deletion: true
  require_tests_for_new_modules: true
  enforce_architecture_layers: true
  protected_files:
    - ".clockwork/context.yaml"
    - ".clockwork/rules.md"
    - ".clockwork/rules.yaml"
    - ".clockwork/repo_map.json"
  protected_directories:
    - "core/"
    - "database/"
  forbid_file_patterns:
    - "*.env"
    - ".env"
    - "credentials.json"
    - "secrets*"
  require_tests_for:
    - "backend/"
    - "services/"
    - "clockwork/"
  dependency_files:
    - "requirements.txt"
    - "pyproject.toml"
    - "package.json"
"""


class RuleLoader:
    def __init__(self, clockwork_dir: Path) -> None:
        self._clockwork_dir = clockwork_dir
        self._rules_yaml_path = clockwork_dir / "rules.yaml"

    def load(self) -> RuleConfig:
        if not self._rules_yaml_path.exists():
            logger.warning("rules.yaml not found — using defaults")
            return RuleConfig()
        try:
            raw = self._rules_yaml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw) or {}
            return RuleConfig.from_dict(data)
        except Exception as exc:
            logger.error("Cannot load rules.yaml: %s — using defaults", exc)
            return RuleConfig()

    def write_defaults(self, overwrite: bool = False) -> bool:
        if self._rules_yaml_path.exists() and not overwrite:
            return False
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        self._rules_yaml_path.write_text(_DEFAULT_RULES_YAML.strip(), encoding="utf-8")
        return True

    def save(self, config: RuleConfig) -> None:
        self._clockwork_dir.mkdir(parents=True, exist_ok=True)
        with self._rules_yaml_path.open("w", encoding="utf-8") as fh:
            yaml.dump(config.to_dict(), fh, default_flow_style=False, sort_keys=False)
