import time
import uuid
import threading
from typing import Dict, List, Optional

class TaskItem:
    def __init__(self, name: str, action: Dict, priority: float = 0.5, deps: List[str] = []):
        self.id       = str(uuid.uuid4())[:8]
        self.name     = name
        self.action   = action
        self.priority = priority
        self.deps     = deps
        self.status   = "pending"
        self.created  = time.time()
        self.result   = None

    def to_dict(self) -> Dict:
        return {
            "id":       self.id,
            "name":     self.name,
            "action":   self.action,
            "priority": self.priority,
            "deps":     self.deps,
            "status":   self.status,
            "created":  self.created,
        }


class TaskQueue:
    def __init__(self):
        self._queue: List[TaskItem] = []
        self._lock  = threading.Lock()
        self._done: List[str] = []

    def push(self, task: TaskItem):
        with self._lock:
            self._queue.append(task)
            self._queue.sort(key=lambda t: t.priority, reverse=True)

    def pop(self) -> Optional[TaskItem]:
        with self._lock:
            ready = [
                t for t in self._queue
                if t.status == "pending" and all(d in self._done for d in t.deps)
            ]
            if not ready:
                return None
            task = ready[0]
            task.status = "running"
            return task

    def complete(self, task_id: str, result=None):
        with self._lock:
            for t in self._queue:
                if t.id == task_id:
                    t.status = "completed"
                    t.result = result
                    self._done.append(t.name)
                    return

    def fail(self, task_id: str, reason: str = ""):
        with self._lock:
            for t in self._queue:
                if t.id == task_id:
                    t.status = "failed"
                    t.result = {"error": reason}
                    return

    def pending(self) -> List[TaskItem]:
        return [t for t in self._queue if t.status == "pending"]

    def completed(self) -> List[TaskItem]:
        return [t for t in self._queue if t.status == "completed"]

    def failed(self) -> List[TaskItem]:
        return [t for t in self._queue if t.status == "failed"]

    def all(self) -> List[Dict]:
        return [t.to_dict() for t in self._queue]

    def size(self) -> int:
        return len(self._queue)

    def stats(self) -> Dict:
        return {
            "total":     self.size(),
            "pending":   len(self.pending()),
            "completed": len(self.completed()),
            "failed":    len(self.failed()),
        }