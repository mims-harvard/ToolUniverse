"""Credential-aware provider rate limiting for shared ToolUniverse workers."""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import threading
import time
from collections import OrderedDict
from typing import Callable, Optional


class ProviderRateLimiter:
    """Reserve request slots independently for each provider credential.

    Raw credential values are never retained. Authenticated buckets use an HMAC generated with a
    process-local random secret; anonymous traffic uses one provider-wide bucket. The LRU bound
    prevents a multi-tenant service from growing state indefinitely.
    """

    def __init__(
        self,
        *,
        max_buckets: int = 4096,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        digest_secret: Optional[bytes] = None,
    ) -> None:
        if max_buckets < 1:
            raise ValueError("max_buckets must be positive")
        self.max_buckets = max_buckets
        self._clock = clock
        self._sleep = sleep
        self._digest_secret = digest_secret or secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._next_slots: OrderedDict[tuple[str, bytes], float] = OrderedDict()

    def _credential_digest(self, credential: str) -> bytes:
        if not credential:
            return b"anonymous"
        return hmac.new(
            self._digest_secret,
            credential.encode("utf-8"),
            hashlib.sha256,
        ).digest()

    def wait(
        self,
        provider: str,
        credential: str,
        requests_per_second: Optional[float],
    ) -> None:
        """Wait until the next slot for one provider/credential bucket is available.

        ``None`` or ``0`` disables local throttling, which is useful for providers whose
        anonymous quota is a shared, adaptive upstream pool.
        """

        if requests_per_second in (None, 0):
            return
        if (
            not isinstance(requests_per_second, (int, float))
            or isinstance(requests_per_second, bool)
            or not math.isfinite(float(requests_per_second))
            or requests_per_second < 0
        ):
            raise ValueError("requests_per_second must be a non-negative finite number")
        if not isinstance(provider, str) or not provider:
            raise ValueError("provider must be a non-empty string")

        interval = 1.0 / float(requests_per_second)
        bucket = (provider, self._credential_digest(credential))
        with self._lock:
            now = self._clock()
            next_slot = self._next_slots.pop(bucket, now)
            reserved_slot = max(now, next_slot)
            self._next_slots[bucket] = reserved_slot + interval
            while len(self._next_slots) > self.max_buckets:
                self._next_slots.popitem(last=False)
            delay = reserved_slot - now

        if delay > 0:
            self._sleep(delay)


_PROVIDER_RATE_LIMITER = ProviderRateLimiter()


def enforce_provider_rate_limit(
    provider: str,
    credential: str,
    requests_per_second: Optional[float],
) -> None:
    """Apply the process-wide limiter for a provider credential bucket."""

    _PROVIDER_RATE_LIMITER.wait(provider, credential, requests_per_second)
