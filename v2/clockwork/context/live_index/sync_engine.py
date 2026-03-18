import time
import threading
from typing import Dict, List, Optional
from context.live_index.watcher             import FileWatcher
from context.live_index.event_queue         import EventQueue
from context.live_index.incremental_processor import IncrementalProcessor

class SyncEngine:
    def __init__(self, root: str, context_engine=None,
                 graph_builder=None, rule_engine=None):
        self.root       = root
        self.context    = context_engine
        self.queue      = EventQueue()
        self.processor  = IncrementalProcessor(
            context_engine=context_engine,
            graph_builder=graph_builder,
            rule_engine=rule_engine,
        )
        self.watcher    = FileWatcher(root, self.queue.push)
        self._thread:   Optional[threading.Thread] = None
        self.running    = False
        self._metrics:  Dict = {
            "cycles": 0, "events_processed": 0,
            "errors": 0, "started_at": 0.0,
        }

    def start(self) -> bool:
        ok = self.watcher.start()
        if not ok:
            print("[SyncEngine] Cannot start — watcher unavailable.")
            return False
        self.running = True
        self._metrics["started_at"] = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="clockwork-sync")
        self._thread.start()
        print("[SyncEngine] Live sync started: " + self.root)
        return True

    def stop(self):
        self.running = False
        self.watcher.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        print("[SyncEngine] Stopped. Cycles: " + str(self._metrics["cycles"]) +
              " | Events: " + str(self._metrics["events_processed"]))

    def _loop(self):
        while self.running:
            if not self.queue.is_empty():
                events = self.queue.drain_deduped()
                if events:
                    count = self.processor.process_all(events)
                    self._metrics["events_processed"] += count
                    self._metrics["cycles"] += 1
                    if count and self.context:
                        self._notify_context(events)
            time.sleep(0.1)

    def _notify_context(self, events: List[Dict]):
        try:
            types  = list({e.get("type","") for e in events})
            paths  = [e.get("path","") for e in events[:5]]
            self.context.record_event("live_index_update", {
                "event_types": types,
                "files":       paths,
                "count":       len(events),
            })
        except Exception:
            pass

    def force_sync(self):
        print("[SyncEngine] Force sync triggered...")
        self.processor.rebuild_index(self.root)
        if self.context:
            self.context.record_event("force_sync", {"root": self.root})

    def stats(self) -> Dict:
        uptime = round(time.time() - self._metrics["started_at"], 1) if self._metrics["started_at"] else 0
        return {
            "running":          self.running,
            "root":             self.root,
            "uptime_s":         uptime,
            "cycles":           self._metrics["cycles"],
            "events_processed": self._metrics["events_processed"],
            "queue_pending":    self.queue.size(),
            "processor":        self.processor.stats(),
            "queue_stats":      self.queue.stats(),
        }