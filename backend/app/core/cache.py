"""A tiny TTL cache for dashboard aggregates. Any data write clears it."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Thread-safe cache with a global time-to-live and explicit invalidation."""

    def __init__(self) -> None:
        self._store: dict[Any, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get_or_set(self, key: Any, ttl_seconds: int, factory: Callable[[], Any]) -> Any:
        """Return the cached value for `key`, computing it with `factory` when missing or stale."""
        if ttl_seconds <= 0:
            return factory()
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry and now - entry[0] < ttl_seconds:
                return entry[1]
        value = factory()
        with self._lock:
            self._store[key] = (now, value)
        return value

    def clear(self) -> None:
        """Drop everything; call after any change that affects aggregates."""
        with self._lock:
            self._store.clear()


dashboard_cache = TTLCache()
