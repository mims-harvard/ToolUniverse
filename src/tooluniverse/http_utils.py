"""
Shared HTTP utilities for ToolUniverse tools.

Goal: provide a small, dependency-light helper for retrying transient HTTP failures
without changing individual tool return formats.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence, Union
import time
import random
import re

import requests


RetryStatuses = Sequence[int]


# Query-string credentials are frequently included in ``requests.Response.url``
# and in RequestException messages.  Returning those values from a tool turns an
# otherwise harmless diagnostics field into a secret disclosure.  Match exact
# credential parameter names only: ordinary parameters such as ``keyword`` must
# remain untouched.
_SENSITIVE_QUERY_VALUE_RE = re.compile(
    r"(?i)([?&](?:"
    r"api[_-]?key|apikey|key|accesskey|x[_-]?api[_-]?key|"
    r"token|api[_-]?token|access[_-]?token|refresh[_-]?token|"
    r"client[_-]?secret|password"
    r")=)[^&#\s\"']*"
)


def redact_url_secrets(value: Any) -> Any:
    """Redact credential-bearing query values in a URL or error message.

    The helper accepts arbitrary text because ``requests`` exceptions often
    embed a full URL inside a longer sentence.  Non-string values are returned
    unchanged so callers can safely use it around optional response fields.
    """
    if not isinstance(value, str):
        return value
    return _SENSITIVE_QUERY_VALUE_RE.sub(r"\1[REDACTED]", value)


def _jittered_sleep(backoff_seconds: float, attempt: int) -> None:
    """Sleep with exponential backoff and a small random jitter."""
    sleep_s = backoff_seconds * (2**attempt)
    sleep_s += random.uniform(0.0, backoff_seconds * 0.25)
    time.sleep(sleep_s)


def request_with_retry(
    session: Union[requests.Session, Any],
    method: str,
    url: str,
    *,
    params: Optional[Mapping[str, Any]] = None,
    headers: Optional[Mapping[str, str]] = None,
    json: Any = None,
    data: Any = None,
    timeout: Optional[float] = None,
    retry_statuses: RetryStatuses = (408, 429, 500, 502, 503, 504),
    max_attempts: int = 3,
    backoff_seconds: float = 0.5,
    max_retry_after_seconds: float = 30.0,
) -> requests.Response:
    """
    Make an HTTP request with small exponential backoff on transient failures.

    Retries on:
    - Timeouts and connection errors
    - HTTP status codes listed in *retry_statuses*

    A ``Retry-After`` response header is honoured but capped at
    *max_retry_after_seconds* — that wait happens outside the per-request
    timeout, so an oversized value must not be allowed to hang the caller.

    Does NOT call ``raise_for_status()``; callers decide how to handle non-2xx.
    Defaults: 3 attempts, 0.5 s initial backoff, Retry-After capped at 30 s.
    """
    m = (method or "GET").upper()
    attempts = max(1, int(max_attempts))
    retry_status_set = set(retry_statuses)
    last_exc: Optional[BaseException] = None

    for attempt in range(attempts):
        try:
            resp = session.request(
                m,
                url,
                params=params,
                headers=headers,
                json=json,
                data=data,
                timeout=timeout,
            )

            if resp.status_code in retry_status_set and attempt < attempts - 1:
                retry_after_header = resp.headers.get("Retry-After")
                if retry_after_header:
                    try:
                        sleep_s = max(0.0, float(retry_after_header))
                    except (TypeError, ValueError):
                        sleep_s = backoff_seconds * (2**attempt)
                    # Cap the honoured Retry-After: this sleep happens outside
                    # the per-request timeout, so an oversized value (e.g. a
                    # server returning "Retry-After: 3600") would otherwise make
                    # the tool block far past its own timeout. If the server
                    # wants a long wait it isn't a "transient" retry — fail fast
                    # and let the caller retry later.
                    sleep_s = min(sleep_s, max_retry_after_seconds)
                    sleep_s += random.uniform(0.0, backoff_seconds * 0.25)
                    time.sleep(sleep_s)
                else:
                    _jittered_sleep(backoff_seconds, attempt)
                continue

            return resp

        except requests.exceptions.RequestException as e:
            last_exc = e
            if attempt < attempts - 1:
                _jittered_sleep(backoff_seconds, attempt)
                continue
            raise

    # Should be unreachable, but keep a clear failure mode.
    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retry failed unexpectedly without an exception")
