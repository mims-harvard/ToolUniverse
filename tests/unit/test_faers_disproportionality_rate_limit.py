"""FAERS_calculate_disproportionality: a failed openFDA count query must not
be silently treated as a genuine zero.

Regression for Fix Round 17: _get_faers_count caught every exception
(including an HTTP 429 from openFDA's rate limit) and returned 0, which is
indistinguishable from "no matching reports." That fake 0 then flowed into
the 2x2 contingency-table arithmetic and could produce a mathematically
impossible negative cell count. Confirmed live with the tool's own
documented example (IBUPROFEN + "Gastrointestinal haemorrhage"): the
unfiltered total-count request hit openFDA's rate limit and the tool
reported "a=0, b=283544, c=0, d=-283544" with no indication anything had
failed.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "faers_analytics_tools.json"
)


def _make_tool():
    from tooluniverse.faers_analytics_tool import FAERSAnalyticsTool

    with open(DATA_FILE) as f:
        tools = json.load(f)
    config = next(
        t for t in tools if t["name"] == "FAERS_calculate_disproportionality"
    )
    return FAERSAnalyticsTool(config)


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"{self.status_code} error")

    def json(self):
        return self._payload


def test_rate_limited_total_count_returns_actionable_error_not_negative_d():
    tool = _make_tool()

    def fake_request_with_retry(session, method, url, **kwargs):
        # The unfiltered total-count request (no `search=`) is rate limited;
        # every filtered request succeeds -- reproduces the exact live
        # scenario that produced a=0, b=283544, c=0, d=-283544.
        if "limit=1" in url and "search=" not in url:
            return _FakeResponse(429, {"error": {"code": "OVER_RATE_LIMIT"}})
        return _FakeResponse(200, {"meta": {"results": {"total": 283544}}})

    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry",
        side_effect=fake_request_with_retry,
    ):
        result = tool.run(
            {
                "operation": "calculate_disproportionality",
                "drug_name": "IBUPROFEN",
                "adverse_event": "Gastrointestinal haemorrhage",
            }
        )

    assert result["status"] == "error"
    # Must not silently report a fabricated (and mathematically impossible)
    # contingency table -- the error should explain the request failed.
    assert "contingency_table" not in result
    assert "rate limit" in result["error"].lower() or "429" in result["error"]


def test_all_counts_succeed_produces_sane_positive_contingency_table():
    tool = _make_tool()

    def fake_request_with_retry(session, method, url, **kwargs):
        if "limit=1" in url and "search=" not in url:
            return _FakeResponse(200, {"meta": {"results": {"total": 20000000}}})
        if 'generic_name:"IBUPROFEN"' in url and "reactionmeddrapt" in url:
            return _FakeResponse(200, {"meta": {"results": {"total": 50}}})
        if 'generic_name:"IBUPROFEN"' in url:
            return _FakeResponse(200, {"meta": {"results": {"total": 283544}}})
        if "reactionmeddrapt" in url:
            return _FakeResponse(200, {"meta": {"results": {"total": 5000}}})
        return _FakeResponse(200, {"meta": {"results": {"total": 0}}})

    with patch(
        "tooluniverse.faers_analytics_tool.request_with_retry",
        side_effect=fake_request_with_retry,
    ):
        result = tool.run(
            {
                "operation": "calculate_disproportionality",
                "drug_name": "IBUPROFEN",
                "adverse_event": "Gastrointestinal haemorrhage",
            }
        )

    assert result["status"] == "success"
    ct = result["data"]["contingency_table"]
    assert all(v > 0 for v in ct.values())


def test_api_key_appended_to_faers_requests_when_env_var_set(monkeypatch):
    monkeypatch.setenv("FDA_API_KEY", "test-key-123")
    tool = _make_tool()
    assert tool.api_key == "test-key-123"
    assert tool._with_api_key("https://api.fda.gov/drug/event.json?limit=1") == (
        "https://api.fda.gov/drug/event.json?limit=1&api_key=test-key-123"
    )
