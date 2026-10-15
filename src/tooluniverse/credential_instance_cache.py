"""Bounded request-credential tool instance reuse.

The cache key contains a process-local HMAC of the complete request credential mapping. Raw
credential values are never retained in cache metadata. Tool instances can still hold provider
clients or constructor-bound credentials, so entries are bounded and expire after an idle TTL.
"""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional


@dataclass
class _InstanceEntry:
    instance: Any
    last_used: float


class CredentialInstanceCache:
    """Thread-safe LRU cache partitioned by tool config and credential fingerprint."""

    def __init__(
        self,
        *,
        max_size: int = 256,
        idle_ttl_seconds: float = 900.0,
        clock: Callable[[], float] = time.monotonic,
        digest_secret: Optional[bytes] = None,
    ) -> None:
        if isinstance(max_size, bool) or not isinstance(max_size, int) or max_size < 0:
            raise ValueError("max_size must be a non-negative integer")
        if (
            isinstance(idle_ttl_seconds, bool)
            or not isinstance(idle_ttl_seconds, (int, float))
            or not math.isfinite(float(idle_ttl_seconds))
            or idle_ttl_seconds < 0
        ):
            raise ValueError("idle_ttl_seconds must be a non-negative finite number")

        self.max_size = max_size
        self.idle_ttl_seconds = float(idle_ttl_seconds)
        self._clock = clock
        self._digest_secret = digest_secret or secrets.token_bytes(32)
        self._lock = threading.RLock()
        self._entries: OrderedDict[tuple[str, str, bytes], _InstanceEntry] = (
            OrderedDict()
        )
        self._inflight: dict[tuple[str, str, bytes], threading.Event] = {}
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.expirations = 0

    @property
    def enabled(self) -> bool:
        """Return whether entries may be retained."""

        return self.max_size > 0 and self.idle_ttl_seconds > 0

    def _credential_digest(self, credentials: Mapping[str, str]) -> bytes:
        digest = hmac.new(self._digest_secret, digestmod=hashlib.sha256)
        for name, value in sorted(credentials.items()):
            name_bytes = name.encode("utf-8")
            value_bytes = value.encode("utf-8")
            digest.update(len(name_bytes).to_bytes(8, "big"))
            digest.update(name_bytes)
            digest.update(len(value_bytes).to_bytes(8, "big"))
            digest.update(value_bytes)
        return digest.digest()

    def _prune_expired_locked(self, now: float) -> None:
        if not self.enabled:
            return
        while self._entries:
            key, entry = next(iter(self._entries.items()))
            if now - entry.last_used < self.idle_ttl_seconds:
                break
            self._entries.pop(key)
            self.expirations += 1

    def get_or_create(
        self,
        *,
        tool_name: str,
        config_version: str,
        credentials: Mapping[str, str],
        factory: Callable[[], Any],
    ) -> Any:
        """Return an isolated cached instance, creating it once on a cache miss."""

        if not self.enabled:
            with self._lock:
                self.misses += 1
            return factory()

        key = (tool_name, config_version, self._credential_digest(credentials))
        while True:
            with self._lock:
                now = self._clock()
                self._prune_expired_locked(now)
                entry = self._entries.pop(key, None)
                if entry is not None:
                    entry.last_used = now
                    self._entries[key] = entry
                    self.hits += 1
                    return entry.instance

                inflight = self._inflight.get(key)
                if inflight is None:
                    inflight = threading.Event()
                    self._inflight[key] = inflight
                    self.misses += 1
                    break

            # Only identical cache misses wait for one initializer. Different tools and tenants
            # construct concurrently instead of being serialized by a process-wide cache lock.
            inflight.wait()

        try:
            instance = factory()
        except BaseException:
            with self._lock:
                self._inflight.pop(key).set()
            raise

        with self._lock:
            if instance is not None:
                self._entries[key] = _InstanceEntry(
                    instance=instance, last_used=self._clock()
                )
                while len(self._entries) > self.max_size:
                    self._entries.popitem(last=False)
                    self.evictions += 1
            self._inflight.pop(key).set()
        return instance

    def invalidate_tool(self, tool_name: str) -> None:
        """Remove every credential partition for one tool."""

        with self._lock:
            keys = [key for key in self._entries if key[0] == tool_name]
            for key in keys:
                self._entries.pop(key, None)

    def clear(self) -> None:
        """Remove all instances and reset telemetry."""

        with self._lock:
            self._entries.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
            self.expirations = 0

    def stats(self) -> dict[str, Any]:
        """Return non-secret cache telemetry."""

        with self._lock:
            self._prune_expired_locked(self._clock())
            return {
                "enabled": self.enabled,
                "max_size": self.max_size,
                "idle_ttl_seconds": self.idle_ttl_seconds,
                "current_size": len(self._entries),
                "hits": self.hits,
                "misses": self.misses,
                "evictions": self.evictions,
                "expirations": self.expirations,
            }
