"""
Shared HTTP utilities for ToolUniverse tools.

Goal: provide a small, dependency-light helper for retrying transient HTTP failures
without changing individual tool return formats.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Union
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


# Some upstreams block the literal User-Agent requests sends by default.
#
# Harvard Dataverse, which hosts every TDC dataset, answers 403 to
# "python-requests/x.y" and 200 to anything else -- measured on
# /api/access/datafile/4259569: 199 bytes of "403 Forbidden" HTML by default,
# 82501 bytes of the actual file with any other User-Agent, including an empty
# one. ConoServer's nginx does the same to
# /download/conoserver_protein.xml.gz: 403 by default, 856975 bytes otherwise.
#
# request_with_retry passed headers straight through and set none of its own,
# and only 99 of the 551 tool modules mention a User-Agent at all, so the rest
# were sending the blocked string. Naming ourselves is also the polite thing to
# do: an upstream that wants to rate-limit or contact a heavy client can.
DEFAULT_USER_AGENT = (
    "ToolUniverse/1.0 (+https://github.com/mims-harvard/ToolUniverse)"
)


def with_user_agent(
    headers: Optional[Mapping[str, str]] = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> Dict[str, str]:
    """Return *headers* with a User-Agent, leaving a caller's own in place."""
    merged: Dict[str, str] = dict(headers or {})
    if not any(key.lower() == "user-agent" for key in merged):
        merged["User-Agent"] = user_agent
    return merged


def cloudflare_challenge(resp: Any) -> Optional[str]:
    """Describe a Cloudflare JavaScript challenge, or None if it is not one.

    A site behind Cloudflare's managed challenge answers any HTTP client with
    403, ``cf-mitigated: challenge`` and a "Just a moment... Enable JavaScript
    and cookies to continue" page. Passing it needs a JavaScript engine, so no
    header, User-Agent or retry gets through -- measured on rest.wormbase.org
    and foodb.ca with the requests default, ToolUniverse, curl and a current
    Chrome User-Agent: 403 for all four.

    Worth naming rather than reporting a bare 403, because the two are acted on
    very differently: a 403 invites checking credentials and headers, and this
    one means the site has turned on a protection no API client can satisfy.
    """
    try:
        status = getattr(resp, "status_code", None)
        headers = getattr(resp, "headers", {}) or {}
    except Exception:  # noqa: BLE001 - never raise from an error path
        return None
    if status != 403:
        return None
    mitigated = str(headers.get("cf-mitigated") or "").lower()
    server = str(headers.get("Server") or headers.get("server") or "").lower()
    if mitigated != "challenge" and "cloudflare" not in server:
        return None
    body = ""
    try:
        body = (getattr(resp, "text", "") or "")[:2000].lower()
    except Exception:  # noqa: BLE001
        body = ""
    if mitigated != "challenge" and "just a moment" not in body:
        return None
    return (
        "the site is behind a Cloudflare JavaScript challenge "
        "(HTTP 403, cf-mitigated: challenge). Passing it requires a browser "
        "engine, so no User-Agent, header or retry will get through -- this is "
        "a setting on their side, not a problem with your credentials or setup"
    )


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
                headers=with_user_agent(headers),
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
