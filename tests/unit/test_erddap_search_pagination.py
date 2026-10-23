from unittest.mock import Mock, patch

from tooluniverse.base_rest_tool import BaseRESTTool


CONFIG = {
    "name": "ERDDAP_search_datasets",
    "type": "BaseRESTTool",
    "parameter": {
        "type": "object",
        "properties": {
            "searchFor": {"type": "string"},
            "itemsPerPage": {
                "type": "integer",
                "minimum": 1,
                "maximum": 100,
                "default": 10,
            },
            "page": {"type": "integer", "minimum": 1, "default": 1},
        },
        "required": ["searchFor"],
    },
    "fields": {
        "endpoint": "https://example.test/erddap/search/index.json",
        "params": {"page": 1, "itemsPerPage": 10},
        "pagination": "erddap_page",
    },
}


def response(status, *, text="", payload=None):
    result = Mock(status_code=status, text=text)
    result.json.return_value = payload
    return result


def test_erddap_page_reports_exact_html_count_and_continuation():
    count_response = response(200, text="<p>369 matching datasets</p>")
    json_response = response(
        200,
        payload={
            "table": {
                "columnNames": ["Dataset ID"],
                "columnTypes": ["String"],
                "columnUnits": [None],
                "rows": [["a"], ["b"], ["c"]],
            }
        },
    )
    tool = BaseRESTTool(CONFIG)

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        side_effect=[count_response, json_response],
    ) as request:
        result = tool.run({"searchFor": "SST", "itemsPerPage": 3, "page": 1})

    assert result["status"] == "success"
    assert result["count"] == 3
    assert result["metadata"] == {
        "returned": 3,
        "total_results": 369,
        "total_results_is_exact": True,
        "page": 1,
        "items_per_page": 3,
        "total_pages": 123,
        "has_more": True,
        "next_page": 2,
        "truncated": True,
        "result_set_complete": False,
        "pagination_scope": "erddap_html_count_json_page",
        "count_probe_error": None,
    }
    assert request.call_args_list[0].args[2].endswith("/index.html")
    assert request.call_args_list[1].args[2].endswith("/index.json")
    assert request.call_args_list[1].kwargs["params"]["itemsPerPage"] == 3


def test_erddap_no_matches_normalizes_upstream_404_to_exact_empty_success():
    count_response = response(404, text="Your query produced no matching results.")
    json_response = response(404, text="Your query produced no matching results.")
    tool = BaseRESTTool(CONFIG)

    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        side_effect=[count_response, json_response],
    ):
        result = tool.run({"searchFor": "definitely-not-real"})

    assert result["status"] == "success"
    assert result["data"]["table"]["rows"] == []
    assert result["metadata"]["total_results"] == 0
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["result_set_complete"] is True


def test_erddap_rejects_values_upstream_would_silently_coerce():
    tool = BaseRESTTool(CONFIG)

    with patch("tooluniverse.base_rest_tool.request_with_retry") as request:
        bad_page = tool.run({"searchFor": "SST", "page": 0})
        bad_size = tool.run({"searchFor": "SST", "itemsPerPage": 101})
        bool_page = tool.run({"searchFor": "SST", "page": True})

    assert bad_page["parameter"] == "page"
    assert bad_size["parameter"] == "itemsPerPage"
    assert bool_page["parameter"] == "page"
    request.assert_not_called()
