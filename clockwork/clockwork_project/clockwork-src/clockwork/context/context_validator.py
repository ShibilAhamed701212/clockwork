from __future__ import annotations

REQUIRED_KEYS = ["project", "repository", "context_state", "memory", "skills", "meta"]
REQUIRED_META = ["context_version", "clockwork_version", "created_at"]


class ContextValidator:
    def __init__(self, repo_map: dict | None = None) -> None:
        self.repo_map = repo_map or {}

    def validate(self, context: dict) -> tuple[bool, list[str]]:
        errors: list[str] = []
        errors += self._check_required_keys(context)
        errors += self._check_meta(context)
        errors += self._check_types(context)
        errors += self._check_integrity(context)
        return len(errors) == 0, errors

    def _check_required_keys(self, context: dict) -> list[str]:
        return [f"Missing key: {key}" for key in REQUIRED_KEYS if key not in context]

    def _check_meta(self, context: dict) -> list[str]:
        meta = context.get("meta", {})
        return [f"Missing meta field: {key}" for key in REQUIRED_META if key not in meta]

    def _check_types(self, context: dict) -> list[str]:
        errors: list[str] = []
        repository = context.get("repository", {})
        if not isinstance(repository.get("languages", {}), dict):
            errors.append("repository.languages must be a dict")
        if not isinstance(repository.get("frameworks", []), list):
            errors.append("repository.frameworks must be a list")
        memory = context.get("memory", {})
        for field in ["past_actions", "decisions", "failures"]:
            if not isinstance(memory.get(field, []), list):
                errors.append(f"memory.{field} must be a list")
        return errors

    def _check_integrity(self, context: dict) -> list[str]:
        if not self.repo_map:
            return []
        errors: list[str] = []
        context_arch = context.get("repository", {}).get("architecture", "")
        repo_arch = self.repo_map.get("architecture", {}).get("type", "")
        if context_arch and repo_arch and context_arch != repo_arch:
            errors.append(f"Architecture drift: context={context_arch} repo={repo_arch}")
        return errors

    def detect_drift(self, context: dict, repo_map: dict) -> list[str]:
        issues: list[str] = []
        context_arch = context.get("repository", {}).get("architecture", "")
        repo_arch = repo_map.get("architecture", {}).get("type", "")
        if context_arch and repo_arch and context_arch != repo_arch:
            issues.append(f"STRUCTURAL DRIFT: {context_arch} vs {repo_arch}")
        return issues

