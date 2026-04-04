from __future__ import annotations

import threading
import time
from pathlib import Path

SANDBOX_TIMEOUT = 30


class SandboxViolation(Exception):
    pass


class SandboxResult:
    def __init__(self, success: bool, output: object = None, error: str = "", violation: bool = False, duration_ms: float = 0) -> None:
        self.success = success
        self.output = output
        self.error = error
        self.violation = violation
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": str(self.output)[:500],
            "error": self.error,
            "violation": self.violation,
            "duration_ms": self.duration_ms,
        }


class Sandbox:
    def __init__(self, timeout: int = SANDBOX_TIMEOUT, dry_run: bool = False, repo_root: Path | None = None) -> None:
        self.timeout = timeout
        self.dry_run = dry_run
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.allowed_roots = [self.repo_root, self.repo_root / ".clockwork"]

    def execute(self, fn, *args, label: str = "", **kwargs) -> SandboxResult:
        if self.dry_run:
            return SandboxResult(True, "[DRY RUN] " + (label or str(getattr(fn, "__name__", "fn"))))
        result = {"success": False, "output": None, "error": "", "violation": False}
        start = time.time()

        def runner() -> None:
            try:
                result["output"] = fn(*args, **kwargs)
                result["success"] = True
            except SandboxViolation as exc:
                result["error"] = "VIOLATION: " + str(exc)
                result["violation"] = True
            except Exception as exc:
                result["error"] = str(exc)

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        elapsed = round((time.time() - start) * 1000, 1)
        if thread.is_alive():
            return SandboxResult(False, error="Timeout after " + str(self.timeout) + "s", duration_ms=elapsed)
        return SandboxResult(
            success=bool(result["success"]),
            output=result.get("output"),
            error=str(result.get("error", "")),
            violation=bool(result.get("violation", False)),
            duration_ms=elapsed,
        )

    def validate_path(self, path: str) -> tuple[bool, str]:
        if ".." in path:
            return False, "Path traversal blocked: " + path
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = (self.repo_root / resolved).resolve()
        for root in self.allowed_roots:
            if str(resolved).startswith(str(root.resolve())):
                return True, ""
        return False, "Path outside sandbox: " + path

    def validate_operation(self, operation: str, target: str) -> tuple[bool, str]:
        ok, message = self.validate_path(target)
        if not ok:
            return False, message
        restricted = {"delete", "overwrite", "execute"}
        protected_paths = {
            ".clockwork/context.yaml",
            ".clockwork/rules.yaml",
            "config/config.yaml",
            "rules/rules.md",
        }
        if operation in restricted:
            normalized = target.replace("\\", "/")
            for protected in protected_paths:
                if protected in normalized:
                    return False, "Protected path: " + protected
        return True, ""

    def is_safe_command(self, command: str) -> tuple[bool, str]:
        forbidden = ["rm -rf", "del /f /s /q", "format c:", "mkfs", "DROP TABLE", "DELETE FROM", ":(){:|:&};:", "wget http", "curl http", "> /dev/sda"]
        lower = command.lower()
        for value in forbidden:
            if value.lower() in lower:
                return False, "Forbidden command: " + value
        return True, ""

