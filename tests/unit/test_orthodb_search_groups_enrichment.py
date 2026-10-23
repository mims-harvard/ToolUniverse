"""Regression guard for Fix-R26E-3: OrthoDB_search_groups
(OrthoDBTool, endpoint "search") only enriched the *first* returned group
with name/level_taxid via the /tab endpoint -- confirmed live querying
"lysozyme": 9 of 10 returned groups were bare {"group_id": ...} with no
name or taxid, even though that data is retrievable per-group via /tab
(there is no batch/comma-separated id support on OrthoDB's /tab endpoint).
Fixed by enriching every returned group, not just groups[0]. Network mocked.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.orthodb_tool import OrthoDBTool

pytestmark = pytest.mark.unit


def _tool():
    return OrthoDBTool({"fields": {"endpoint": "search"}, "timeout": 30})


def _json_resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


def _tab_resp(name, level_taxid):
    r = MagicMock()
    r.status_code = 200
    r.text = f"pub_og_id\tog_name\tlevel_taxid\n" f"x\t{name}\t{level_taxid}\n"
    return r


class TestSearchGroupsEnrichment:
    def test_all_returned_groups_are_enriched_not_just_first(self):
        tool = _tool()
        search_resp = _json_resp({"data": ["1at2759", "2at33208", "3at7742"]})
        tab_responses = [
            _tab_resp("Lysozyme", "2759"),
            _tab_resp("lysozyme g-like", "33208"),
            _tab_resp("lysozyme G-like", "7742"),
        ]
        with patch(
            "tooluniverse.orthodb_tool.requests.get",
            side_effect=[search_resp] + tab_responses,
        ):
            result = tool.run({"query": "lysozyme", "limit": 3})

        assert result["status"] == "success"
        groups = result["data"]["groups"]
        assert len(groups) == 3
        for g in groups:
            assert "name" in g
            assert "level_taxid" in g
            assert g["enrichment_status"] == "complete"
        assert groups[0]["name"] == "Lysozyme"
        assert groups[1]["name"] == "lysozyme g-like"
        assert groups[2]["name"] == "lysozyme G-like"

    def test_per_group_tab_failure_is_disclosed_without_dropping_other_groups(self):
        tool = _tool()
        search_resp = _json_resp({"data": ["1at2759", "2at33208"]})
        with patch(
            "tooluniverse.orthodb_tool.requests.get",
            side_effect=[search_resp, Exception("network error"), _tab_resp("ok", "1")],
        ):
            result = tool.run({"query": "lysozyme", "limit": 2})

        assert result["status"] == "success"
        groups = result["data"]["groups"]
        assert len(groups) == 2
        assert "name" not in groups[0]
        assert groups[0]["enrichment_status"] == "unavailable"
        assert "network error" in groups[0]["enrichment_error"]
        assert groups[1]["name"] == "ok"
        assert groups[1]["enrichment_status"] == "complete"
        summary = result["metadata"]["group_enrichment"]
        assert summary == {
            "attempted": 2,
            "complete": 1,
            "failed": 1,
            "all_complete": False,
            "failures": [
                {
                    "group_id": "1at2759",
                    "error": "OrthoDB /tab request failed: network error",
                }
            ],
        }

    def test_non_200_or_malformed_enrichment_is_never_silent(self):
        tool = _tool()
        search_resp = _json_resp({"data": ["1at2759", "2at33208"], "count": "2"})
        unavailable = MagicMock(status_code=503, text="maintenance")
        malformed = MagicMock(status_code=200, text="pub_og_id\tog_name\tlevel_taxid\n")
        with patch(
            "tooluniverse.orthodb_tool.requests.get",
            side_effect=[search_resp, unavailable, malformed],
        ):
            result = tool.run({"query": "lysozyme", "limit": 2})

        assert result["status"] == "success"
        assert [g["enrichment_status"] for g in result["data"]["groups"]] == [
            "unavailable",
            "unavailable",
        ]
        assert result["metadata"]["group_enrichment"]["failed"] == 2
        assert "HTTP 503" in result["metadata"]["group_enrichment"]["failures"][0]["error"]
        assert "no member row" in result["metadata"]["group_enrichment"]["failures"][1]["error"]
