from __future__ import annotations

import ast
import json


class OutputValidator:
    def validate(self, output: dict) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if not isinstance(output, dict):
            return False, ["Output must be a dict"]

        if "success" not in output:
            errors.append("Missing 'success' field")

        proposed = output.get("proposed_changes", [])
        if not isinstance(proposed, list):
            errors.append("proposed_changes must be a list")
        else:
            for index, change in enumerate(proposed):
                errors.extend(self._validate_change(change, index))

        return len(errors) == 0, errors

    def _validate_change(self, change: dict, index: int) -> list[str]:
        prefix = f"Change[{index}] "
        if not isinstance(change, dict):
            return [prefix + "must be a dict"]

        errors: list[str] = []
        if "file" not in change:
            errors.append(prefix + "missing 'file'")
        if "change" not in change and "content" not in change:
            errors.append(prefix + "missing 'change' or 'content'")

        file_name = str(change.get("file", ""))
        if file_name and ".." in file_name:
            errors.append(prefix + f"path traversal detected in file: {file_name}")
        return errors

    def validate_syntax(self, code: str, language: str = "python") -> tuple[bool, str]:
        if language != "python":
            return True, ""
        try:
            ast.parse(code)
            return True, ""
        except SyntaxError as exc:
            return False, f"SyntaxError at line {exc.lineno}: {exc.msg}"

    def validate_json(self, text: str) -> tuple[bool, str]:
        try:
            json.loads(text)
            return True, ""
        except json.JSONDecodeError as exc:
            return False, f"JSONDecodeError: {exc}"

    def check_minimal_diff(self, original: str, proposed: str) -> bool:
        original_lines = set(original.splitlines())
        proposed_lines = set(proposed.splitlines())
        changed = len(original_lines.symmetric_difference(proposed_lines))
        total = max(len(original_lines), 1)
        return (changed / total) < 0.5

