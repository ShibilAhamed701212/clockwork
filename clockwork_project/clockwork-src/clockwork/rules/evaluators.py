from __future__ import annotations
import fnmatch
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from clockwork.rules.models import RuleCategory, RuleConfig, RuleSeverity, RuleViolation

logger = logging.getLogger(__name__)


class BaseEvaluator(ABC):
    category: RuleCategory

    def __init__(self, config: RuleConfig, repo_root: Path) -> None:
        self._config = config
        self._repo_root = repo_root

    @abstractmethod
    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]: ...

    def _violation(self, rule_id: str, message: str, file_path: str | None = None, severity: RuleSeverity = RuleSeverity.BLOCK) -> RuleViolation:
        return RuleViolation(rule_id=rule_id, category=self.category, severity=severity, message=message, file_path=file_path)

    @staticmethod
    def _matches_any(path: str, patterns: list[str]) -> bool:
        for p in patterns:
            if fnmatch.fnmatch(path, p) or fnmatch.fnmatch(Path(path).name, p):
                return True
        return False

    @staticmethod
    def _under_prefix(path: str, prefixes: list[str]) -> bool:
        return any(path.replace("\\", "/").startswith(p) for p in prefixes)


class SafetyEvaluator(BaseEvaluator):
    category = RuleCategory.SAFETY

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        violations = []
        for path in changed_files:
            if path in self._config.protected_files:
                violations.append(self._violation("protected_file_modification", f"Protected file modification attempted: {path}", path))
                continue
            for d in self._config.protected_directories:
                if path.startswith(d):
                    violations.append(self._violation("protected_directory_modification", f"Protected directory modified: {path}", path))
            if self._matches_any(path, self._config.forbid_file_patterns):
                violations.append(self._violation("forbidden_file_pattern", f"Forbidden file pattern: {path}", path))
        if self._config.forbid_core_file_deletion:
            for path in deleted_files:
                if path in self._config.protected_files:
                    violations.append(self._violation("core_file_deletion", f"Deletion of protected file attempted: {path}", path))
        return violations


class ArchitectureEvaluator(BaseEvaluator):
    category = RuleCategory.ARCHITECTURE
    _FORBIDDEN_PAIRS = [("frontend/", "database/"), ("frontend/", "models/"), ("ui/", "database/")]

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        if not self._config.enforce_architecture_layers:
            return []
        violations = []
        for path in changed_files:
            full = self._repo_root / path
            if not full.exists() or full.suffix not in {".py", ".js", ".ts"}:
                continue
            try:
                source = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for src_prefix, tgt_prefix in self._FORBIDDEN_PAIRS:
                if not path.startswith(src_prefix):
                    continue
                tgt_module = tgt_prefix.rstrip("/").replace("/", ".")
                if tgt_module in source:
                    violations.append(self._violation("architecture_layer_violation", f"Layer violation in {path}: '{src_prefix}' must not import from '{tgt_prefix}'", path))
        return violations


class DevelopmentEvaluator(BaseEvaluator):
    category = RuleCategory.DEVELOPMENT

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        if not self._config.require_tests_for_new_modules:
            return []
        violations = []
        for path in changed_files:
            if not path.endswith(".py"):
                continue
            if not self._under_prefix(path, self._config.require_tests_for):
                continue
            if Path(path).name.startswith("__") or "test" in path.lower():
                continue
            expected = f"tests/test_{Path(path).stem}.py"
            if not (self._repo_root / expected).exists() and expected not in changed_files:
                violations.append(self._violation("missing_test_file", f"New module without test:\n  Module  : {path}\n  Expected: {expected}", path, RuleSeverity.WARN))
        return violations


class ContextEvaluator(BaseEvaluator):
    category = RuleCategory.CONTEXT
    _MANAGED = frozenset({".clockwork/context.yaml", ".clockwork/repo_map.json", ".clockwork/agent_history.json", ".clockwork/validation_log.json", ".clockwork/rule_log.json"})

    def evaluate(self, changed_files: list[str], deleted_files: list[str]) -> list[RuleViolation]:
        violations = []
        for path in changed_files + deleted_files:
            if path in self._MANAGED:
                violations.append(self._violation("clockwork_memory_tampered", f"Clockwork-managed file modified outside Clockwork: {path}", path, RuleSeverity.WARN))
        return violations
