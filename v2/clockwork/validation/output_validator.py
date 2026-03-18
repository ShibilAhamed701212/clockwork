import ast
import json
from pathlib import Path
from typing import Dict, List, Tuple

class OutputValidator:
    def validate(self, output: Dict) -> Tuple[bool, List[str]]:
        errors = []
        if not isinstance(output, dict):
            return False, ["Output must be a dict"]
        if "success" not in output:
            errors.append("Missing 'success' field")
        proposed = output.get("proposed_changes", [])
        if not isinstance(proposed, list):
            errors.append("proposed_changes must be a list")
        else:
            for i, change in enumerate(proposed):
                errs = self._validate_change(change, i)
                errors.extend(errs)
        return len(errors) == 0, errors

    def _validate_change(self, change: Dict, idx: int) -> List[str]:
        errors = []
        prefix = "Change[" + str(idx) + "] "
        if not isinstance(change, dict):
            return [prefix + "must be a dict"]
        if "file" not in change:
            errors.append(prefix + "missing 'file'")
        if "change" not in change and "content" not in change:
            errors.append(prefix + "missing 'change' or 'content'")
        fname = change.get("file","")
        if fname and ".." in fname:
            errors.append(prefix + "path traversal detected in file: " + fname)
        return errors

    def validate_syntax(self, code: str, language: str = "python") -> Tuple[bool, str]:
        if language == "python":
            try:
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, "SyntaxError at line " + str(e.lineno) + ": " + str(e.msg)
        return True, ""

    def validate_json(self, text: str) -> Tuple[bool, str]:
        try:
            json.loads(text)
            return True, ""
        except json.JSONDecodeError as e:
            return False, "JSONDecodeError: " + str(e)

    def check_minimal_diff(self, original: str, proposed: str) -> bool:
        orig_lines = set(original.splitlines())
        prop_lines = set(proposed.splitlines())
        changed    = len(orig_lines.symmetric_difference(prop_lines))
        total      = max(len(orig_lines), 1)
        return (changed / total) < 0.5