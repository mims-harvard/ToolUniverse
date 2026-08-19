"""Tests for the openFDA device tool.

ToolUniverse's existing openFDA tools cover only drug data (drug/event,
drug/label, drug/drugsfda); the device side (recalls, MAUDE adverse
events) had no coverage. A bare full-text search was verified to
discriminate correctly (nonsense terms return a clean 404, not an
inflated count) before building, given this codebase's own git history
documents prior openFDA quoting/exactness bugs. Tests assert real,
known recall/event content survives the round trip.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert "OpenFDADevice_search_recalls" in names
        assert "OpenFDADevice_search_adverse_events" in names


class TestSearchRecalls:
    def test_finds_known_pacemaker_recalls(self, tu):
        rows = data_of(
            tu.tools.OpenFDADevice_search_recalls(query="pacemaker", limit=10)
        )
        assert rows
        assert all(r["product_description"] for r in rows)
        assert any(r["recall_status"] for r in rows)

    def test_search_actually_discriminates(self, tu):
        # Regression guard against the openFDA quoting/exactness bugs this
        # codebase's git history documents elsewhere (Fix Round 20).
        result = tu.tools.OpenFDADevice_search_recalls(query="pacemaker", limit=1)
        assert 0 < result["metadata"]["total_matching"] < 100_000

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.OpenFDADevice_search_recalls(query="pacemaker", limit=3)
        )
        assert len(rows) <= 3

    def test_unmatched_query(self, tu):
        result = tu.tools.OpenFDADevice_search_recalls(
            query="zzzznotarealdevice12345"
        )
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.OpenFDADevice_search_recalls(query="")["status"] == "error"


class TestSearchAdverseEvents:
    def test_finds_pacemaker_lead_events(self, tu):
        rows = data_of(
            tu.tools.OpenFDADevice_search_adverse_events(
                device_name="pacemaker", limit=10
            )
        )
        assert rows
        assert all(r["generic_name"] for r in rows)
        assert all(r["event_type"] for r in rows)

    def test_limit_is_respected(self, tu):
        rows = data_of(
            tu.tools.OpenFDADevice_search_adverse_events(
                device_name="pacemaker", limit=3
            )
        )
        assert len(rows) <= 3

    def test_missing_device_name(self, tu):
        result = tu.tools.OpenFDADevice_search_adverse_events(device_name="")
        assert result["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("OpenFDADevice_search_recalls", {"query": ""}),
            ("OpenFDADevice_search_recalls", {"query": "zzzznotarealdevice12345"}),
            ("OpenFDADevice_search_adverse_events", {"device_name": ""}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
