import json
from unittest.mock import Mock, patch

from tooluniverse.openneuro_tool import OpenNeuroTool


def _config():
    with open("src/tooluniverse/data/openneuro_tools.json") as handle:
        return next(
            item
            for item in json.load(handle)
            if item["name"] == "OpenNeuro_search_by_modality"
        )


def _response(ids, count, has_more, cursor):
    response = Mock()
    response.ok = True
    response.json.return_value = {
        "data": {
            "datasets": {
                "edges": [{"node": {"id": item}} for item in ids],
                "pageInfo": {
                    "count": count,
                    "hasNextPage": has_more,
                    "endCursor": cursor,
                },
            }
        }
    }
    return response


@patch("tooluniverse.graphql_tool.requests.post")
def test_modality_search_passes_cursor_and_exposes_exact_total(mock_post):
    mock_post.return_value = _response(["ds4", "ds5", "ds6"], 446, True, "cursor-6")
    result = OpenNeuroTool(_config()).run(
        {"modality": "EEG", "first": 3, "after": "cursor-3"}
    )

    assert result["status"] == "success"
    assert result["metadata"] == {
        "returned": 3,
        "total_results": 446,
        "total_results_is_exact": True,
        "has_more": True,
        "next_cursor": "cursor-6",
        "result_set_complete": False,
    }
    assert mock_post.call_args.kwargs["json"]["variables"]["after"] == "cursor-3"


@patch("tooluniverse.graphql_tool.requests.post")
def test_modality_search_last_page_clears_stale_cursor(mock_post):
    mock_post.return_value = _response(["last"], 446, False, "server-end")
    result = OpenNeuroTool(_config()).run(
        {"modality": "EEG", "first": 3, "after": "cursor-445"}
    )
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_cursor"] is None
