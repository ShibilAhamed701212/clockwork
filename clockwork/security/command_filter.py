from __future__ import annotations

import re

FORBIDDEN_COMMANDS = [
    "rm -rf",
    "del /f /s",
    "format c:",
    "mkfs",
    "DROP TABLE",
    "DELETE FROM",
    "TRUNCATE TABLE",
    ":(){:|:&};:",
    "fork bomb",
    "wget http",
    "curl http",
    "nc -e",
    "netcat",
    "> /dev/sda",
    "dd if=/dev/zero",
]

FORBIDDEN_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.(call|run|Popen)\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"__import__\s*\(",
    r"open\s*\(.+['\"]w['\"]",
    r"shutil\.rmtree\s*\(",
    r"pathlib.*\.unlink\s*\(",
    r"os\.remove\s*\(",
    r"os\.unlink\s*\(",
]

ALERT_KEYWORDS = {
    "critical": ["rm -rf", "del /f", "format", "DROP TABLE", "fork bomb"],
    "warning": ["subprocess", "eval(", "exec(", "os.system"],
    "info": ["open(", "write", "delete"],
}


class SecurityAlert:
    def __init__(self, level: str, message: str, command: str = "") -> None:
        self.level = level
        self.message = message
        self.command = command

    def __str__(self) -> str:
        return "[" + self.level.upper() + "] " + self.message


class CommandFilter:
    def filter(self, command: str) -> tuple[bool, str, str]:
        lower = command.lower()
        for forbidden in FORBIDDEN_COMMANDS:
            if forbidden.lower() in lower:
                return False, "Forbidden command: " + forbidden, "critical"
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command):
                return False, "Forbidden pattern: " + pattern, "warning"
        return True, "", "info"

    def get_alert(self, command: str) -> SecurityAlert:
        ok, message, level = self.filter(command)
        if not ok:
            return SecurityAlert(level, message, command)
        for level, keywords in ALERT_KEYWORDS.items():
            if any(keyword.lower() in command.lower() for keyword in keywords):
                return SecurityAlert(level, "Suspicious content: " + command[:80], command)
        return SecurityAlert("info", "Command appears safe", command)

    def sanitize_path(self, path: str) -> tuple[bool, str]:
        if ".." in path:
            return False, "Path traversal detected"
        unsafe = ["/etc/", "/root/", "C:\\Windows\\", "C:\\System32\\"]
        for prefix in unsafe:
            if path.lower().startswith(prefix.lower()):
                return False, "System path blocked: " + prefix
        return True, ""

    def validate_args(self, args: list[str]) -> tuple[bool, list[str]]:
        issues: list[str] = []
        for arg in args:
            ok, message, _ = self.filter(arg)
            if not ok:
                issues.append(message)
            ok_path, path_message = self.sanitize_path(arg)
            if not ok_path:
                issues.append(path_message)
        return len(issues) == 0, issues

    def scan_content(self, content: str) -> list[SecurityAlert]:
        alerts: list[SecurityAlert] = []
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                alerts.append(SecurityAlert("warning", "Unsafe pattern: " + pattern))
        for forbidden in FORBIDDEN_COMMANDS:
            if forbidden.lower() in content.lower():
                alerts.append(SecurityAlert("critical", "Forbidden command in content: " + forbidden))
        return alerts

