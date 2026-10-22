from unittest.mock import MagicMock, patch

from tooluniverse.semantic_scholar_tool import SemanticScholarTool


def _tool():
    return SemanticScholarTool({"name": "SemanticScholar_search_papers"})


def _papers(count=5):
    return [
        {
            "paperId": f"paper-{index}",
            "externalIds": {},
            "title": f"Paper {index}",
            "authors": [],
        }
        for index in range(count)
    ]


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    return response


@patch.object(SemanticScholarTool, "_enforce_rate_limit")
@patch("tooluniverse.semantic_scholar_tool.request_with_retry")
def test_sorted_search_consumes_bulk_page_before_next_token(mock_request, _rate):
    mock_request.return_value = _response(
        {"total": 50, "token": "NEXT", "data": _papers()}
    )

    result = _tool().run(
        {"query": "cancer", "sort": "citationCount:desc", "limit": 2}
    )

    assert [row["paper_id"] for row in result["data"]] == ["paper-0", "paper-1"]
    metadata = result["metadata"]
    assert metadata["total_results"] == 50
    assert metadata["upstream_page_size"] == 5
    assert metadata["next_offset"] == 2
    assert metadata["next_token"] is None
    params = mock_request.call_args.kwargs["params"]
    assert "limit" not in params
    assert "offset" not in params


@patch.object(SemanticScholarTool, "_enforce_rate_limit")
@patch("tooluniverse.semantic_scholar_tool.request_with_retry")
def test_sorted_search_exposes_next_token_only_at_bulk_page_end(mock_request, _rate):
    mock_request.return_value = _response(
        {"total": 50, "token": "NEXT", "data": _papers()}
    )

    result = _tool().run(
        {
            "query": "cancer",
            "sort": "citationCount:desc",
            "limit": 2,
            "offset": 4,
            "token": "CURRENT",
        }
    )

    assert [row["paper_id"] for row in result["data"]] == ["paper-4"]
    metadata = result["metadata"]
    assert metadata["next_offset"] is None
    assert metadata["next_token"] == "NEXT"
    assert metadata["has_more"] is True
    assert mock_request.call_args.kwargs["params"]["token"] == "CURRENT"


@patch.object(SemanticScholarTool, "_enforce_rate_limit")
@patch("tooluniverse.semantic_scholar_tool.request_with_retry")
def test_regular_search_sends_offset_and_reports_database_cap(mock_request, _rate):
    mock_request.return_value = _response(
        {"total": 20000, "offset": 3, "next": 5, "data": _papers(2)}
    )

    result = _tool().run({"query": "cancer", "limit": 2, "offset": 3})

    assert mock_request.call_args.kwargs["params"]["offset"] == 3
    metadata = result["metadata"]
    assert metadata["total_results"] == 20000
    assert metadata["retrievable_results"] == 10000
    assert metadata["database_result_complete"] is False
    assert metadata["next_offset"] == 5


def test_token_without_sort_and_out_of_range_offsets_are_rejected():
    tool = _tool()
    assert "only valid" in tool.run({"query": "x", "token": "abc"})["error"]
    assert "0 and 999" in tool.run(
        {"query": "x", "sort": "citationCount:desc", "offset": 1000}
    )["error"]
    assert "0 and 9999" in tool.run({"query": "x", "offset": 10000})["error"]
