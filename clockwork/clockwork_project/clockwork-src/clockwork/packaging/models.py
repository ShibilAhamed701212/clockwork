"""
clockwork/packaging/models.py
------------------------------
Data models for the Clockwork Packaging Engine.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CLOCKWORK_VERSION = "0.2.0"
PACKAGE_SCHEMA_VERSION = 1

# Files that are ALWAYS excluded from packages for security reasons
SENSITIVE_EXCLUSIONS: set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "secret.json",
    "service_account.json",
    ".netrc",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
}

# Required source files from .clockwork/ that must be present to build a package
REQUIRED_SOURCE_FILES: list[str] = [
    "context.yaml",
    "repo_map.json",
]

# Optional source files included when present
OPTIONAL_SOURCE_FILES: list[str] = [
    "rules.md",
    "skills.json",
    "agent_history.json",
    "handoff/handoff.json",
    "validation_log.json",
    "config.yaml",
    "logs/activity_history.jsonl",
    "integrations/agent-context.md",
    "integrations/agent-rules.md",
    "integrations/agents.md",
    "integrations/copilot-instructions.md",
]


@dataclass
class PackageMetadata:
    """Describes a .clockwork package artifact."""

    clockwork_version: str = CLOCKWORK_VERSION
    package_version: int = PACKAGE_SCHEMA_VERSION
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    project_name: str = "unknown_project"
    clockwork_required: str = f">={CLOCKWORK_VERSION}"
    source_machine: Optional[str] = None
    file_manifest: list[str] = field(default_factory=list)
    checksum: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Serialisation helpers
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        """Return metadata as a plain dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialise to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "PackageMetadata":
        """Deserialise from a plain dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, raw: str) -> "PackageMetadata":
        """Deserialise from a JSON string."""
        return cls.from_dict(json.loads(raw))

    # ------------------------------------------------------------------ #
    # Compatibility check
    # ------------------------------------------------------------------ #

    def is_compatible(self) -> bool:
        """
        Check whether this package is compatible with the running Clockwork version.

        Currently enforces:
          - package_version must equal PACKAGE_SCHEMA_VERSION
          - clockwork_version must match (simple equality; extend for semver later)
        """
        return (
            self.package_version == PACKAGE_SCHEMA_VERSION
            and self.clockwork_version == CLOCKWORK_VERSION
        )
