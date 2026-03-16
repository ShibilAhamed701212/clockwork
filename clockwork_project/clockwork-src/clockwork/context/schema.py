"""
Clockwork Context Schema
"""
from __future__ import annotations
from typing import Any

CONTEXT_VERSION = 1

CONTEXT_SCHEMA: dict[str, Any] = {
    "project": {
        "type": dict,
        "required": True,
        "fields": {
            "name": {"type": str, "required": True},
            "type": {"type": str, "required": False},
            "version": {"type": (str, float, int), "required": False},
        },
    },
    "repository": {
        "type": dict,
        "required": True,
        "fields": {
            "architecture": {"type": str, "required": False},
            "languages": {"type": dict, "required": False},
        },
    },
    "frameworks": {"type": list, "required": False},
    "current_state": {
        "type": dict,
        "required": True,
        "fields": {
            "summary": {"type": str, "required": False},
            "next_task": {"type": str, "required": False},
            "blockers": {"type": list, "required": False},
        },
    },
    "skills_required": {"type": list, "required": False},
    "clockwork_context_version": {"type": int, "required": False},
}

def validate_context_schema(data, schema, path=""):
    errors = []
    for key, rules in schema.items():
        full_key = f"{path}.{key}" if path else key
        value = data.get(key)
        if rules.get("required") and value is None:
            errors.append(f"Missing required field: '{full_key}'")
            continue
        if value is None:
            continue
        expected_type = rules.get("type")
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"Field '{full_key}' must be {expected_type}, got {type(value).__name__}.")
            continue
        if rules.get("fields") and isinstance(value, dict):
            errors.extend(validate_context_schema(value, rules["fields"], full_key))
    return errors
