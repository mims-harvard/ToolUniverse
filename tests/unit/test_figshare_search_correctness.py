import json
from unittest.mock import Mock, patch

from tooluniverse.figshare_tool import FigshareTool


def _config():
    with open("src/tooluniverse/data/figshare_tools.json") as handle:
        return next(
            item
            for item in json.load(handle)
            if item["name"] == "Figshare_search_articles"
        )


def _response(items, status=200):
    response = Mock()
    response.status_code = status
    response.json.return_value = items
    response.text = ""
    return response


@patch("tooluniverse.figshare_tool.request_with_retry")
def test_search_uses_post_body_and_exposes_next_page(mock_request):
    mock_request.side_effect = [
        _response([{"id": 1}, {"id": 2}]),
        _response([{"id": 3}]),
    ]
    result = FigshareTool(_config()).run(
        {"search_for": "  CRISPR  ", "item_type": 3, "page_size": 2, "page": 4}
    )

    first = mock_request.call_args_list[0]
    assert first.args[1] == "POST"
    assert first.kwargs["json"] == {
        "search_for": "CRISPR",
        "item_type": 3,
        "page": 4,
        "page_size": 2,
    }
    assert mock_request.call_args_list[1].kwargs["json"]["page"] == 5
    assert result["metadata"]["query_applied"] == "CRISPR"
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 5
    assert result["metadata"]["matches_lower_bound"] == 9


@patch("tooluniverse.figshare_tool.request_with_retry")
def test_short_page_is_known_to_be_final(mock_request):
    mock_request.return_value = _response([{"id": 9}])
    result = FigshareTool(_config()).run(
        {"search_for": "volcanic ash", "page_size": 3, "page": 1}
    )

    assert mock_request.call_count == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None
    assert result["metadata"]["result_set_complete"] is True


def test_invalid_page_size_fails_before_network():
    result = FigshareTool(_config()).run({"search_for": "RNA", "page_size": 0})
    assert result["status"] == "error"
    assert "page_size" in result["error"]
