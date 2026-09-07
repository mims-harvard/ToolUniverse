"""Tests for the SmartAPI registry tool.

ToolUniverse already wraps a large fraction of what SmartAPI's ~270
registered biomedical APIs describe, but had no way to discover what else
is registered or resolve an API name to its base URL and endpoints.
Tests assert a well-known entry (MyVariant.info) round-trips correctly.
"""

import pytest
from tooluniverse import ToolUniverse


TRANSIENT = ("timed out", "Failed to connect", "HTTP 5")

MYVARIANT_SLUG = "myvariant"


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
        assert "SmartAPI_search_apis" in names
        assert "SmartAPI_get_api" in names


class TestSearchApis:
    def test_finds_myvariant(self, tu):
        rows = data_of(tu.tools.SmartAPI_search_apis(query="variant", limit=20))
        assert any(r["slug"] == MYVARIANT_SLUG for r in rows)

    def test_tag_scoped_query(self, tu):
        rows = data_of(
            tu.tools.SmartAPI_search_apis(query="tags.name:translator", limit=5)
        )
        assert rows

    def test_limit_is_respected(self, tu):
        rows = data_of(tu.tools.SmartAPI_search_apis(query="variant", limit=2))
        assert len(rows) <= 2

    def test_unmatched_query(self, tu):
        result = tu.tools.SmartAPI_search_apis(query="zzzznotarealAPIterm12345")
        assert result["status"] == "error"

    def test_missing_query(self, tu):
        assert tu.tools.SmartAPI_search_apis(query="")["status"] == "error"


class TestGetApi:
    def test_myvariant_metadata(self, tu):
        data = data_of(tu.tools.SmartAPI_get_api(api_id=MYVARIANT_SLUG))
        assert data["title"] == "MyVariant.info API"
        assert data["base_urls"] == ["https://myvariant.info/v1"]
        assert "/query" in data["endpoints"]

    def test_unknown_api_id(self, tu):
        result = tu.tools.SmartAPI_get_api(api_id="notarealslug12345")
        assert result["status"] == "error"

    def test_missing_api_id(self, tu):
        assert tu.tools.SmartAPI_get_api(api_id="")["status"] == "error"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("SmartAPI_search_apis", {"query": ""}),
            ("SmartAPI_get_api", {"api_id": ""}),
            ("SmartAPI_get_api", {"api_id": "notarealslug12345"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
