import json
from unittest.mock import Mock, patch

from tooluniverse.zenodo_tool import ZenodoRESTTool


def _config():
    with open("src/tooluniverse/data/zenodo_tools.json") as handle:
        return next(
            item
            for item in json.load(handle)
            if item["name"] == "Zenodo_search_records"
        )


def _response(ids, total, next_link=True):
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "hits": {"hits": [{"id": item} for item in ids], "total": total},
        "links": {"next": "https://example.test/page/next"} if next_link else {},
    }
    response.text = ""
    return response


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_search_forwards_page_and_reports_exact_total(mock_request):
    mock_request.return_value = _response([4, 5, 6], 3418)
    result = ZenodoRESTTool(_config()).run({"query": "CRISPR", "limit": 3, "page": 2})

    params = mock_request.call_args.kwargs["params"]
    assert params["q"] == "CRISPR"
    assert params["size"] == 3
    assert params["page"] == 2
    assert result["metadata"] == {
        "page": 2,
        "limit": 3,
        "returned": 3,
        "total_results": 3418,
        "total_results_is_exact": True,
        "has_more": True,
        "next_page": 3,
        "result_set_complete": False,
    }


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_exact_last_page_clears_navigation(mock_request):
    mock_request.return_value = _response([10], 10, next_link=False)
    result = ZenodoRESTTool(_config()).run({"query": "rare", "limit": 3, "page": 4})
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_page"] is None


def test_invalid_page_is_rejected_before_network():
    result = ZenodoRESTTool(_config()).run({"query": "x", "page": 0})
    assert result["status"] == "error"
    assert result["parameter"] == "page"
