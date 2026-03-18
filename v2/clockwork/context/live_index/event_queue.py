import threading
import time
from collections import deque
from typing import Dict, List, Optional

PRIORITY_FILES = {
    "high":   {"requirements.txt","pyproject.toml","package.json","go.mod","Cargo.toml"},
    "medium": {".py",".js",".ts",".go",".rs",".java"},
    "low":    {".yaml",".yml",".json",".md",".txt"},
}

class EventQueue:
    def __init__(self, maxsize: int = 2000):
        self._queue = deque(maxlen=maxsize)
        self._lock  = threading.Lock()
        self._seen: Dict[str, float] = {}
        self.total_received  = 0
        self.total_processed = 0
        self.total_skipped   = 0

    def push(self, event: Dict):
        with self._lock:
            self.total_received += 1
            path = event.get("path","")
            priority = self._priority(path)
            event["priority"] = priority
            self._queue.append(event)

    def pop(self) -> Optional[Dict]:
        with self._lock:
            if self._queue:
                self.total_processed += 1
                return self._queue.popleft()
            return None

    def drain(self) -> List[Dict]:
        with self._lock:
            items = list(self._queue)
            self._queue.clear()
            self.total_processed += len(items)
            return items

    def drain_deduped(self) -> List[Dict]:
        with self._lock:
            seen_paths: Dict[str, Dict] = {}
            for event in self._queue:
                path = event.get("path","")
                seen_paths[path] = event
            self._queue.clear()
            items = list(seen_paths.values())
            items.sort(key=lambda e: self._priority_score(e.get("priority","low")), reverse=True)
            self.total_processed += len(items)
            self.total_skipped   += (self.total_received - self.total_processed - self.total_skipped)
            return items

    def _priority(self, path: str) -> str:
        name = path.replace("\\","/").split("/")[-1]
        ext  = "." + name.split(".")[-1] if "." in name else ""
        if name in PRIORITY_FILES["high"]:
            return "high"
        if ext in PRIORITY_FILES["medium"]:
            return "medium"
        return "low"

    def _priority_score(self, p: str) -> int:
        return {"high": 3, "medium": 2, "low": 1}.get(p, 1)

    def size(self)     -> int:  return len(self._queue)
    def is_empty(self) -> bool: return len(self._queue) == 0

    def stats(self) -> Dict:
        return {
            "received":  self.total_received,
            "processed": self.total_processed,
            "skipped":   self.total_skipped,
            "pending":   self.size(),
        }