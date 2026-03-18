import time
from typing import Dict, List, Tuple

REQUIRED_KEYS = ["project", "repository", "context_state", "memory", "skills", "meta"]
REQUIRED_META = ["context_version", "clockwork_version", "created_at"]

class ContextValidator:
    def __init__(self, repo_map: Dict = {}):
        self.repo_map = repo_map

    def validate(self, context: Dict) -> Tuple[bool, List[str]]:
        errors = []
        errors += self._check_required_keys(context)
        errors += self._check_meta(context)
        errors += self._check_types(context)
        errors += self._check_integrity(context)
        ok = len(errors) == 0
        return ok, errors

    def _check_required_keys(self, ctx: Dict) -> List[str]:
        return ["Missing key: " + k for k in REQUIRED_KEYS if k not in ctx]

    def _check_meta(self, ctx: Dict) -> List[str]:
        meta = ctx.get("meta", {})
        return ["Missing meta field: " + k for k in REQUIRED_META if k not in meta]

    def _check_types(self, ctx: Dict) -> List[str]:
        errors = []
        repo = ctx.get("repository", {})
        if not isinstance(repo.get("languages", {}), dict):
            errors.append("repository.languages must be a dict")
        if not isinstance(repo.get("frameworks", []), list):
            errors.append("repository.frameworks must be a list")
        mem = ctx.get("memory", {})
        for field in ["past_actions", "decisions", "failures"]:
            if not isinstance(mem.get(field, []), list):
                errors.append("memory." + field + " must be a list")
        return errors

    def _check_integrity(self, ctx: Dict) -> List[str]:
        errors = []
        if not self.repo_map:
            return errors
        ctx_arch = ctx.get("repository", {}).get("architecture", "")
        map_arch = self.repo_map.get("architecture", {}).get("type", "")
        if ctx_arch and map_arch and ctx_arch != map_arch:
            errors.append(
                "Architecture drift: context=" + ctx_arch + " repo=" + map_arch
            )
        ctx_langs = set(ctx.get("repository", {}).get("languages", {}).keys())
        map_langs = set(self.repo_map.get("languages", {}).get("languages", {}).keys())
        drift = ctx_langs - map_langs
        if drift:
            errors.append("Language drift detected: " + str(drift))
        return errors

    def detect_drift(self, context: Dict, repo_map: Dict) -> List[str]:
        issues = []
        ctx_arch = context.get("repository", {}).get("architecture", "")
        map_arch = repo_map.get("architecture", {}).get("type", "")
        if ctx_arch and map_arch and ctx_arch != map_arch:
            issues.append("STRUCTURAL DRIFT: " + ctx_arch + " vs " + map_arch)
        ctx_deps = {d.get("name") for d in context.get("repository", {}).get("dependencies", [])}
        map_deps = {d.get("name") for d in repo_map.get("dependencies", {}).get("dependencies", [])}
        added = map_deps - ctx_deps
        removed = ctx_deps - map_deps
        if added:
            issues.append("DEPENDENCY DRIFT added: " + str(added))
        if removed:
            issues.append("DEPENDENCY DRIFT removed: " + str(removed))
        return issues