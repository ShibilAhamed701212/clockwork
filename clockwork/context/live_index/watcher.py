from __future__ import annotations

from pathlib import Path
from typing import Callable

from clockwork.index.watcher import RepositoryWatcher
from clockwork.index.models import ChangeEvent


class FileWatcher:
    def __init__(self, root: str, on_event: Callable[[dict], None]) -> None:
        self.root = root
        self.on_event = on_event
        self._watcher = RepositoryWatcher(Path(root), self._handle)
        self.running = False

    def _handle(self, event: ChangeEvent) -> None:
        payload = {
            "type": event.event_type,
            "path": event.file_path,
            "src": event.src_path,
            "ts": event.timestamp,
        }
        self.on_event(payload)

    def start(self) -> bool:
        ok = self._watcher.start()
        self.running = True
        return ok

    def stop(self) -> None:
        self._watcher.stop()
        self.running = False

    def is_running(self) -> bool:
        return self.running

