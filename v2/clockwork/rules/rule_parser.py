import yaml
import json
from pathlib import Path
from typing import Dict, List

RULES_YAML = Path(".clockwork/rules.yaml")
RULES_MD   = Path("rules/rules.md")

DEFAULT_RULES = {
    "safety": {
        "forbid_core_file_deletion": True,
        "protect_clockwork_directory": True,
        "block_unverified_code_execution": True,
        "no_unsafe_file_operations": True,
    },
    "architecture": {
        "enforce_architecture_layers": True,
        "restrict_cross_layer_access": True,
        "require_module_boundaries": True,
    },
    "dependency": {
        "new_dependency_must_be_declared": True,
        "removed_dependency_must_not_be_referenced": True,
        "no_version_conflicts": True,
    },
    "development": {
        "new_module_requires_test": True,
        "require_documentation_for_public_api": False,
    },
    "context": {
        "context_must_match_repository": True,
        "no_stale_memory_allowed": True,
    },
}

PRIORITY = {
    "safety": 1,
    "architecture": 2,
    "dependency": 3,
    "development": 4,
    "context": 5,
}

class RuleParser:
    def __init__(self):
        self.rules = {}

    def load(self) -> Dict:
        if RULES_YAML.exists():
            with open(RULES_YAML) as f:
                loaded = yaml.safe_load(f) or {}
            self.rules = self._merge(DEFAULT_RULES, loaded)
        else:
            self.rules = DEFAULT_RULES
            self._persist_defaults()
        return self.rules

    def _merge(self, base: Dict, override: Dict) -> Dict:
        result = dict(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(result.get(k), dict):
                result[k] = self._merge(result[k], v)
            else:
                result[k] = v
        return result

    def _persist_defaults(self):
        RULES_YAML.parent.mkdir(parents=True, exist_ok=True)
        with open(RULES_YAML, "w") as f:
            yaml.dump(DEFAULT_RULES, f, default_flow_style=False)

    def get_category(self, category: str) -> Dict:
        return self.rules.get(category, {})

    def is_enabled(self, category: str, rule: str) -> bool:
        return self.rules.get(category, {}).get(rule, False)

    def get_priority(self, category: str) -> int:
        return PRIORITY.get(category, 99)

    def all_rules(self) -> Dict:
        return dict(self.rules)

    def load_plugins(self) -> List[Dict]:
        plugin_dir = Path(".clockwork/plugins")
        plugins = []
        if plugin_dir.exists():
            for f in plugin_dir.glob("*.yaml"):
                try:
                    with open(f) as fp:
                        plugins.append(yaml.safe_load(fp) or {})
                except Exception:
                    pass
        return plugins