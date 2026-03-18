import re
from pathlib import Path
from typing import Dict, List, Tuple

SECRET_PATTERNS = [
    (r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{4,}['\"]",          "password"),
    (r"(?i)(api_key|apikey|api-key)\s*[=:]\s*['\"][^'\"]{8,}['\"]",       "api_key"),
    (r"(?i)(secret|client_secret)\s*[=:]\s*['\"][^'\"]{8,}['\"]",         "secret"),
    (r"(?i)(token|auth_token|access_token|bearer)\s*[=:]\s*['\"][^'\"]{8,}['\"]", "token"),
    (r"(?i)(private_key|ssh_key)\s*[=:]\s*['\"][^'\"]{10,}['\"]",         "private_key"),
    (r"(?i)(database_url|db_url|db_password)\s*[=:]\s*['\"][^'\"]{6,}['\"]", "db_credential"),
    (r"sk-[a-zA-Z0-9]{32,}",                                                "openai_key"),
    (r"ghp_[a-zA-Z0-9]{36}",                                                "github_token"),
    (r"ghs_[a-zA-Z0-9]{36}",                                                "github_secret"),
    (r"(?i)aws_access_key_id\s*[=:]\s*[A-Z0-9]{16,}",                      "aws_access_key"),
    (r"(?i)aws_secret_access_key\s*[=:]\s*[a-zA-Z0-9/+=]{32,}",           "aws_secret"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",                    "private_key_pem"),
]

SCAN_EXTENSIONS = {".py",".js",".ts",".yaml",".yml",".env",".json",".toml",".ini",".cfg",".sh"}
SKIP_EXTENSIONS = {".png",".jpg",".gif",".db",".sqlite",".bin",".exe",".whl",".lock"}

class SecretsProtection:
    def scan_content(self, content: str, filepath: str = "") -> Tuple[bool, List[Dict]]:
        findings = []
        for pattern, secret_type in SECRET_PATTERNS:
            if re.search(pattern, content):
                findings.append({"type": secret_type, "file": filepath, "severity": "critical"})
        return len(findings) == 0, findings

    def scan_file(self, filepath: str) -> Tuple[bool, List[Dict]]:
        p = Path(filepath)
        if not p.exists() or not p.is_file():
            return True, []
        if p.suffix.lower() in SKIP_EXTENSIONS:
            return True, []
        if p.stat().st_size > 1_000_000:
            return True, []
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            return self.scan_content(content, filepath)
        except Exception:
            return True, []

    def scan_directory(self, root: str = ".") -> List[Dict]:
        all_findings = []
        excluded = {"__pycache__",".git","node_modules",".venv","venv","dist","build"}
        for p in Path(root).rglob("*"):
            if any(part in excluded for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() in SCAN_EXTENSIONS:
                ok, findings = self.scan_file(str(p))
                if not ok:
                    all_findings.extend(findings)
        return all_findings

    def redact(self, content: str) -> str:
        redacted = content
        for pattern, secret_type in SECRET_PATTERNS:
            redacted = re.sub(pattern, "[" + secret_type.upper() + "_REDACTED]", redacted,
                              flags=re.IGNORECASE)
        return redacted

    def redact_dict(self, data: Dict) -> Dict:
        if not isinstance(data, dict):
            return data
        cleaned = {}
        secret_keys = {"password","api_key","secret","token","private_key",
                       "access_key","client_secret","auth","credential"}
        for k, v in data.items():
            if any(sk in k.lower() for sk in secret_keys):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = self.redact_dict(v)
            elif isinstance(v, str) and len(v) > 8:
                ok, _ = self.scan_content(v)
                cleaned[k] = "[REDACTED]" if not ok else v
            else:
                cleaned[k] = v
        return cleaned