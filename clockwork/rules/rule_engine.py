# -*- coding: utf-8 -*-
"""Rule Engine - real static analysis for all 3 rules."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any
import yaml
from clockwork.state import append_activity

PROTECTED_CORE_FILES = [
    "clockwork/cli/main.py",
    "clockwork/scanner/scanner.py",
    "clockwork/context/context_engine.py",
    "clockwork/rules/rule_engine.py",
    "clockwork/brain/mini_brain.py",
    "clockwork/handoff/handoff_engine.py",
    "clockwork/packaging/packaging_engine.py",
    "clockwork/graph/graph_engine.py",
]
SCHEMA_FILE_PATTERNS = [
    "schema.sql",
    "schema.py",
    "models.py",
    "models.sql",
    "create_tables",
    "db_schema",
    "database_schema",
]
MIGRATION_PATTERNS = [
    "migrations/",
    "migration/",
    "alembic/",
    "flyway/",
    "migrate_",
    "_migration",
    "001_",
    "002_",
    "003_",
]
DIRECT_DB_PATTERNS = [
    "sqlite3.connect",
    "psycopg2.connect",
    "pymysql.connect",
    "mysql.connector",
    "cx_Oracle",
    "pyodbc.connect",
]
API_LAYER_FILES = [
    "api.py",
    "routes.py",
    "views.py",
    "endpoints.py",
    "router.py",
    "controllers.py",
]


class RuleEngine:
    """Evaluates repository state against Clockwork rules."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path
        self.clockwork_dir = repo_path / ".clockwork"

    def _load_rules(self) -> list[dict[str, Any]]:
        p = self.clockwork_dir / "rules.yaml"
        if not p.exists():
            return []
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return data.get("rules", []) if data else []

    def _load_repo_map(self) -> dict[str, Any]:
        p = self.clockwork_dir / "repo_map.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

    def verify(self) -> tuple[bool, list[str]]:
        """Run all rules. Returns (passed, violations)."""
        rules = self._load_rules()
        repo_map = self._load_repo_map()
        violations: list[str] = []
        for rule in rules:
            v = self._evaluate_rule(rule, repo_map)
            if v:
                violations.append(v)
        passed = len(violations) == 0
        self._log_validation(passed, violations)
        self._log_rule(rules, passed, violations)
        self._log_agent_action("rule_engine.verify", passed, violations)
        return passed, violations

    def _evaluate_rule(
        self, rule: dict[str, Any], repo_map: dict[str, Any]
    ) -> str | None:
        """Real static analysis per rule."""
        rule_id = rule.get("id", "")
        file_paths = [f["path"] for f in repo_map.get("files", [])]
        if rule_id == "no_schema_change_without_migration":
            return self._check_schema_without_migration(file_paths)
        if rule_id == "no_bypass_api_layer":
            return self._check_api_layer_bypass(file_paths)
        if rule_id == "no_delete_core_modules":
            return self._check_core_modules_present(file_paths)
        return None

    def _check_schema_without_migration(self, file_paths: list[str]) -> str | None:
        has_schema = any(
            any(p in fp.lower() for p in SCHEMA_FILE_PATTERNS) for fp in file_paths
        )
        has_migration = any(
            any(p in fp.lower() for p in MIGRATION_PATTERNS) for fp in file_paths
        )
        if has_schema and not has_migration:
            schema_files = [
                fp
                for fp in file_paths
                if any(p in fp.lower() for p in SCHEMA_FILE_PATTERNS)
            ]
            return f"Rule [no_schema_change_without_migration]: Schema file(s) detected ({', '.join(schema_files[:3])}) but no migration files found."
        return None

    def _check_api_layer_bypass(self, file_paths: list[str]) -> str | None:
        has_api = any(
            any(a in fp.lower() for a in API_LAYER_FILES) for fp in file_paths
        )
        if not has_api:
            return None
        found: list[str] = []
        for fp in file_paths:
            if not fp.endswith(".py"):
                continue
            if any(a in fp.lower() for a in API_LAYER_FILES):
                continue
            full = self.repo_path / fp
            if not full.exists():
                continue
            try:
                content = full.read_text(encoding="utf-8", errors="ignore")
                for pat in DIRECT_DB_PATTERNS:
                    if pat in content:
                        found.append(f"{fp} uses {pat}")
                        break
            except OSError:
                continue
        if found:
            return f"Rule [no_bypass_api_layer]: Direct DB access outside API layer: {', '.join(found[:3])}"
        return None

    def _check_core_modules_present(self, file_paths: list[str]) -> str | None:
        is_cw = any("clockwork/cli" in p or "clockwork\\cli" in p for p in file_paths)
        if not is_cw:
            return None
        missing = [
            f
            for f in PROTECTED_CORE_FILES
            if not (self.repo_path / f).exists()
            and not (self.repo_path / f.replace("/", "\\")).exists()
        ]
        if missing:
            return f"Rule [no_delete_core_modules]: Core module(s) missing from disk: {', '.join(missing[:3])}"
        return None

    def _log_validation(self, passed: bool, violations: list[str]) -> None:
        p = self.clockwork_dir / "validation_log.json"
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "passed": passed,
                "violations": violations,
            }
        )
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")

    def _log_rule(
        self, rules: list[dict[str, Any]], passed: bool, violations: list[str]
    ) -> None:
        p = self.clockwork_dir / "logs" / "rule_log.json"
        p.parent.mkdir(exist_ok=True)
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rules_evaluated": len(rules),
                "passed": passed,
                "violations": violations,
            }
        )
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")

    def _log_agent_action(
        self, action: str, passed: bool, violations: list[str]
    ) -> None:
        p = self.clockwork_dir / "agent_history.json"
        try:
            ex = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
        except (json.JSONDecodeError, OSError):
            ex = []
        ex.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "rule_engine",
                "action": action,
                "result": "passed" if passed else "failed",
                "violations": violations,
            }
        )
        p.write_text(json.dumps(ex, indent=2), encoding="utf-8")

        append_activity(
            self.clockwork_dir,
            actor="rule_engine",
            action=action,
            status="success" if passed else "failed",
            details={"violations": violations},
        )
