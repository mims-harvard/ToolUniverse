from unittest.mock import patch

from tooluniverse.unified_guideline_tools import (
    CTFPHCListGuidelinesTool,
    CTFPHCSearchGuidelinesTool,
    SIGNListGuidelinesTool,
    SIGNSearchGuidelinesTool,
)


SIGN_ROWS = [
    {
        "number": index,
        "title": f"Cancer guideline {index}",
        "topic": "Cancer",
        "published": "2025",
        "url": f"https://example.org/sign/{index}",
    }
    for index in range(5)
]

CTFPHC_ROWS = [
    {
        "title": f"Cancer screening {index}",
        "url": f"https://example.org/ctfphc/{index}",
        "year": "2025",
    }
    for index in range(5)
]


@patch(
    "tooluniverse.unified_guideline_tools._fetch_sign_table", return_value=SIGN_ROWS
)
def test_sign_list_and_search_recover_later_page(_fetch):
    for tool, arguments in (
        (SIGNListGuidelinesTool({}), {"limit": 2, "offset": 2}),
        (
            SIGNSearchGuidelinesTool({}),
            {"query": "cancer", "limit": 2, "offset": 2},
        ),
    ):
        result = tool.run(arguments)
        assert [row["number"] for row in result] == [2, 3]
        page = result[0]["search_pagination"]
        assert page["total_count"] == 5
        assert page["has_more"] is True
        assert page["next_offset"] == 4


@patch(
    "tooluniverse.unified_guideline_tools._fetch_ctfphc_links",
    return_value=CTFPHC_ROWS,
)
def test_ctfphc_list_and_search_tail_page_terminates(_fetch):
    for tool, arguments in (
        (CTFPHCListGuidelinesTool({}), {"limit": 2, "offset": 4}),
        (
            CTFPHCSearchGuidelinesTool({}),
            {"query": "cancer", "limit": 2, "offset": 4},
        ),
    ):
        result = tool.run(arguments)
        assert [row["title"] for row in result] == ["Cancer screening 4"]
        page = result[0]["search_pagination"]
        assert page["total_count"] == 5
        assert page["has_more"] is False
        assert page["next_offset"] is None


def test_guideline_tools_reject_invalid_pagination_before_fetch():
    with patch("tooluniverse.unified_guideline_tools._fetch_sign_table") as fetch:
        result = SIGNListGuidelinesTool({}).run({"limit": 0})
        assert "positive integer" in result["error"]
        result = SIGNListGuidelinesTool({}).run({"offset": -1})
        assert "non-negative integer" in result["error"]
    fetch.assert_not_called()
