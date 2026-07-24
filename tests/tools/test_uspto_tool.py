"""
Unit tests for the USPTO Open Data Portal tool.

Covers the authentication-error guidance added so that a rejected API key
(HTTP 403) produces an actionable hint instead of an opaque "HTTP Error: 403".
USPTO validates the API key before parsing the query, so a bad key makes every
query return 403 regardless of query format.
"""

import json
import pytest
import requests
from unittest.mock import patch, MagicMock


TOOL_NAME = "get_patent_overview_by_text_query"


@pytest.fixture
def tool_config():
    with open("src/tooluniverse/data/uspto_tools.json") as f:
        tools = json.load(f)
    return next(t for t in tools if t["name"] == TOOL_NAME)


@pytest.fixture
def tool(tool_config):
    from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

    # api_key is passed explicitly so the tool initialises without a real key.
    return USPTOOpenDataPortalTool(tool_config, api_key="test-key")


def _http_error_response(status_code, body):
    """Build a mocked response whose raise_for_status() raises an HTTPError."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    return resp


class TestHttpErrorHint:
    """The static status-code -> guidance mapper."""

    def test_hint_401_missing_key(self):
        from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

        hint = USPTOOpenDataPortalTool._http_error_hint(401)
        assert hint and "401" in hint
        assert "USPTO_API_KEY" in hint

    def test_hint_403_rejected_key(self):
        from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

        hint = USPTOOpenDataPortalTool._http_error_hint(403)
        assert hint and "403" in hint
        # Must steer users away from query-syntax debugging.
        assert "query-format" in hint.lower()
        assert "data.uspto.gov" in hint

    def test_hint_404_no_records(self):
        from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

        hint = USPTOOpenDataPortalTool._http_error_hint(404)
        assert hint and "404" in hint
        # Must distinguish "no data" from a key/tool failure.
        assert "no records" in hint.lower() or "no matching" in hint.lower()
        assert "key" in hint.lower()

    def test_hint_other_status_is_none(self):
        from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

        assert USPTOOpenDataPortalTool._http_error_hint(500) is None
        assert USPTOOpenDataPortalTool._http_error_hint(200) is None


class TestRunHttpErrorHandling:
    """The run() HTTPError branch attaches hints for auth failures only."""

    def test_run_403_returns_actionable_hint(self, tool):
        resp = _http_error_response(403, {"message": "Forbidden"})
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"query": "applicationMetaData.patentNumber:10117952", "limit": 1}
            )
        assert result["status"] == "error"
        assert result["data"]["error"] == "HTTP Error: 403"
        assert result["data"]["details"] == {"message": "Forbidden"}
        assert "hint" in result["data"]
        assert "query-format" in result["data"]["hint"].lower()

    def test_run_401_returns_actionable_hint(self, tool):
        resp = _http_error_response(401, {"message": "Unauthorized"})
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run({"query": "applicationMetaData.inventionTitle:widget"})
        assert result["status"] == "error"
        assert result["data"]["error"] == "HTTP Error: 401"
        assert "USPTO_API_KEY" in result["data"]["hint"]

    def test_run_404_returns_no_records_hint(self, tool):
        resp = _http_error_response(
            404,
            {"code": "404", "message": "Not Found",
             "detailedMessage": "No matching records found"},
        )
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run(
                {"query": "applicationMetaData.patentNumber:10117952", "limit": 1}
            )
        assert result["status"] == "error"
        assert result["data"]["error"] == "HTTP Error: 404"
        assert "no records" in result["data"]["hint"].lower()

    def test_run_500_has_no_hint(self, tool):
        resp = _http_error_response(500, {"message": "Server Error"})
        with patch.object(tool.session, "get", return_value=resp):
            result = tool.run({"query": "applicationMetaData.inventionTitle:widget"})
        assert result["status"] == "error"
        assert result["data"]["error"] == "HTTP Error: 500"
        assert "hint" not in result["data"]


class TestInitRequiresKey:
    """The tool refuses to initialise without a key rather than failing at call time."""

    def test_missing_key_raises(self, tool_config):
        from tooluniverse.uspto_tool import USPTOOpenDataPortalTool

        with pytest.raises(ValueError, match="USPTO_API_KEY"):
            USPTOOpenDataPortalTool(tool_config, api_key=None)
