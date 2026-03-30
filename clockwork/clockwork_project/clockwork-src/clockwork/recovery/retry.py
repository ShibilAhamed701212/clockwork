from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class RetryEngine:
    def __init__(
        self,
        max_retries: int = 3,
        delay_s: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple[type[BaseException], ...] = (Exception,),
    ) -> None:
        self.max_retries = max_retries
        self.delay_s = delay_s
        self.backoff = backoff
        self.exceptions = exceptions

    def run(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        delay = self.delay_s
        last_exception: BaseException | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except self.exceptions as exc:
                last_exception = exc
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.backoff
        raise RuntimeError(
            f"All {self.max_retries} attempts failed. Last: {last_exception}"
        )

    def run_safe(self, fn: Callable[..., Any], default: Any = None, *args: Any, **kwargs: Any) -> Any:
        try:
            return self.run(fn, *args, **kwargs)
        except Exception:
            return default

