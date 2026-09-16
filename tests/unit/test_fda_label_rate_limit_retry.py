"""openFDA rate limits must be retried, not surfaced on the first 429.

openFDA throttles per minute as well as per day, so a burst of label lookups
can hit 429 even with a valid FDA_API_KEY. These calls previously went through
a bare ``requests.get`` followed by ``raise_for_status()``, so a transient 429
became a hard failure for that tool call.

Routing them through ``request_with_retry`` reuses the same backoff-and-honour-
``Retry-After`` behaviour the rest of the package already uses.
"""

import types

import pytest
import requests

from tooluniverse import fda_label_tool as FL

pytestmark = pytest.mark.unit


class _Resp:
    def __init__(self, payload, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code}", response=self)


def _install(monkeypatch, responses):
    """Serve *responses* in order, recording how many requests were made."""
    calls = {"n": 0}

    def fake_request(method, url, **kwargs):
        calls["n"] += 1
        return responses[min(calls["n"] - 1, len(responses) - 1)]

    monkeypatch.setattr(
        FL,
        "requests",
        types.SimpleNamespace(
            get=lambda url, **kw: fake_request("GET", url, **kw),
            exceptions=requests.exceptions,
        ),
    )
    from tooluniverse import http_utils

    monkeypatch.setattr(http_utils.time, "sleep", lambda *_: None)
    return calls


def _label_payload():
    return {
        "results": [
            {"openfda": {"brand_name": ["Kisunla"]}, "indications_and_usage": ["x"]}
        ]
    }


def test_a_rate_limited_lookup_is_retried_rather_than_failing(monkeypatch):
    calls = _install(
        monkeypatch,
        [
            _Resp({"error": {"code": "OVER_RATE_LIMIT"}}, 429, {"Retry-After": "0"}),
            _Resp(_label_payload(), 200),
        ],
    )

    tool = FL.FDALabelTool(
        {"name": "FDA_get_indications_by_drug_name", "fields": {"query_type": "search"}}
    )
    tool.run({"drug_name": "Kisunla", "limit": 1})

    assert calls["n"] == 2, "a 429 should have been retried, not surfaced immediately"


def test_a_persistent_rate_limit_still_surfaces(monkeypatch):
    """Retrying must not mask a sustained outage as an empty result."""
    _install(
        monkeypatch,
        [_Resp({"error": {"code": "OVER_RATE_LIMIT"}}, 429, {"Retry-After": "0"})],
    )

    tool = FL.FDALabelTool(
        {"name": "FDA_get_indications_by_drug_name", "fields": {"query_type": "search"}}
    )
    result = tool.run({"drug_name": "Kisunla", "limit": 1})

    assert result is not None
    text = str(result).lower()
    assert "error" in text or "429" in text, result


def test_a_successful_lookup_makes_exactly_one_request(monkeypatch):
    """The retry wrapper must not add requests to the happy path."""
    calls = _install(monkeypatch, [_Resp(_label_payload(), 200)])

    tool = FL.FDALabelTool(
        {"name": "FDA_get_indications_by_drug_name", "fields": {"query_type": "search"}}
    )
    tool.run({"drug_name": "Kisunla", "limit": 1})

    assert calls["n"] == 1
