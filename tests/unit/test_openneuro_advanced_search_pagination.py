import json
from unittest.mock import Mock, patch

from tooluniverse.openneuro_tool import OpenNeuroTool


def _config():
    with open("src/tooluniverse/data/openneuro_tools.json") as handle:
        return next(
            item
            for item in json.load(handle)
            if item["name"] == "OpenNeuro_advanced_search"
        )


def _response(*, edges, count, has_more, cursor, errors=None):
    response = Mock()
    response.ok = True
    response.json.return_value = {
        "data": {
            "participantCount": 86623,
            "advancedSearch": {
                "edges": edges,
                "pageInfo": {
                    "count": count,
                    "hasNextPage": has_more,
                    "endCursor": cursor,
                },
            },
        },
        **({"errors": errors} if errors else {}),
    }
    return response


@patch("tooluniverse.openneuro_tool.requests.post")
def test_advanced_search_preserves_cursor_when_permission_hides_an_edge(mock_post):
    mock_post.return_value = _response(
        edges=[None, {"node": {"id": "ds008590"}}, {"node": {"id": "ds008589"}}],
        count=3390,
        has_more=True,
        cursor="cursor-6",
        errors=[{"message": "You do not have access to read this dataset."}],
    )
    result = OpenNeuroTool(_config()).run(
        {"species": "human", "first": 3, "after": "cursor-3"}
    )

    assert result["status"] == "success"
    assert result["metadata"]["returned_readable"] == 2
    assert result["metadata"]["permission_omitted_on_page"] == 1
    assert result["metadata"]["total_results"] == 3390
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_cursor"] == "cursor-6"
    assert result["metadata"]["result_set_complete"] is False
    sent = mock_post.call_args.kwargs["json"]["variables"]
    assert sent["query"] == {"species": "human"}
    assert sent["after"] == "cursor-3"


@patch("tooluniverse.openneuro_tool.requests.post")
def test_advanced_search_last_complete_page_clears_cursor(mock_post):
    mock_post.return_value = _response(
        edges=[{"node": {"id": "only"}}],
        count=1,
        has_more=False,
        cursor="server-end",
    )
    result = OpenNeuroTool(_config()).run({"species": "mouse", "first": 3})

    assert result["metadata"]["next_cursor"] is None
    assert result["metadata"]["result_set_complete"] is True
