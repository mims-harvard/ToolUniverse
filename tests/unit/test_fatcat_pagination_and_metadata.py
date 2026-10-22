from unittest.mock import Mock, patch

import pytest

from tooluniverse.fatcat_tool import FatcatResultParser, FatcatScholarTool


def _html(count, next_offset=None):
    links = "".join(
        f'<a href="/fatcat/release/id-{i}">A sufficiently long title {i}</a>'
        for i in range(count)
    )
    next_link = (
        f'<a href="/fatcat/search?q=test&entity_type=releases&offset={next_offset}">Next »</a>'
        if next_offset is not None
        else ""
    )
    return f"<html><body>{links}{next_link}</body></html>"


def _response(text="", status=200):
    response = Mock(status_code=status, text=text)
    response.raise_for_status.return_value = None
    return response


def _tool():
    return FatcatScholarTool({"name": "Fatcat_search_scholar"})


def test_parser_captures_upstream_next_offset_without_making_it_a_result():
    parser = FatcatResultParser()
    parser.feed(_html(2, next_offset=25))

    assert len(parser.results) == 2
    assert parser.upstream_next_offset == 25


def test_search_exposes_recoverable_local_offset_pages():
    search = _response(_html(4, next_offset=25))
    detail = _response(
        '<meta name="citation_author" content="Ada Lovelace">'
        '<meta name="citation_doi" content="10.1/example">'
    )
    with patch(
        "tooluniverse.fatcat_tool.requests.get",
        side_effect=[search, detail, detail],
    ) as get:
        result = _tool().run({"query": "biology", "max_results": 2, "offset": 10})

    assert len(result["data"]) == 2
    assert result["metadata"]["offset"] == 10
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 12
    assert result["metadata"]["total_results_is_known"] is False
    assert result["metadata"]["metadata_fetch_failures"] == 0
    assert all(row["metadata_complete"] for row in result["data"])
    assert get.call_args_list[0].kwargs["params"] == {
        "q": "biology",
        "entity_type": "releases",
        "offset": 10,
    }


def test_short_terminal_page_is_explicitly_complete():
    search = _response(_html(1))
    detail = _response("")
    with patch("tooluniverse.fatcat_tool.requests.get", side_effect=[search, detail]):
        result = _tool().run({"query": "rare phrase", "max_results": 10})

    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert result["metadata"]["complete"] is True


def test_release_metadata_failures_are_not_silently_presented_as_nulls():
    search = _response(_html(2))
    failed = _response("", status=503)
    with patch(
        "tooluniverse.fatcat_tool.requests.get",
        side_effect=[search, failed, RuntimeError("detail timeout")],
    ):
        result = _tool().run({"query": "biology", "max_results": 2})

    assert result["status"] == "success"
    assert result["metadata"]["metadata_fetch_failures"] == 2
    assert result["metadata"]["metadata_complete_for_all_returned"] is False
    assert result["data"][0]["metadata_complete"] is False
    assert "HTTP 503" in result["data"][0]["metadata_error"]
    assert result["data"][1]["metadata_error"] == "detail timeout"


@pytest.mark.parametrize(
    ("arguments", "field"),
    [
        ({"query": ""}, "query"),
        ({"query": "biology", "max_results": "2"}, "max_results"),
        ({"query": "biology", "max_results": 11}, "max_results"),
        ({"query": "biology", "offset": -1}, "offset"),
        ({"query": "biology", "offset": True}, "offset"),
    ],
)
def test_invalid_pagination_is_rejected_before_network(arguments, field):
    with patch("tooluniverse.fatcat_tool.requests.get") as get:
        result = _tool().run(arguments)

    assert result["status"] == "error"
    assert field in result["error"]
    get.assert_not_called()
