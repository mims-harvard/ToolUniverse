"""Regression guard for Fix-R11A-1: RCSBAdvSearch_search_structures had no
way to request relevance-sorted results, even though every hit already
carries a `score` field in the response -- the sort_map only had
resolution/date/weight. Confirmed live and via raw RCSB Search API curl
that "score" is a valid sort_by value and sorts correctly descending.
Without it, results defaulted to resolution-sorted order, so the
highest-relevance hit for a text query could be buried well past the
first page.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.rcsb_advanced_search_tool import RCSBAdvancedSearchTool

pytestmark = pytest.mark.unit


def _tool():
    return RCSBAdvancedSearchTool(
        {
            "name": "RCSBAdvSearch_search_structures",
            "fields": {"endpoint": "advanced_search"},
        }
    )


def _mock_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"result_set": [], "total_count": 0}
    return resp


def test_score_sort_by_maps_to_score_field_descending():
    tool = _tool()
    with patch("requests.post", return_value=_mock_response()) as mock_post:
        tool.run({"query": "KRAS G12C", "sort_by": "score"})

    body = mock_post.call_args.kwargs["json"]
    sort_clause = body["request_options"]["sort"][0]
    assert sort_clause["sort_by"] == "score"
    assert sort_clause["direction"] == "desc"


def test_default_sort_is_still_resolution_ascending():
    tool = _tool()
    with patch("requests.post", return_value=_mock_response()) as mock_post:
        tool.run({"query": "KRAS G12C"})

    body = mock_post.call_args.kwargs["json"]
    sort_clause = body["request_options"]["sort"][0]
    assert sort_clause["sort_by"] == "rcsb_entry_info.resolution_combined"
    assert sort_clause["direction"] == "asc"


def test_date_sort_still_descending():
    tool = _tool()
    with patch("requests.post", return_value=_mock_response()) as mock_post:
        tool.run({"query": "KRAS G12C", "sort_by": "date"})

    sort_clause = mock_post.call_args.kwargs["json"]["request_options"]["sort"][0]
    assert sort_clause["direction"] == "desc"
