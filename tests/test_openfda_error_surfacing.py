"""openFDA API failures must surface as errors, not as an empty result.

openFDA answers quota / auth / server problems with a JSON error envelope.
Only NOT_FOUND means "this label has no such field". Every other code means the
query never ran, and returning None for those is indistinguishable from a
genuinely absent field -- an LLM agent then answers from parametric knowledge
with nothing in the logs to show the evidence was missing.

Regression guard for that silent-null path.
"""
import sys
import types

import pytest
import requests

pytestmark = pytest.mark.unit

from tooluniverse import openfda_tool as M
from tooluniverse.openfda_tool import search_openfda

ENDPOINT = "https://api.fda.gov/drug/label.json"
PARAMS = {"search": 'openfda.brand_name:"Kisunla"', "limit": 1}


class _Resp:
    def __init__(self, payload, status=200, headers=None, text=""):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.text = text

    def json(self):
        if self._payload is _Resp:  # sentinel: non-JSON body
            raise ValueError("no json")
        return self._payload


@pytest.fixture
def fake_requests(monkeypatch):
    """Swap requests inside openfda_tool, keeping the real exception classes."""

    def _install(resp_factory):
        monkeypatch.setattr(
            M, "requests",
            types.SimpleNamespace(get=lambda *a, **k: resp_factory(),
                                  exceptions=requests.exceptions),
        )
        monkeypatch.setattr(M, "OPENFDA_MAX_RETRIES", 0)

    return _install


def _call():
    return search_openfda(params=PARAMS, endpoint_url=ENDPOINT,
                          return_fields=["clinical_pharmacology"])


@pytest.mark.parametrize(
    "code,status",
    [("OVER_RATE_LIMIT", 429), ("API_KEY_INVALID", 403), ("SERVER_ERROR", 500)],
)
def test_api_errors_are_not_silently_none(fake_requests, code, status):
    fake_requests(lambda: _Resp({"error": {"code": code, "message": "boom"}}, status))
    out = _call()
    assert out is not None, f"{code} returned None -- indistinguishable from missing data"
    assert isinstance(out, dict)
    assert out.get("status") == "error"
    assert code in out.get("error", "")
    assert out.get("results") == []


def test_rate_limit_explains_how_to_fix(fake_requests):
    fake_requests(
        lambda: _Resp({"error": {"code": "OVER_RATE_LIMIT", "message": "slow down"}}, 429)
    )
    out = _call()
    assert out["error_details"]["retriable"] is True
    assert any("FDA_API_KEY" in s for s in out.get("next_steps", []))


def test_not_found_still_reports_no_data(fake_requests):
    """NOT_FOUND is legitimate absence and must keep its existing shape."""
    fake_requests(lambda: _Resp({"error": {"code": "NOT_FOUND", "message": "No matches"}}, 404))
    out = _call()
    assert isinstance(out, dict)
    assert out.get("results") == []
    assert "suggestion" in out


def test_non_json_body_is_reported(fake_requests):
    """A non-JSON body (e.g. an HTML gateway page) must surface as an error."""
    fake_requests(lambda: _Resp(_Resp, 502, text="<html>gateway</html>"))
    out = _call()
    assert out is not None and out.get("status") == "error"
    assert "non-JSON" in out["error"]


def test_timeout_is_reported(monkeypatch):
    """A network timeout must surface as an error, not as absent data."""

    def boom(*a, **k):
        raise requests.exceptions.Timeout("too slow")

    monkeypatch.setattr(
        M, "requests",
        types.SimpleNamespace(get=boom, exceptions=requests.exceptions),
    )
    monkeypatch.setattr(M, "OPENFDA_MAX_RETRIES", 0)
    out = _call()
    assert out is not None and out.get("status") == "error"
    assert "timed out" in out["error"]


def test_request_uses_a_timeout(monkeypatch):
    """A hung openFDA connection must not stall the caller forever."""
    seen = {}

    def capture(url, **kw):
        seen.update(kw)
        return _Resp({"results": [{"clinical_pharmacology": ["x"]}],
                      "meta": {"results": {}}})

    monkeypatch.setattr(
        M, "requests",
        types.SimpleNamespace(get=capture, exceptions=requests.exceptions),
    )
    _call()
    assert seen.get("timeout"), "openFDA GET issued without a timeout"


# ---------------------------------------------------------------------------
# fda_label_tool: the FDA_* label tools sent no api_key at all, so they sat on
# openFDA's anonymous quota even when FDA_API_KEY was configured.
# ---------------------------------------------------------------------------
from tooluniverse import fda_label_tool as FL  # noqa: E402


def test_label_tool_sends_api_key(monkeypatch):
    """A configured FDA_API_KEY must actually reach openFDA."""
    seen = {}

    def capture(url, params=None, timeout=None, **kw):
        seen["params"] = params or {}
        seen["timeout"] = timeout
        return _Resp({"results": []}, 200)

    monkeypatch.setenv("FDA_API_KEY", "k" * 40)
    monkeypatch.setattr(FL, "requests",
                        types.SimpleNamespace(get=capture, exceptions=requests.exceptions))
    FL._fda_get({"search": "x", "limit": 1})
    assert seen["params"].get("api_key") == "k" * 40
    assert seen["timeout"], "label tool issued a request without a timeout"


def test_label_tool_ignores_placeholder_key(monkeypatch):
    """Placeholder values must not be sent as a key."""
    seen = {}

    def capture(url, params=None, timeout=None, **kw):
        seen["params"] = params or {}
        return _Resp({"results": []}, 200)

    monkeypatch.setenv("FDA_API_KEY", "your_api_key_here")
    monkeypatch.setattr(FL, "requests",
                        types.SimpleNamespace(get=capture, exceptions=requests.exceptions))
    FL._fda_get({"search": "x", "limit": 1})
    assert "api_key" not in seen["params"]


def test_label_tool_retries_rate_limit(monkeypatch):
    """429 is retried with backoff rather than surfaced on the first attempt."""
    calls = {"n": 0}

    def flaky(url, params=None, timeout=None, **kw):
        calls["n"] += 1
        if calls["n"] == 1:
            return _Resp({"error": {"code": "OVER_RATE_LIMIT"}}, 429,
                         headers={"Retry-After": "0"})
        return _Resp({"results": [{"openfda": {}}]}, 200)

    monkeypatch.setattr(FL, "requests",
                        types.SimpleNamespace(get=flaky, exceptions=requests.exceptions))
    monkeypatch.setattr(FL, "FDA_LABEL_MAX_RETRIES", 2)
    monkeypatch.setattr(FL.time, "sleep", lambda *_: None)
    resp = FL._fda_get({"search": "x", "limit": 1})
    assert calls["n"] == 2
    assert resp.status_code == 200
