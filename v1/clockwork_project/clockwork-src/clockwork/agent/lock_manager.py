"""
clockwork/agent/lock_manager.py
--------------------------------
File lock manager for the Agent Runtime (spec §9).

Prevents multiple agents from modifying the same file simultaneously.

Lock files are stored in:
    .clockwork/locks/<encoded_path>.lock

Each lock file contains JSON with the holding agent and timestamp.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Optional


class FileLockError(Exception):
    """Raised when a lock cannot be acquired."""


class LockManager:
    """
    Manages file locks inside .clockwork/locks/.

    Usage::

        lm = LockManager(clockwork_dir)
        lm.acquire("backend/auth.py", agent_name="claude_code")
        # ... do work ...
        lm.release("backend/auth.py", agent_name="claude_code")

    Or as a context manager::

        with lm.locked("backend/auth.py", "claude_code"):
            # exclusive access guaranteed
    """

    LOCK_TTL_SECONDS = 300   # stale locks older than 5 min are auto-released

    def __init__(self, clockwork_dir: Path) -> None:
        self.locks_dir = clockwork_dir / "locks"

    def _lock_path(self, file_path: str) -> Path:
        """Convert a repo-relative file path to its .lock file path."""
        safe_name = file_path.replace("/", "_").replace("\\", "_") + ".lock"
        return self.locks_dir / safe_name

    # ── acquire / release ──────────────────────────────────────────────────

    def acquire(self, file_path: str, agent_name: str) -> None:
        """
        Acquire a lock for *file_path*.

        Raises FileLockError if the file is already locked by another agent.
        Stale locks (older than LOCK_TTL_SECONDS) are silently cleared.
        """
        self.locks_dir.mkdir(parents=True, exist_ok=True)
        lp = self._lock_path(file_path)

        if lp.exists():
            try:
                existing = json.loads(lp.read_text(encoding="utf-8"))
                holder   = existing.get("agent", "unknown")
                acquired = existing.get("acquired_at", 0)

                # same agent re-acquiring is fine
                if holder == agent_name:
                    return

                # stale lock? clear it
                if time.time() - acquired > self.LOCK_TTL_SECONDS:
                    lp.unlink(missing_ok=True)
                else:
                    raise FileLockError(
                        f"File '{file_path}' is locked by agent '{holder}'. "
                        "Try again later."
                    )
            except (json.JSONDecodeError, OSError):
                lp.unlink(missing_ok=True)

        lp.write_text(
            json.dumps({
                "file_path":   file_path,
                "agent":       agent_name,
                "acquired_at": time.time(),
            }),
            encoding="utf-8",
        )

    def release(self, file_path: str, agent_name: str) -> bool:
        """
        Release the lock for *file_path*.

        Returns False if the lock doesn't exist or is held by another agent.
        """
        lp = self._lock_path(file_path)
        if not lp.exists():
            return False

        try:
            existing = json.loads(lp.read_text(encoding="utf-8"))
            if existing.get("agent") != agent_name:
                return False
        except Exception:
            pass

        lp.unlink(missing_ok=True)
        return True

    def release_all(self, agent_name: str) -> int:
        """Release all locks held by *agent_name*. Returns count released."""
        released = 0
        if not self.locks_dir.exists():
            return 0
        for lp in self.locks_dir.glob("*.lock"):
            try:
                d = json.loads(lp.read_text(encoding="utf-8"))
                if d.get("agent") == agent_name:
                    lp.unlink(missing_ok=True)
                    released += 1
            except Exception:
                pass
        return released

    def is_locked(self, file_path: str) -> bool:
        """Return True if *file_path* is currently locked."""
        lp = self._lock_path(file_path)
        if not lp.exists():
            return False
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
            acquired = d.get("acquired_at", 0)
            if time.time() - acquired > self.LOCK_TTL_SECONDS:
                lp.unlink(missing_ok=True)
                return False
            return True
        except Exception:
            return False

    def lock_holder(self, file_path: str) -> Optional[str]:
        """Return the name of the agent holding the lock, or None."""
        lp = self._lock_path(file_path)
        if not lp.exists():
            return None
        try:
            d = json.loads(lp.read_text(encoding="utf-8"))
            return d.get("agent")
        except Exception:
            return None

    def list_locks(self) -> list[dict]:
        """Return all active locks as a list of dicts."""
        if not self.locks_dir.exists():
            return []
        locks = []
        now = time.time()
        for lp in self.locks_dir.glob("*.lock"):
            try:
                d = json.loads(lp.read_text(encoding="utf-8"))
                if now - d.get("acquired_at", 0) <= self.LOCK_TTL_SECONDS:
                    locks.append(d)
                else:
                    lp.unlink(missing_ok=True)   # clean stale lock
            except Exception:
                pass
        return locks

    # ── context manager ────────────────────────────────────────────────────

    class _Lock:
        def __init__(self, manager: "LockManager", file_path: str, agent: str):
            self._m = manager
            self._fp = file_path
            self._agent = agent

        def __enter__(self) -> "_Lock":
            self._m.acquire(self._fp, self._agent)
            return self

        def __exit__(self, *_) -> None:
            self._m.release(self._fp, self._agent)

    def locked(self, file_path: str, agent_name: str) -> "_Lock":
        """Return a context manager that acquires and auto-releases the lock."""
        return self._Lock(self, file_path, agent_name)

