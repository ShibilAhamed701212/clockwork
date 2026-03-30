from __future__ import annotations


class DependencyRules:
    def validate(self, proposed_changes: list[dict]) -> tuple[bool, list[str]]:
        issues: list[str] = []
        for change in proposed_changes:
            file_path = str(change.get("file", ""))
            if "requirements" in file_path and "delete" in str(change.get("change", "")).lower():
                issues.append("Dependency manifest deletion is not allowed")
        return len(issues) == 0, issues

