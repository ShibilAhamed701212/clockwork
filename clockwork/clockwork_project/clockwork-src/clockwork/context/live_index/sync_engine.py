from __future__ import annotations

import threading
import time

from clockwork.context.live_index.event_queue import EventQueue
from clockwork.context.live_index.incremental_processor import IncrementalProcessor
from clockwork.context.live_index.watcher import FileWatcher


class SyncEngine:
    def __init__(
        self,
        root: str,
        context_engine: object | None = None,
        graph_builder: object | None = None,
        rule_engine: object | None = None,
    ) -> None:
        self.root = root
        self.context = context_engine
        self.queue = EventQueue()
        self.processor = IncrementalProcessor(
            context_engine=context_engine,
            graph_builder=graph_builder,
            rule_engine=rule_engine,
        )
        self.watcher = FileWatcher(root, self.queue.push)
        self._thread: threading.Thread | None = None
        self.running = False
        self._metrics = {
            "cycles": 0,
            "events_processed": 0,
            "errors": 0,
            "started_at": 0.0,
        }

    def start(self) -> bool:
        ok = self.watcher.start()
        if not ok:
            return False
        self.running = True
        self._metrics["started_at"] = time.time()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="clockwork-sync",
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self.running = False
        self.watcher.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)

    def _loop(self) -> None:
        while self.running:
            if not self.queue.is_empty():
                events = self.queue.drain_deduped()
                if events:
                    count = self.processor.process_all(events)
                    self._metrics["events_processed"] += count
                    self._metrics["cycles"] += 1
            time.sleep(0.1)

    def force_sync(self) -> None:
        self.processor.rebuild_index(self.root)

    def stats(self) -> dict:
        uptime = 0
        if self._metrics["started_at"]:
            uptime = round(time.time() - self._metrics["started_at"], 1)
        return {
            "running": self.running,
            "root": self.root,
            "uptime_s": uptime,
            "cycles": self._metrics["cycles"],
            "events_processed": self._metrics["events_processed"],
            "queue_pending": self.queue.size(),
            "processor": self.processor.stats(),
            "queue_stats": self.queue.stats(),
        }

