import json
from pathlib import Path
from typing import Dict, List, Tuple

class RealityCheck:
    def __init__(self, repo_map: Dict = {}):
        self.repo_map = repo_map

    def check_file_exists(self, file_path: str) -> bool:
        return Path(file_path).exists()

    def check_architecture_alignment(self, proposed_file: str, context: Dict) -> Tuple[bool, str]:
        arch = context.get("repository",{}).get("architecture","")
        if not arch:
            return True, ""
        lower = proposed_file.lower().replace("\\","/")
        if arch == "cli" and "frontend" in lower:
            return False, "CLI architecture should not have frontend files: " + proposed_file
        return True, ""

    def check_dependency_exists(self, dep_name: str, declared_deps: List[str]) -> Tuple[bool, str]:
        names_lower = [d.lower() for d in declared_deps]
        if dep_name.lower() not in names_lower:
            return False, "Dependency not declared: " + dep_name
        return True, ""

    def check_proposed_changes(self, proposed: List[Dict], context: Dict) -> Tuple[bool, List[str]]:
        issues = []
        for change in proposed:
            fpath  = change.get("file","")
            ok, msg = self.check_architecture_alignment(fpath, context)
            if not ok:
                issues.append(msg)
            if ".." in fpath or fpath.startswith("/"):
                issues.append("Unsafe file path: " + fpath)
        return len(issues) == 0, issues

    def full_check(self, output: Dict, context: Dict) -> Tuple[bool, List[str]]:
        issues = []
        proposed = output.get("proposed_changes",[])
        ok, errs = self.check_proposed_changes(proposed, context)
        if not ok:
            issues.extend(errs)
        return len(issues) == 0, issues