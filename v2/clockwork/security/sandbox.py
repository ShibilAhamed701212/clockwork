import os
import sys
import time
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SANDBOX_TIMEOUT = 30
ALLOWED_ROOTS   = [Path(".").resolve(), Path(".clockwork").resolve()]

class SandboxViolation(Exception):
    pass

class SandboxResult:
    def __init__(self, success: bool, output: Any = None,
                 error: str = "", violation: bool = False, duration_ms: float = 0):
        self.success     = success
        self.output      = output
        self.error       = error
        self.violation   = violation
        self.duration_ms = duration_ms

    def to_dict(self) -> Dict:
        return {"success": self.success, "output": str(self.output)[:500],
                "error": self.error, "violation": self.violation,
                "duration_ms": self.duration_ms}


class Sandbox:
    def __init__(self, timeout: int = SANDBOX_TIMEOUT, dry_run: bool = False):
        self.timeout = timeout
        self.dry_run = dry_run
        self._violations: List[str] = []

    def execute(self, fn: Callable, *args, label: str = "", **kwargs) -> SandboxResult:
        if self.dry_run:
            return SandboxResult(True, "[DRY RUN] " + (label or str(fn.__name__)))
        result = {"success": False, "output": None, "error": ""}
        t0 = time.time()

        def runner():
            try:
                result["output"]  = fn(*args, **kwargs)
                result["success"] = True
            except SandboxViolation as e:
                result["error"]     = "VIOLATION: " + str(e)
                result["violation"] = True
            except Exception as e:
                result["error"] = str(e)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        elapsed = round((time.time() - t0) * 1000, 1)

        if thread.is_alive():
            return SandboxResult(False, error="Timeout after " + str(self.timeout) + "s",
                                 duration_ms=elapsed)
        return SandboxResult(
            success=result["success"],
            output=result.get("output"),
            error=result.get("error",""),
            violation=result.get("violation", False),
            duration_ms=elapsed,
        )

    def validate_path(self, path: str) -> Tuple[bool, str]:
        if ".." in path:
            return False, "Path traversal blocked: " + path
        p = Path(path).resolve()
        for root in ALLOWED_ROOTS:
            if str(p).startswith(str(root)):
                return True, ""
        return False, "Path outside sandbox: " + path

    def validate_operation(self, operation: str, target: str) -> Tuple[bool, str]:
        ok, msg = self.validate_path(target)
        if not ok:
            return False, msg
        restricted_ops  = {"delete", "overwrite", "execute"}
        protected_paths = {
            ".clockwork/context.yaml", ".clockwork/rules.yaml",
            "config/config.yaml", "rules/rules.md",
        }
        if operation in restricted_ops:
            norm = target.replace("\\", "/")
            for pp in protected_paths:
                if pp in norm:
                    return False, "Protected path: " + pp
        return True, ""

    def is_safe_command(self, command: str) -> Tuple[bool, str]:
        forbidden = [
            "rm -rf", "del /f /s /q", "format c:", "mkfs",
            "DROP TABLE", "DELETE FROM", ":(){:|:&};:",
            "wget http", "curl http", "> /dev/sda",
        ]
        lower = command.lower()
        for f in forbidden:
            if f.lower() in lower:
                return False, "Forbidden command: " + f
        return True, ""

    def get_violations(self) -> List[str]:
        return list(self._violations)