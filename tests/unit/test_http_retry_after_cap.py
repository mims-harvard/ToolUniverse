"""Unit test for request_with_retry's Retry-After cap.

A 429/503 Retry-After header is honoured, but the wait happens outside the
per-request timeout — so an oversized value (e.g. "Retry-After: 3600")
must be capped, otherwise the tool blocks far past its own timeout.
"""
from unittest.mock import MagicMock

import pytest

import tooluniverse.http_utils as hu


class _FakeSession:
    """Returns 429+Retry-After on the first call, then 200."""

    def __init__(self, retry_after):
        self.calls = 0
        self.retry_after = retry_after

    def request(self, *args, **kwargs):
        self.calls += 1
        resp = MagicMock()
        if self.calls == 1:
            resp.status_code = 429
            resp.headers = {"Retry-After": self.retry_after}
        else:
            resp.status_code = 200
            resp.headers = {}
        return resp


@pytest.mark.unit
def test_oversized_retry_after_is_capped(monkeypatch):
    slept = []
    monkeypatch.setattr(hu.time, "sleep", lambda s: slept.append(s))

    resp = hu.request_with_retry(
        _FakeSession("3600"), "GET", "http://example", max_retry_after_seconds=30.0
    )

    assert resp.status_code == 200
    assert slept, "should have slept once before the retry"
    # 30 + a small jitter, never the raw 3600.
    assert slept[0] <= 31.0


@pytest.mark.unit
def test_small_retry_after_is_honoured_unchanged(monkeypatch):
    slept = []
    monkeypatch.setattr(hu.time, "sleep", lambda s: slept.append(s))

    hu.request_with_retry(
        _FakeSession("2"), "GET", "http://example", max_retry_after_seconds=30.0
    )

    # ~2s honoured (plus tiny jitter), well under the cap.
    assert 2.0 <= slept[0] <= 2.5
