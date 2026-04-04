from __future__ import annotations

import threading
import time
import uuid


class TaskItem:
    def __init__(
        self,
        name: str,
        action: dict,
        priority: float = 0.5,
        deps: list[str] | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.action = action
        self.priority = priority
        self.deps = deps or []
        self.status = "pending"
        self.created = time.time()
        self.result = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "priority": self.priority,
            "deps": self.deps,
            "status": self.status,
            "created": self.created,
        }


class TaskQueue:
    def __init__(self) -> None:
        self._queue: list[TaskItem] = []
        self._lock = threading.Lock()
        self._done: list[str] = []

    def push(self, task: TaskItem) -> None:
        with self._lock:
            self._queue.append(task)
            self._queue.sort(key=lambda item: item.priority, reverse=True)

    def pop(self) -> TaskItem | None:
        with self._lock:
            ready = [
                item
                for item in self._queue
                if item.status == "pending" and all(dep in self._done for dep in item.deps)
            ]
            if not ready:
                return None
            task = ready[0]
            task.status = "running"
            return task

    def complete(self, task_id: str, result: object = None) -> None:
        with self._lock:
            for task in self._queue:
                if task.id == task_id:
                    task.status = "completed"
                    task.result = result
                    self._done.append(task.name)
                    return

    def fail(self, task_id: str, reason: str = "") -> None:
        with self._lock:
            for task in self._queue:
                if task.id == task_id:
                    task.status = "failed"
                    task.result = {"error": reason}
                    return

    def pending(self) -> list[TaskItem]:
        return [task for task in self._queue if task.status == "pending"]

    def completed(self) -> list[TaskItem]:
        return [task for task in self._queue if task.status == "completed"]

    def failed(self) -> list[TaskItem]:
        return [task for task in self._queue if task.status == "failed"]

    def all(self) -> list[dict]:
        return [task.to_dict() for task in self._queue]

    def size(self) -> int:
        return len(self._queue)

    def stats(self) -> dict:
        return {
            "total": self.size(),
            "pending": len(self.pending()),
            "completed": len(self.completed()),
            "failed": len(self.failed()),
        }

