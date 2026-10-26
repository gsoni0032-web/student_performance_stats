"""A small in-memory sliding-window rate limiter.

State lives in the process, so run a single Uvicorn worker (or put a limiter in front)
if you need the limit to be exact across several workers.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.core.errors import AppError


class RateLimiter:
    """Allow at most `limit` hits per `window_seconds` for each key."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        """Record a hit for `key`, raising a 429 `AppError` when the limit is exceeded."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - hits[0])))
                raise AppError(
                    429,
                    "rate_limited",
                    "Too many attempts. Please wait a moment and try again.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)

    def reset(self) -> None:
        """Forget all recorded hits (used by tests)."""
        with self._lock:
            self._hits.clear()
