import time
from typing import Any, Callable, Optional

class RetryEngine:
    def __init__(self, max_retries: int = 3, delay_s: float = 1.0,
                 backoff: float = 2.0, exceptions=(Exception,)):
        self.max_retries = max_retries
        self.delay_s     = delay_s
        self.backoff     = backoff
        self.exceptions  = exceptions

    def run(self, fn: Callable, *args, **kwargs) -> Any:
        delay   = self.delay_s
        last_ex = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = fn(*args, **kwargs)
                if attempt > 1:
                    print("[Retry] Succeeded on attempt " + str(attempt))
                return result
            except self.exceptions as e:
                last_ex = e
                print("[Retry] Attempt " + str(attempt) + "/" + str(self.max_retries) +
                      " failed: " + str(e))
                if attempt < self.max_retries:
                    time.sleep(delay)
                    delay *= self.backoff
        raise RuntimeError("All " + str(self.max_retries) + " attempts failed. Last: " + str(last_ex))

    def run_safe(self, fn: Callable, default: Any = None, *args, **kwargs) -> Any:
        try:
            return self.run(fn, *args, **kwargs)
        except Exception as e:
            print("[Retry] All retries exhausted: " + str(e))
            return default