import re
from pathlib import Path
from typing import Dict, List, Tuple

DANGEROUS_PACKAGES = [
    "ld-linux", "pwntools", "scapy",
]

class DependencyRules:
    def __init__(self, root: Path = Path(".")):
        self.root = root

    def validate_new_dependency(self, dep_name: str, declared_deps: List[str]) -> Tuple[bool, str, str]:
        if dep_name.lower() in [d.lower() for d in DANGEROUS_PACKAGES]:
            return False, "high", "Dangerous package blocked: " + dep_name
        if dep_name.lower() not in [d.lower() for d in declared_deps]:
            return False, "medium", "Undeclared dependency: " + dep_name + " — add to requirements.txt"
        return True, "none", "ok"

    def validate_removed_dependency(self, dep_name: str, source_files: List[Path]) -> Tuple[bool, str, str]:
        for f in source_files:
            if f.suffix not in (".py", ".js", ".ts"):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                if dep_name in content:
                    return False, "high", "Removed dependency still referenced in: " + str(f)
            except Exception:
                pass
        return True, "none", "ok"

    def validate_no_conflicts(self, deps: List[Dict]) -> Tuple[bool, List[str]]:
        seen = {}
        conflicts = []
        for d in deps:
            name = d.get("name", "").lower()
            ver = d.get("version", "")
            if name in seen and seen[name] != ver:
                conflicts.append("Version conflict: " + name + " (" + seen[name] + " vs " + ver + ")")
            seen[name] = ver
        return len(conflicts) == 0, conflicts

    def validate_all(self, deps: List[Dict], source_files: List[Path]) -> Tuple[bool, List[str]]:
        errors = []
        ok, conflicts = self.validate_no_conflicts(deps)
        if not ok:
            errors.extend(conflicts)
        declared = [d.get("name", "") for d in deps]
        return len(errors) == 0, errors