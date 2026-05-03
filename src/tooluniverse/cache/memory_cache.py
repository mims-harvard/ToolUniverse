"""
In-memory cache utilities for ToolUniverse.

Provides a lightweight, thread-safe LRU cache with optional singleflight
deduplication for expensive misses.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional, Tuple


class LRUCache:
    """Thread-safe LRU cache with basic telemetry."""

    def __init__(self, max_size: int = 128):
        self.max_size = max(1, int(max_size))
        self._data: "OrderedDict[str, Tuple[Any, float]]" = OrderedDict()
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._data:
                self.misses += 1
                return None

            value, timestamp = self._data.pop(key)
            self._data[key] = (value, timestamp)
            self.hits += 1
            return value

    def set(self, key: str, value: Any):
        with self._lock:
            if key in self._data:
                self._data.pop(key)
            self._data[key] = (value, time.time())
            self._evict_if_needed()

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)

    def clear(self):
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def _evict_if_needed(self):
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "max_size": self.max_size,
                "current_size": len(self._data),
                "hits": self.hits,
                "misses": self.misses,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)

    def items(self) -> Iterator[Tuple[str, Any]]:
        with self._lock:
            for key, (value, _) in list(self._data.items()):
                yield key, value


class SingleFlight:
    """Per-key lock manager to collapse duplicate cache misses."""

    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._refcounts: Dict[str, int] = {}
        self._global = threading.Lock()

    @contextmanager
    def acquire(self, key: str):
        with self._global:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
                self._refcounts[key] = 0
            self._refcounts[key] += 1

        lock.acquire()
        try:
            yield
        finally:
            lock.release()
            with self._global:
                self._refcounts[key] -= 1
                # Only remove if no one is waiting and lock is not held
                if self._refcounts[key] == 0:
                    self._locks.pop(key, None)
                    self._refcounts.pop(key, None)
