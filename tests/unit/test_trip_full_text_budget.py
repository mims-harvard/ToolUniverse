"""TRIP full-text fetches are bounded and never publish an error as content.

Observed live: one wound-care PDF trickled for 54.9 s under requests'
timeout=10 (that timeout bounds each read, not the download) and ran the search
to 72 s, past the 30 s an agent allows; 10 of 43 TRIP calls in ATHENA's runs
timed out. A failed extraction also returned "Error extracting content: ...",
which became the guideline's description.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import unified_guideline_tools as U

pytestmark = pytest.mark.unit

SEARCH_XML = (
    "<results><total>2</total><count>2</count>"
    "<document><title>Burn care guideline</title><link>https://example.org/a.pdf</link>"
    "<category>Guidelines</category><description></description></document>"
    "<document><title>Burn injury</title><link>https://example.org/b</link>"
    "<category>Guidelines</category><description>TRIP summary of burn injury.</description></document>"
    "</results>"
)


def _tool():
    return U.TRIPDatabaseTool({"name": "TRIP_Database_Guidelines_Search"})


def _search_response():
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.content = SEARCH_XML.encode()
    return resp


def test_a_failed_fetch_keeps_the_row_and_says_why():
    tool = _tool()
    with (
        patch.object(tool.session, "get", return_value=_search_response()),
        patch.object(
            tool,
            "_fetch_guideline_content",
            side_effect=U._ContentUnavailable("full text of a.pdf: 403"),
        ),
    ):
        result = tool.run({"query": "burn"})
    first, second = result["data"]
    assert first["description"] == "" and "403" in first["content_unavailable"]
    assert "Error" not in first["content"]
    assert second["description"] == "TRIP summary of burn injury."


def test_past_the_budget_rows_are_not_fetched():
    tool = _tool()
    with (
        patch.object(tool.session, "get", return_value=_search_response()),
        patch.object(tool, "_fetch_guideline_content") as fetch,
        patch.object(U.time, "monotonic", side_effect=[0.0] + [1000.0] * 10),
    ):
        result = tool.run({"query": "burn"})
    fetch.assert_not_called()
    assert "budget" in result["data"][0]["content_unavailable"]


def _streamed(chunks, headers=None):
    resp = MagicMock()
    resp.__enter__.return_value = resp
    resp.raise_for_status.return_value = None
    resp.headers = headers or {}
    resp.iter_content.return_value = iter(chunks)
    return resp


def test_a_trickling_download_is_cut_at_the_wall_clock():
    tool = _tool()
    with (
        patch.object(tool.session, "get", return_value=_streamed([b"x"] * 5)),
        patch.object(U.time, "monotonic", side_effect=[0.0, 1.0, 50.0, 60.0]),
        pytest.raises(U._ContentUnavailable, match="exceeded"),
    ):
        tool._page_text("https://example.org/slow.pdf")


def test_an_oversized_download_is_refused():
    tool = _tool()
    tool.PAGE_MAX_BYTES = 10
    with (
        patch.object(tool.session, "get", return_value=_streamed([b"x" * 6, b"x" * 6])),
        pytest.raises(U._ContentUnavailable, match="larger than"),
    ):
        tool._page_text("https://example.org/big.pdf")


def test_the_downloaded_body_is_what_markitdown_converts():
    tool = _tool()
    converter = MagicMock()
    converter.convert_response.return_value = MagicMock(
        text_content="Recommendation: cool the burn."
    )
    response = _streamed([b"%PDF-1.4 body"])
    with (
        patch.object(tool.session, "get", return_value=response) as get,
        patch.object(U, "_markitdown", return_value=converter),
    ):
        assert (
            tool._page_text("https://example.org/a.pdf")
            == "Recommendation: cool the burn."
        )
    assert get.call_args.kwargs == {"timeout": tool.PAGE_TIMEOUT_S, "stream": True}
    assert response._content == b"%PDF-1.4 body"


def test_no_extracted_text_is_unavailable_not_content():
    tool = _tool()
    converter = MagicMock()
    converter.convert_response.return_value = MagicMock(text_content="")
    with (
        patch.object(tool.session, "get", return_value=_streamed([b"<html></html>"])),
        patch.object(U, "_markitdown", return_value=converter),
        pytest.raises(U._ContentUnavailable, match="no text"),
    ):
        tool._page_text("https://example.org/empty")


def test_an_empty_description_element_does_not_end_the_search():
    tool = _tool()
    with (
        patch.object(tool.session, "get", return_value=_search_response()),
        patch.object(
            tool,
            "_fetch_guideline_content",
            return_value="Cool the burn for 20 minutes.",
        ),
    ):
        result = tool.run({"query": "burn"})
    assert result["status"] == "success"
    assert result["data"][0]["description"] == "Cool the burn for 20 minutes."


def test_a_declared_oversized_page_is_refused_before_reading():
    tool = _tool()
    response = _streamed(
        [b"x"], headers={"Content-Length": str(tool.PAGE_MAX_BYTES + 1)}
    )
    with (
        patch.object(tool.session, "get", return_value=response),
        pytest.raises(U._ContentUnavailable, match="larger than"),
    ):
        tool._page_text("https://example.org/huge.pdf")
    response.iter_content.assert_not_called()


def test_the_calls_remaining_budget_caps_a_download():
    tool = _tool()
    with (
        patch.object(tool.session, "get", return_value=_streamed([b"x"])) as get,
        patch.object(U, "_markitdown", return_value=MagicMock()),
        patch.object(U.time, "monotonic", return_value=100.0),
    ):
        tool._page_text("https://example.org/a", deadline=103.0)
    assert get.call_args.kwargs["timeout"] == 3.0
