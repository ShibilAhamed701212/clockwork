import re
from typing import Dict, List, Tuple

FORBIDDEN_COMMANDS = [
    "rm -rf", "del /f /s", "format c:", "mkfs",
    "DROP TABLE", "DELETE FROM", "TRUNCATE TABLE",
    ":(){:|:&};:", "fork bomb",
    "wget http", "curl http", "nc -e", "netcat",
    "> /dev/sda", "dd if=/dev/zero",
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
    "critical": ["rm -rf","del /f","format","DROP TABLE","fork bomb"],
    "warning":  ["subprocess","eval(","exec(","os.system"],
    "info":     ["open(","write","delete"],
}

class SecurityAlert:
    def __init__(self, level: str, message: str, command: str = ""):
        self.level   = level
        self.message = message
        self.command = command

    def __str__(self):
        return "[" + self.level.upper() + "] " + self.message

class CommandFilter:
    def filter(self, command: str) -> Tuple[bool, str, str]:
        lower = command.lower()
        for forbidden in FORBIDDEN_COMMANDS:
            if forbidden.lower() in lower:
                return False, "Forbidden command: " + forbidden, "critical"
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, command):
                return False, "Forbidden pattern: " + pattern, "warning"
        return True, "", "info"

    def get_alert(self, command: str) -> SecurityAlert:
        ok, msg, level = self.filter(command)
        if not ok:
            return SecurityAlert(level, msg, command)
        for level, keywords in ALERT_KEYWORDS.items():
            if any(kw.lower() in command.lower() for kw in keywords):
                return SecurityAlert(level, "Suspicious content: " + command[:80], command)
        return SecurityAlert("info", "Command appears safe", command)

    def sanitize_path(self, path: str) -> Tuple[bool, str]:
        if ".." in path:
            return False, "Path traversal detected"
        unsafe = ["/etc/", "/root/", "C:\\Windows\\", "C:\\System32\\"]
        for u in unsafe:
            if path.lower().startswith(u.lower()):
                return False, "System path blocked: " + u
        return True, ""

    def validate_args(self, args: List[str]) -> Tuple[bool, List[str]]:
        issues = []
        for arg in args:
            ok, msg, _ = self.filter(arg)
            if not ok:
                issues.append(msg)
            ok2, msg2 = self.sanitize_path(arg)
            if not ok2:
                issues.append(msg2)
        return len(issues) == 0, issues

    def scan_content(self, content: str) -> List[SecurityAlert]:
        alerts = []
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, content):
                alerts.append(SecurityAlert("warning", "Unsafe pattern: " + pattern))
        for forbidden in FORBIDDEN_COMMANDS:
            if forbidden.lower() in content.lower():
                alerts.append(SecurityAlert("critical", "Forbidden command in content: " + forbidden))
        return alerts