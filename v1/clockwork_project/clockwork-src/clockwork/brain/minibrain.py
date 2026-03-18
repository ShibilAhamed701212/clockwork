"""
clockwork/brain/minibrain.py

MiniBrain — the default, fully-offline, deterministic reasoning engine.

Uses static analysis techniques:
  * repository diff classification
  * AST-based file inspection
  * dependency cross-checking against context
  * architecture rule matching

No external services or AI models are required.
"""

from __future__ import annotations

import ast
import re
from typing import Any

from .base import BrainInterface, BrainResult, BrainStatus, RiskLevel

_CORE_MODULE_PATTERNS: list[str] = [
    r"^clockwork/",
    r"__init__\.py$",
    r"pyproject\.toml$",
    r"setup\.py$",
]

_DEP_FILE_PATTERNS: list[str] = [
    "pyproject.toml",
    "requirements.txt",
    "requirements*.txt",
    "setup.cfg",
]

_FRONTEND_DIRS: list[str] = ["frontend", "ui", "web", "client", "static"]

_DB_IMPORT_SIGNATURES: list[str] = [
    "sqlalchemy", "sqlite3", "psycopg2", "pymysql", "motor", "pymongo",
]


class MiniBrain(BrainInterface):
    """Deterministic reasoning engine — no AI model required."""

    def analyze_change(
        self,
        context:   dict[str, Any],
        repo_diff: dict[str, Any],
        rules:     list[dict[str, Any]],
    ) -> BrainResult:
        violations: list[str] = []
        warnings:   list[str] = []

        added:         list[str]       = repo_diff.get("added", [])
        deleted:       list[str]       = repo_diff.get("deleted", [])
        modified:      list[str]       = repo_diff.get("modified", [])
        file_contents: dict[str, str]  = repo_diff.get("file_contents", {})

        violations.extend(self._detect_core_deletions(deleted))
        violations.extend(self._check_dependency_context(context, deleted, modified, file_contents))
        violations.extend(self._check_layer_violations(added + modified, file_contents))

        ctx_issues, ctx_warnings = self._check_context_consistency(context, added, deleted, modified)
        violations.extend(ctx_issues)
        warnings.extend(ctx_warnings)

        violations.extend(self._apply_rules(rules, added, deleted, modified, file_contents))
        warnings.extend(self._warn_new_modules(added))

        return self._build_result(violations, warnings)

    def _detect_core_deletions(self, deleted: list[str]) -> list[str]:
        issues: list[str] = []
        for path in deleted:
            for pattern in _CORE_MODULE_PATTERNS:
                if re.search(pattern, path):
                    issues.append(f"Core module deletion detected: {path}")
                    break
        return issues

    def _check_dependency_context(
        self,
        context:       dict[str, Any],
        deleted:       list[str],
        modified:      list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues:     list[str] = []
        frameworks: list[str] = context.get("frameworks", [])
        changed_dep_files = [
            p for p in deleted + modified
            if any(p.endswith(pat.lstrip("*")) for pat in _DEP_FILE_PATTERNS)
        ]
        for dep_file in changed_dep_files:
            content = file_contents.get(dep_file, "")
            if not content:
                continue
            for framework in frameworks:
                if framework.lower() not in content.lower():
                    issues.append(
                        f"Context declares framework '{framework}' but it is missing "
                        f"from modified dependency file '{dep_file}'."
                    )
        return issues

    def _check_layer_violations(
        self,
        changed_paths: list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues: list[str] = []
        for path in changed_paths:
            path_lower = path.lower()
            is_frontend = any(
                f"/{d}/" in path_lower or path_lower.startswith(d + "/")
                for d in _FRONTEND_DIRS
            )
            if not is_frontend or not path.endswith(".py"):
                continue
            content = file_contents.get(path, "")
            if not content:
                continue
            try:
                tree = ast.parse(content, filename=path)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = ""
                    if isinstance(node, ast.Import):
                        module = node.names[0].name if node.names else ""
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        module = node.module
                    for sig in _DB_IMPORT_SIGNATURES:
                        if sig in module.lower():
                            issues.append(
                                f"Architecture violation: frontend module '{path}' "
                                f"directly imports database library '{module}'."
                            )
        return issues

    def _check_context_consistency(
        self,
        context:  dict[str, Any],
        added:    list[str],
        deleted:  list[str],
        modified: list[str],
    ) -> tuple[list[str], list[str]]:
        issues:   list[str] = []
        warnings: list[str] = []
        modules: list[str] = context.get("modules", [])
        for module in modules:
            module_path = module.replace(".", "/")
            deleted_match = any(module_path in d for d in deleted)
            added_match   = any(module_path in a for a in added)
            if deleted_match and not added_match:
                issues.append(
                    f"Context references module '{module}' but it was deleted from the repository."
                )
        if "context.yaml" in modified or ".clockwork/context.yaml" in modified:
            warnings.append("context.yaml was modified. Verify context accuracy manually.")
        return issues, warnings

    def _apply_rules(
        self,
        rules:         list[dict[str, Any]],
        added:         list[str],
        deleted:       list[str],
        modified:      list[str],
        file_contents: dict[str, str],
    ) -> list[str]:
        issues:    list[str] = []
        all_paths: list[str] = added + deleted + modified
        for rule in rules:
            rule_id    = rule.get("id", "unknown")
            description = rule.get("description", "")
            pattern     = rule.get("pattern", "")
            applies_to  = rule.get("applies_to", "path")
            if not pattern:
                continue
            try:
                compiled = re.compile(pattern)
            except re.error:
                continue
            if applies_to == "path":
                for path in all_paths:
                    if compiled.search(path):
                        issues.append(f"Rule '{rule_id}' violated by path '{path}': {description}")
            elif applies_to == "content":
                for path in all_paths:
                    content = file_contents.get(path, "")
                    if content and compiled.search(content):
                        issues.append(f"Rule '{rule_id}' violated in '{path}': {description}")
        return issues

    def _warn_new_modules(self, added: list[str]) -> list[str]:
        warnings: list[str] = []
        for path in added:
            if path.endswith(".py") and "__init__" not in path:
                warnings.append(f"New module introduced: '{path}'. Verify it follows architecture guidelines.")
        return warnings

    def _build_result(self, violations: list[str], warnings: list[str]) -> BrainResult:
        if violations:
            high_keywords = ["core module deletion", "architecture violation", "context references module"]
            is_high = any(
                any(kw in v.lower() for kw in high_keywords)
                for v in violations
            )
            risk       = RiskLevel.HIGH if is_high else RiskLevel.MEDIUM
            confidence = 0.95 if is_high else 0.80
            return BrainResult(
                status=BrainStatus.REJECTED,
                confidence=confidence,
                risk_level=risk,
                explanation=f"{len(violations)} violation(s) detected. Review required.",
                violations=violations,
                warnings=warnings,
            )
        if warnings:
            return BrainResult(
                status=BrainStatus.WARNING,
                confidence=0.75,
                risk_level=RiskLevel.LOW,
                explanation=f"{len(warnings)} advisory warning(s). Change appears safe but review suggested.",
                warnings=warnings,
            )
        return BrainResult(
            status=BrainStatus.VALID,
            confidence=0.97,
            risk_level=RiskLevel.LOW,
            explanation="No violations detected. Change is consistent with architecture and context.",
        )
