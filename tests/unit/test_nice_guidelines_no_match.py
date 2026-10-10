"""A NICE search that matches nothing is an empty result, not an error.

It used to answer {"status": "error", "error": "No NICE guidelines found",
"suggestion": "... check if the NICE website is accessible"}, so an agent asking
about a condition NICE has no guidance on (23 of 30 replayed MedR/NOHARM
queries) was told the tool might be broken.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.unified_guideline_tools import NICEWebScrapingTool

pytestmark = pytest.mark.unit


def _page(results):
    data = {"props": {"pageProps": {"results": results}}}
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.content = (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(data)
        + "</script></html>"
    ).encode()
    return resp


def _run(response):
    tool = NICEWebScrapingTool({"name": "NICE_Clinical_Guidelines_Search"})
    with (
        patch.object(tool.session, "get", return_value=response),
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
    ):
        return tool.run({"query": "chronic orchialgia", "limit": 5})


def test_no_documents_is_an_empty_success_with_the_total():
    result = _run(_page({"documents": [], "resultCount": 0}))
    assert result["status"] == "success" and result["data"] == []
    assert result["metadata"]["total"] == 0 and result["metadata"]["source"] == "NICE"


def test_matches_are_still_returned():
    doc = {
        "title": "Hypertension in adults",
        "url": "/guidance/ng136",
        "abstract": "This guideline covers hypertension.",
        "niceResultType": "NICE guideline",
    }
    result = _run(_page({"documents": [doc], "resultCount": 1}))
    assert result["status"] == "success"
    assert result["data"][0]["url"] == "https://www.nice.org.uk/guidance/ng136"


def test_an_unreadable_page_is_an_error_that_says_so():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.content = b"<html><body>maintenance</body></html>"
    result = _run(resp)
    assert result["status"] == "error" and "__NEXT_DATA__" in result["error"]


def test_detail_page_summaries_stop_at_the_budget():
    docs = [
        {
            "title": f"Guideline {i}",
            "url": f"/guidance/ng{i}",
            "niceResultType": "NICE guideline",
        }
        for i in range(3)
    ]
    tool = NICEWebScrapingTool({"name": "NICE_Clinical_Guidelines_Search"})
    with (
        patch.object(
            tool.session,
            "get",
            return_value=_page({"documents": docs, "resultCount": 3}),
        ),
        patch.object(
            tool, "_fetch_guideline_summary", return_value="Summary."
        ) as fetch,
        patch("tooluniverse.unified_guideline_tools.time.sleep"),
        # call start, then one row inside the budget, then the budget is spent
        patch(
            "tooluniverse.unified_guideline_tools.time.monotonic",
            side_effect=[0.0, 1.0, 99.0, 99.0],
        ),
    ):
        result = tool.run({"query": "x", "limit": 3})
    assert fetch.call_count == 1
    assert [r["summary"] for r in result["data"]] == ["Summary.", "", ""]
    assert "content_unavailable" not in result["data"][0]
    assert all("budget" in r["content_unavailable"] for r in result["data"][1:])
