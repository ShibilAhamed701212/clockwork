import re
from pathlib import Path
from typing import List, Tuple

FORBIDDEN_PATTERNS = [
    r"os\.system\(",
    r"subprocess\.call\(",
    r"subprocess\.Popen\(",
    r"eval\(",
    r"exec\(",
    r"__import__\(",
    r"open\(.+['\"]w['\"]\).+rm\b",
]

FORBIDDEN_COMMANDS = [
    "rm -rf", "del /f", "format c:",
    "DROP TABLE", "DELETE FROM",
    ":(){:|:&};:",
]

SECRET_PATTERNS = [
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"api_key\s*=\s*['\"][^'\"]+['\"]",
    r"secret\s*=\s*['\"][^'\"]+['\"]",
    r"token\s*=\s*['\"][^'\"]+['\"]",
]

class SafetyRules:
    def validate_code_content(self, content: str, filepath: str = "") -> Tuple[bool, List[str]]:
        violations = []
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                violations.append("Unsafe code pattern in " + filepath + ": " + pattern)
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append("Possible secret hardcoded in " + filepath)
        return len(violations) == 0, violations

    def validate_command(self, command: str) -> Tuple[bool, str]:
        cmd_lower = command.lower()
        for forbidden in FORBIDDEN_COMMANDS:
            if forbidden.lower() in cmd_lower:
                return False, "Forbidden command blocked: " + forbidden
        return True, "ok"

    def validate_file_operation(self, operation: str, target_path: str) -> Tuple[bool, str]:
        protected = [
            ".clockwork/context.yaml",
            ".clockwork/rules.md",
            "config/config.yaml",
        ]
        norm = target_path.replace("\\", "/")
        if operation in ("delete", "overwrite"):
            for p in protected:
                if p in norm:
                    return False, "Blocked " + operation + " on protected file: " + p
        return True, "ok"

    def scan_file(self, filepath: Path) -> Tuple[bool, List[str]]:
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            return self.validate_code_content(content, str(filepath))
        except Exception as e:
            return False, ["Cannot read file: " + str(e)]