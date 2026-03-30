from __future__ import annotations

from pathlib import Path


class RealityCheck:
    def __init__(self, repo_map: dict | None = None) -> None:
        self.repo_map = repo_map or {}

    def check_file_exists(self, file_path: str) -> bool:
        return Path(file_path).exists()

    def check_architecture_alignment(self, proposed_file: str, context: dict) -> tuple[bool, str]:
        architecture = context.get("repository", {}).get("architecture", "")
        if not architecture:
            return True, ""
        normalized = proposed_file.lower().replace("\\", "/")
        if architecture == "cli" and "frontend" in normalized:
            return False, f"CLI architecture should not have frontend files: {proposed_file}"
        return True, ""

    def check_proposed_changes(self, proposed: list[dict], context: dict) -> tuple[bool, list[str]]:
        issues: list[str] = []
        for change in proposed:
            file_path = str(change.get("file", ""))
            ok, message = self.check_architecture_alignment(file_path, context)
            if not ok:
                issues.append(message)
            if ".." in file_path or file_path.startswith("/"):
                issues.append(f"Unsafe file path: {file_path}")
        return len(issues) == 0, issues

    def full_check(self, output: dict, context: dict) -> tuple[bool, list[str]]:
        proposed = output.get("proposed_changes", [])
        return self.check_proposed_changes(proposed, context)

