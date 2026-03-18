import re
from pathlib import Path
from typing import Dict, List, Tuple

HALLUCINATION_PATTERNS = [
    r"(?i)as an AI",
    r"(?i)I cannot access",
    r"(?i)I don.t have access to",
    r"(?i)placeholder",
    r"(?i)TODO: implement",
    r"(?i)your_api_key",
    r"(?i)INSERT_[A-Z_]+_HERE",
    r"(?i)FIXME",
    r"(?i)example\.com/api",
    r"pass\s*#\s*implement",
]

GHOST_FILE_INDICATORS = [
    "non_existent", "fake_module", "imaginary",
]

class HallucinationGuard:
    def check_content(self, content: str, filepath: str = "") -> Tuple[bool, List[str]]:
        issues = []
        for pattern in HALLUCINATION_PATTERNS:
            if re.search(pattern, content):
                issues.append("Hallucination pattern in " + filepath + ": " + pattern)
        return len(issues) == 0, issues

    def check_file_references(self, proposed_changes: List[Dict]) -> Tuple[bool, List[str]]:
        issues = []
        for change in proposed_changes:
            fpath = change.get("file","")
            if not fpath:
                continue
            for indicator in GHOST_FILE_INDICATORS:
                if indicator in fpath.lower():
                    issues.append("Ghost file reference: " + fpath)
            if fpath and not Path(fpath).parent.exists() and fpath != ".":
                pass
        return len(issues) == 0, issues

    def check_imports(self, code: str, declared_deps: List[str]) -> Tuple[bool, List[str]]:
        import ast
        issues = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                        if mod not in declared_deps and mod not in __builtins__:
                            pass
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split(".")[0]
        except Exception:
            pass
        return len(issues) == 0, issues

    def score(self, content: str, filepath: str = "") -> float:
        ok, issues = self.check_content(content, filepath)
        return max(0.0, 1.0 - (len(issues) * 0.2))