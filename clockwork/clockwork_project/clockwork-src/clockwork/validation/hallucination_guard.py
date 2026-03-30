from __future__ import annotations

import re
from pathlib import Path

HALLUCINATION_PATTERNS = [
    r"(?i)as an AI",
    r"(?i)I cannot access",
    r"(?i)I don.t have access to",
    r"(?i)placeholder",
    r"(?i)TODO: implement",
    r"(?i)your_api_key",
    r"(?i)INSERT_[A-Z_]+_HERE",
    r"(?i)FIXME",
    r"(?i)example\\.com/api",
    r"pass\\s*#\\s*implement",
]

GHOST_FILE_INDICATORS = ["non_existent", "fake_module", "imaginary"]


class HallucinationGuard:
    def check_content(self, content: str, filepath: str = "") -> tuple[bool, list[str]]:
        issues: list[str] = []
        for pattern in HALLUCINATION_PATTERNS:
            if re.search(pattern, content):
                issues.append(f"Hallucination pattern in {filepath}: {pattern}")
        return len(issues) == 0, issues

    def check_file_references(self, proposed_changes: list[dict]) -> tuple[bool, list[str]]:
        issues: list[str] = []
        for change in proposed_changes:
            file_path = str(change.get("file", ""))
            if not file_path:
                continue
            for indicator in GHOST_FILE_INDICATORS:
                if indicator in file_path.lower():
                    issues.append(f"Ghost file reference: {file_path}")
            parent = Path(file_path).parent
            if file_path != "." and parent.as_posix() not in ("", ".") and not parent.exists():
                # Missing parent path is informational only; pipeline treats this as warning.
                continue
        return len(issues) == 0, issues

    def score(self, content: str, filepath: str = "") -> float:
        ok, issues = self.check_content(content, filepath)
        if ok:
            return 1.0
        return max(0.0, 1.0 - (len(issues) * 0.2))

