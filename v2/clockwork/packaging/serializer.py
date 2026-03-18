import json
import yaml
import hashlib
import time
from pathlib import Path
from typing import Any, Dict

SECRET_PATTERNS = [
    "password", "api_key", "secret", "token",
    "credential", "private_key", "access_key",
    "auth_token", "client_secret",
]

class Serializer:
    def to_json(self, data: Any, indent: int = 2) -> str:
        return json.dumps(data, indent=indent, default=str)

    def from_json(self, text: str) -> Any:
        return json.loads(text)

    def to_yaml(self, data: Any) -> str:
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def from_yaml(self, text: str) -> Any:
        return yaml.safe_load(text) or {}

    def checksum(self, data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def verify_checksum(self, data: str, expected: str) -> bool:
        return self.checksum(data) == expected

    def filter_secrets(self, data: Dict) -> Dict:
        if not isinstance(data, dict):
            return data
        cleaned = {}
        for k, v in data.items():
            key_lower = k.lower()
            if any(p in key_lower for p in SECRET_PATTERNS):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = self.filter_secrets(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    self.filter_secrets(i) if isinstance(i, dict) else i
                    for i in v
                ]
            elif isinstance(v, str) and any(p in v.lower() for p in SECRET_PATTERNS[:4]):
                cleaned[k] = v
            else:
                cleaned[k] = v
        return cleaned

    def build_metadata(self, project_name: str = "", version: int = 1) -> Dict:
        return {
            "clockwork_version":  "2.0",
            "package_version":    version,
            "clockwork_required": ">=2.0",
            "generated_at":       time.time(),
            "project_name":       project_name,
            "format":             "clockwork-package",
        }