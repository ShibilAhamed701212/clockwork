import time
import threading
from pathlib import Path
from typing import Callable, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_OK = True
except ImportError:
    WATCHDOG_OK = False

WATCH_EXTENSIONS: Set[str] = {".py",".js",".ts",".yaml",".yml",".json",".toml",".md",".txt"}
EXCLUDED_DIRS:    Set[str] = {"__pycache__",".git","node_modules",".venv","venv","dist","build"}

class _Handler:
    pass

if WATCHDOG_OK:
    class _Handler(FileSystemEventHandler):
        def __init__(self, on_event: Callable, extensions: Set[str], excluded: Set[str]):
            self.on_event  = on_event
            self.extensions = extensions
            self.excluded   = excluded

        def _skip(self, path: str) -> bool:
            p = Path(path)
            for part in p.parts:
                if part in self.excluded:
                    return True
            return p.suffix.lower() not in self.extensions

        def on_modified(self, event):
            if not event.is_directory and not self._skip(event.src_path):
                self.on_event({"type": "modified", "path": event.src_path, "ts": time.time()})

        def on_created(self, event):
            if not event.is_directory and not self._skip(event.src_path):
                self.on_event({"type": "created", "path": event.src_path, "ts": time.time()})

        def on_deleted(self, event):
            if not self._skip(event.src_path):
                self.on_event({"type": "deleted", "path": event.src_path, "ts": time.time()})

        def on_moved(self, event):
            self.on_event({"type": "moved", "path": event.dest_path,
                           "src": event.src_path, "ts": time.time()})


class FileWatcher:
    def __init__(self, root: str, on_event: Callable):
        self.root     = root
        self.on_event = on_event
        self.running  = False
        self._observer = None

    def start(self):
        if not WATCHDOG_OK:
            print("[Watcher] watchdog not installed — install with: pip install watchdog")
            return False
        handler = _Handler(self.on_event, WATCH_EXTENSIONS, EXCLUDED_DIRS)
        self._observer = Observer()
        self._observer.schedule(handler, self.root, recursive=True)
        self._observer.start()
        self.running = True
        print("[Watcher] Watching: " + self.root)
        return True

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
        self.running = False
        print("[Watcher] Stopped.")

    def is_running(self) -> bool:
        return self.running