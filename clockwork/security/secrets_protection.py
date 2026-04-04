from __future__ import annotations

import re
from pathlib import Path

SECRET_PATTERNS = [
    (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]", "password"),
    (r"(?i)(api_key|apikey|api-key)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "api_key"),
    (r"(?i)(secret|client_secret)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "secret"),
    (r"(?i)(token|auth_token|access_token|bearer)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "token"),
    (r"sk-[a-zA-Z0-9]{32,}", "openai_key"),
    (r"ghp_[a-zA-Z0-9]{36}", "github_token"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "private_key_pem"),
]

SCAN_EXTENSIONS = {".py", ".js", ".ts", ".yaml", ".yml", ".env", ".json", ".toml", ".ini", ".cfg", ".sh"}
SKIP_EXTENSIONS = {".png", ".jpg", ".gif", ".db", ".sqlite", ".bin", ".exe", ".whl", ".lock"}


class SecretsProtection:
    def scan_content(self, content: str, filepath: str = "") -> tuple[bool, list[dict]]:
        findings: list[dict] = []
        for pattern, secret_type in SECRET_PATTERNS:
            if re.search(pattern, content):
                findings.append({"type": secret_type, "file": filepath, "severity": "critical"})
        return len(findings) == 0, findings

    def scan_file(self, filepath: str) -> tuple[bool, list[dict]]:
        path = Path(filepath)
        if not path.exists() or not path.is_file():
            return True, []
        if path.suffix.lower() in SKIP_EXTENSIONS:
            return True, []
        if path.stat().st_size > 1_000_000:
            return True, []
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, filepath)
        except Exception:
            return True, []

    def scan_directory(self, root: str = ".") -> list[dict]:
        findings: list[dict] = []
        excluded = {"__pycache__", ".git", "node_modules", ".venv", "venv", "dist", "build"}
        for path in Path(root).rglob("*"):
            if any(part in excluded for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in SCAN_EXTENSIONS:
                ok, result = self.scan_file(str(path))
                if not ok:
                    findings.extend(result)
        return findings

    def redact(self, content: str) -> str:
        redacted = content
        for pattern, secret_type in SECRET_PATTERNS:
            redacted = re.sub(pattern, "[" + secret_type.upper() + "_REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted

    def redact_dict(self, data: dict) -> dict:
        cleaned: dict = {}
        secret_keys = {"password", "api_key", "secret", "token", "private_key", "access_key", "client_secret", "auth", "credential"}
        for key, value in data.items():
            if any(secret_key in key.lower() for secret_key in secret_keys):
                cleaned[key] = "[REDACTED]"
            elif isinstance(value, dict):
                cleaned[key] = self.redact_dict(value)
            elif isinstance(value, str) and len(value) > 8:
                ok, _ = self.scan_content(value)
                cleaned[key] = "[REDACTED]" if not ok else value
            else:
                cleaned[key] = value
        return cleaned

