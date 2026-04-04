from __future__ import annotations


class SafetyRules:
    def validate_code_content(self, content: str, file_path: str = "") -> tuple[bool, list[str]]:
        issues: list[str] = []
        lowered = content.lower()
        if "eval(" in lowered:
            issues.append("Unsafe call detected: eval()")
        if "exec(" in lowered:
            issues.append("Unsafe call detected: exec()")
        if "rm -rf" in lowered:
            issues.append("Dangerous command detected: rm -rf")
        if file_path.endswith(".env"):
            issues.append("Direct .env modifications are blocked")
        return len(issues) == 0, issues

