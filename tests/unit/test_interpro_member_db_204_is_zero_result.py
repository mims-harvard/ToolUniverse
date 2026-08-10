"""Regression guard for round-32 fix: the EBI InterPro REST API returns HTTP
204 No Content to mean "the query was valid but matched zero records" (e.g.
GET /entry/antifam/?type=domain -- AntiFam has zero entries of type
'domain', they're all 'family'). InterProMemberDBTool._get() used to map
every non-200/non-404 status -- including 204 -- to a generic
'InterPro API HTTP error: 204', turning a legitimate empty result into a
false failure.

The fix: list-shaped endpoints (_list_member_entries,
_get_structures_for_entry) treat 204 as a valid empty result and return
status "success" with an honest zero count plus an explanatory 'note' key.
Detail-shaped endpoints (_get_member_entry) keep failing loudly on 204,
since turning a single-record 204 into an object of all-None fields would
be worse than an explicit error.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.interpro_member_db_tool import InterProMemberDBTool

pytestmark = pytest.mark.unit


def _mock_204_response():
    resp = MagicMock()
    resp.status_code = 204
    return resp


class TestListMemberEntries204IsZeroResult:
    def test_204_returns_success_with_zero_count_and_note(self):
        tool = InterProMemberDBTool({"fields": {"endpoint": "list_member_entries"}})

        with patch(
            "tooluniverse.interpro_member_db_tool.requests.get",
            return_value=_mock_204_response(),
        ):
            result = tool.run(
                {
                    "member_database": "antifam",
                    "entry_type": "domain",
                    "page_size": 5,
                }
            )

        assert result["status"] == "success"
        data = result["data"]
        assert data["total_count"] == 0
        assert data["returned"] == 0
        assert data["entries"] == []
        assert "note" in data
        assert "204" in data["note"] or "zero" in data["note"].lower()
        # Filter that narrowed it to zero should be echoed.
        assert "domain" in data["note"]


class TestGetStructuresForEntry204IsZeroResult:
    def test_204_returns_success_with_zero_count_and_note(self):
        tool = InterProMemberDBTool(
            {"fields": {"endpoint": "get_structures_for_entry"}}
        )

        with patch(
            "tooluniverse.interpro_member_db_tool.requests.get",
            return_value=_mock_204_response(),
        ):
            result = tool.run({"interpro_id": "IPR000719", "page_size": 5})

        assert result["status"] == "success"
        data = result["data"]
        assert data["total_structures"] == 0
        assert data["returned"] == 0
        assert data["structures"] == []
        assert "note" in data
        assert "204" in data["note"] or "zero" in data["note"].lower()


class TestGetMemberEntry204StaysAnError:
    def test_204_on_detail_endpoint_is_still_an_error(self):
        tool = InterProMemberDBTool({"fields": {"endpoint": "get_member_entry"}})

        with patch(
            "tooluniverse.interpro_member_db_tool.requests.get",
            return_value=_mock_204_response(),
        ):
            result = tool.run({"member_database": "pfam", "accession": "PF00069"})

        assert result["status"] == "error"
        assert "204" in result["error"]


class TestListMemberDatabases204StaysAnError:
    def test_204_on_catalog_endpoint_is_still_an_error(self):
        """list_member_databases does not pass empty_ok=True: a 204 there
        would mean the whole catalog vanished, which is not a legitimate
        empty result and should keep failing loudly."""
        tool = InterProMemberDBTool({"fields": {"endpoint": "list_member_databases"}})

        with patch(
            "tooluniverse.interpro_member_db_tool.requests.get",
            return_value=_mock_204_response(),
        ):
            result = tool.run({})

        assert result["status"] == "error"
        assert "204" in result["error"]
