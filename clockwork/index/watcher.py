"""
clockwork/index/watcher.py
---------------------------
Filesystem watcher for the Live Context Index.

Uses the `watchdog` library (spec §4) to capture file events
and feeds them into a thread-safe queue with debouncing (spec §9).

Events captured:
  created / modified / deleted / renamed
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .models import ChangeEvent, EventType

logger = logging.getLogger("clockwork.index.watcher")

# Default debounce window in seconds (spec §9: 200 ms)
DEFAULT_DEBOUNCE_S = 0.2

# Directories always ignored
_IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "dist", "build", ".clockwork", ".idea", ".vscode",
}

# File extensions always ignored
_IGNORE_EXTENSIONS = {".pyc", ".pyo", ".pyd", ".swp", ".tmp", ".log"}


class ChangeEventHandler:
    """
    Watchdog event handler that filters and queues filesystem events.

    Designed to work with or without watchdog installed — if watchdog
    is missing, the watcher gracefully degrades to poll-based fallback.
    """

    def __init__(
        self,
        event_queue: "queue.Queue[ChangeEvent]",
        repo_root: str,
    ) -> None:
        self._queue     = event_queue
        self._repo_root = repo_root

    def _should_ignore(self, path: str) -> bool:
        parts = Path(path).parts
        for part in parts:
            if part in _IGNORE_DIRS:
                return True
        ext = Path(path).suffix.lower()
        if ext in _IGNORE_EXTENSIONS:
            return True
        return False

    def _enqueue(self, event_type: str, path: str, src_path: str = "") -> None:
        if self._should_ignore(path):
            return
        event = ChangeEvent(
            event_type=event_type,
            file_path=path,
            timestamp=time.time(),
            src_path=src_path,
        )
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("Event queue full — dropping event for %s", path)

    # watchdog callback interface
    def on_created(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.CREATED, getattr(event, "src_path", ""))

    def on_modified(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.MODIFIED, getattr(event, "src_path", ""))

    def on_deleted(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(EventType.DELETED, getattr(event, "src_path", ""))

    def on_moved(self, event: object) -> None:
        if not getattr(event, "is_directory", False):
            self._enqueue(
                EventType.RENAMED,
                getattr(event, "dest_path", ""),
                src_path=getattr(event, "src_path", ""),
            )


class DebouncedProcessor:
    """
    Reads from the event queue, deduplicates rapid-fire events for the
    same file (spec §9: 200 ms window), then calls the process callback.

    Runs in its own daemon thread.
    """

    def __init__(
        self,
        event_queue: "queue.Queue[ChangeEvent]",
        process_fn: Callable[[ChangeEvent], None],
        debounce_s: float = DEFAULT_DEBOUNCE_S,
    ) -> None:
        self._queue      = event_queue
        self._process_fn = process_fn
        self._debounce_s = debounce_s
        self._pending:   dict[str, ChangeEvent] = {}
        self._lock       = threading.Lock()
        self._stop_event = threading.Event()
        self._thread     = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            # drain available events into _pending (last-write-wins per path)
            try:
                while True:
                    event = self._queue.get_nowait()
                    with self._lock:
                        self._pending[event.file_path] = event
            except queue.Empty:
                pass

            # flush events whose debounce window has elapsed
            now = time.time()
            to_process: list[ChangeEvent] = []
            with self._lock:
                for path, ev in list(self._pending.items()):
                    if now - ev.timestamp >= self._debounce_s:
                        to_process.append(ev)
                        del self._pending[path]

            for ev in to_process:
                try:
                    self._process_fn(ev)
                except Exception as exc:
                    logger.error("Error processing event %s: %s", ev.file_path, exc)

            time.sleep(0.05)  # 50 ms poll interval


class RepositoryWatcher:
    """
    High-level watcher that combines watchdog + DebouncedProcessor.

    Usage::

        def on_change(event: ChangeEvent):
            print(event)

        watcher = RepositoryWatcher(repo_root=Path("."), on_change=on_change)
        watcher.start()
        # ... do work ...
        watcher.stop()
    """

    def __init__(
        self,
        repo_root: Path,
        on_change: Callable[[ChangeEvent], None],
        debounce_s: float = DEFAULT_DEBOUNCE_S,
        queue_maxsize: int = 1000,
    ) -> None:
        self.repo_root  = repo_root.resolve()
        self._on_change = on_change
        self._debounce_s = debounce_s
        self._event_queue: queue.Queue[ChangeEvent] = queue.Queue(maxsize=queue_maxsize)
        self._processor   = DebouncedProcessor(self._event_queue, on_change, debounce_s)
        self._observer: Optional[object] = None
        self._watchdog_available = False

    def start(self) -> bool:
        """
        Start watching.  Returns True if watchdog is available and
        real-time watching started, False if watchdog is not installed
        (caller should fall back to polling or manual index updates).
        """
        self._processor.start()

        try:
            from watchdog.observers import Observer  # type: ignore
            from watchdog.events import FileSystemEventHandler  # type: ignore

            handler = _WatchdogAdapter(
                ChangeEventHandler(self._event_queue, str(self.repo_root))
            )
            observer = Observer()
            observer.schedule(handler, str(self.repo_root), recursive=True)
            observer.start()
            self._observer = observer
            self._watchdog_available = True
            logger.info("Watchdog observer started on %s", self.repo_root)
            return True

        except ImportError:
            logger.warning(
                "watchdog not installed — real-time watching unavailable. "
                "Install it with: pip install watchdog"
            )
            return False

        except Exception as exc:
            # Windows compatibility: watchdog Observer may fail on some
            # Windows filesystem configurations.  Fall back to polling.
            logger.warning(
                "Watchdog observer failed (%s) — falling back to polling.", exc
            )
            self._start_polling_fallback()
            return True

    def _start_polling_fallback(self) -> None:
        """
        Start a lightweight poll-based watcher for Windows compatibility.
        Checks file mtimes every 2 seconds and injects events.
        """
        self._poll_thread = threading.Thread(
            target=self._poll_loop, daemon=True
        )
        self._poll_stop = threading.Event()
        self._poll_thread.start()
        self._watchdog_available = True
        logger.info("Poll-based watcher started on %s", self.repo_root)

    def _poll_loop(self) -> None:
        """Poll for file changes by comparing mtimes."""
        known: dict[str, float] = {}
        handler = ChangeEventHandler(self._event_queue, str(self.repo_root))

        # Initial snapshot
        for path in self.repo_root.rglob("*"):
            if path.is_file() and not handler._should_ignore(str(path)):
                try:
                    known[str(path)] = path.stat().st_mtime
                except OSError:
                    pass

        poll_stop = getattr(self, "_poll_stop", None)
        while poll_stop and not poll_stop.is_set():
            current: dict[str, float] = {}
            for path in self.repo_root.rglob("*"):
                if path.is_file() and not handler._should_ignore(str(path)):
                    try:
                        current[str(path)] = path.stat().st_mtime
                    except OSError:
                        pass

            # Detect changes
            for p, mtime in current.items():
                if p not in known:
                    handler._enqueue(EventType.CREATED, p)
                elif known[p] != mtime:
                    handler._enqueue(EventType.MODIFIED, p)

            for p in known:
                if p not in current:
                    handler._enqueue(EventType.DELETED, p)

            known = current
            poll_stop.wait(2.0)  # Poll every 2 seconds

    def stop(self) -> None:
        if self._observer:
            try:
                self._observer.stop()   # type: ignore
                self._observer.join()   # type: ignore
            except Exception:
                pass
        # Stop polling fallback if running
        poll_stop = getattr(self, "_poll_stop", None)
        if poll_stop:
            poll_stop.set()
        self._processor.stop()

    def is_watching(self) -> bool:
        return self._watchdog_available and (
            self._observer is not None or hasattr(self, "_poll_thread")
        )

    def inject_event(self, event: ChangeEvent) -> None:
        """Manually inject an event (useful for testing without watchdog)."""
        self._event_queue.put_nowait(event)


class _WatchdogAdapter:
    """
    Thin adapter that converts watchdog FileSystemEventHandler interface
    to our ChangeEventHandler interface.
    """

    def __init__(self, handler: ChangeEventHandler) -> None:
        self._h = handler

    def on_created(self, event: object)  -> None: self._h.on_created(event)
    def on_modified(self, event: object) -> None: self._h.on_modified(event)
    def on_deleted(self, event: object)  -> None: self._h.on_deleted(event)
    def on_moved(self, event: object)    -> None: self._h.on_moved(event)

    # watchdog requires these
    def on_any_event(self, event: object) -> None: pass
    dispatch = on_any_event

