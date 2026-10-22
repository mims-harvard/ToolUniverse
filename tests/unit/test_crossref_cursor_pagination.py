import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.crossref_tool import CrossrefRESTTool


def _config(name):
    with open("src/tooluniverse/data/crossref_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def _response(items, total, next_cursor="cursor-next"):
    response = Mock()
    response.status_code = 200
    response.text = ""
    response.json.return_value = {
        "message": {
            "items": items,
            "total-results": total,
            "items-per-page": len(items),
            "query": {"start-index": 0},
            "next-cursor": next_cursor,
        }
    }
    return response


@pytest.mark.parametrize(
    "name,query",
    [
        ("Crossref_search_works", "CRISPR"),
        ("Crossref_list_funders", "health"),
        ("Crossref_search_members", "elsevier"),
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_crossref_lists_start_in_deep_cursor_mode(mock_request, name, query):
    mock_request.return_value = _response([{"id": 1}, {"id": 2}], 2064)
    result = CrossrefRESTTool(_config(name)).run({"query": query, "limit": 2})

    assert mock_request.call_args.kwargs["params"]["cursor"] == "*"
    assert result["metadata"]["total_results"] == 2064
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == "cursor-next"
    assert result["metadata"]["result_set_complete"] is False


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_continuation_cursor_is_forwarded_verbatim(mock_request):
    mock_request.return_value = _response([{"DOI": "a"}, {"DOI": "b"}], 49212)
    result = CrossrefRESTTool(_config("Crossref_search_works")).run(
        {"query": "CRISPR", "limit": 2, "cursor": "opaque-server-cursor"}
    )

    assert mock_request.call_args.kwargs["params"]["cursor"] == "opaque-server-cursor"
    assert result["metadata"]["next_cursor"] == "cursor-next"


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_small_initial_result_is_complete_even_if_crossref_emits_cursor(mock_request):
    mock_request.return_value = _response([{"id": 340}], 1, "unused-cursor")
    result = CrossrefRESTTool(_config("Crossref_search_members")).run(
        {"query": "plos", "limit": 20}
    )

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None
    assert result["metadata"]["result_set_complete"] is True
