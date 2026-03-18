from pathlib import Path
from typing import Dict, List, Tuple

PROTECTED_FILES = [
    ".clockwork/context.yaml",
    ".clockwork/rules.md",
    ".clockwork/repo_map.json",
    ".clockwork/tasks.json",
    ".clockwork/agents.json",
]

PROTECTED_DIRS = [
    ".clockwork",
    "config",
]

REQUIRED_STRUCTURE = [
    "cli", "scanner", "context", "rules", "brain",
    "graph", "agents", "validation", "state",
    "recovery", "security", "packaging", "registry",
    "config", "logs", ".clockwork",
]

class StructureRules:
    def __init__(self, root: Path = Path(".")):
        self.root = root

    def validate_change(self, changed_path: str) -> Tuple[bool, str, str]:
        p = changed_path.replace("\\", "/")
        for pf in PROTECTED_FILES:
            if p.endswith(pf) or pf in p:
                return False, "high", "Protected file modification blocked: " + pf
        for pd in PROTECTED_DIRS:
            if p.startswith(pd + "/") or ("/" + pd + "/") in p:
                return False, "high", "Protected directory modification blocked: " + pd
        return True, "none", "ok"

    def validate_structure(self) -> Tuple[bool, List[str]]:
        errors = []
        for d in REQUIRED_STRUCTURE:
            if not (self.root / d).exists():
                errors.append("Missing required directory: " + d)
        return len(errors) == 0, errors

    def check_test_exists(self, module_path: str) -> Tuple[bool, str]:
        p = Path(module_path)
        if p.suffix != ".py":
            return True, "ok"
        if "test" in p.name or "tests" in str(p):
            return True, "ok"
        expected_test = self.root / "tests" / ("test_" + p.name)
        if not expected_test.exists():
            return False, "Missing test for module: " + module_path + " -> expected: " + str(expected_test)
        return True, "ok"

    def validate_layers(self, changed_path: str) -> Tuple[bool, str]:
        layer_map = {
            "cli": ["config", "scanner", "context", "state"],
            "scanner": ["config"],
            "context": ["config", "state"],
            "brain": ["context", "graph", "rules", "config"],
            "agents": ["brain", "context", "validation", "security", "config"],
            "validation": ["context", "config"],
            "recovery": ["state", "context", "config"],
            "graph": ["config"],
            "rules": ["config", "context"],
        }
        parts = changed_path.replace("\\", "/").split("/")
        if not parts:
            return True, "ok"
        layer = parts[0]
        return True, "ok"