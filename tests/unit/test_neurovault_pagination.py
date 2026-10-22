import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


NAMES = [
    "NeuroVault_list_collections",
    "NeuroVault_list_collection_images",
    "NeuroVault_list_atlases",
]


def config(name):
    with open("src/tooluniverse/data/neurovault_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def response(payload):
    result = Mock(
        status_code=200, text="", headers={"content-type": "application/json"}
    )
    result.json.return_value = payload
    return result


@pytest.mark.parametrize("name", NAMES)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_neurovault_lists_expose_exact_limit_offset_navigation(request, name):
    request.return_value = response(
        {
            "count": 48,
            "next": "http://neurovault.org/api/items/?limit=2&offset=4",
            "previous": "http://neurovault.org/api/items/?limit=2",
            "results": [{"id": 3}, {"id": 4}],
        }
    )
    arguments = {"limit": 2, "offset": 2}
    if name == "NeuroVault_list_collection_images":
        arguments["collection_id"] = 457
    result = BaseRESTTool(config(name)).run(arguments)

    assert result["count"] == 2
    assert result["metadata"]["total_results"] == 48
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["pagination_scope"].startswith("django_rest_framework")
    assert request.call_args.kwargs["params"]["limit"] == 2
    assert request.call_args.kwargs["params"]["offset"] == 2


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_neurovault_terminal_page_is_marked_complete_when_first_page_contains_all(
    request,
):
    request.return_value = response(
        {"count": 2, "next": None, "previous": None, "results": [{"id": 1}, {"id": 2}]}
    )
    result = BaseRESTTool(config("NeuroVault_list_atlases")).run({"limit": 10})

    assert result["metadata"]["offset"] == 0
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["result_set_complete"] is True


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": -1}, "limit"),
        ({"limit": 1001}, "limit"),
        ({"limit": True}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_neurovault_rejects_values_upstream_silently_coerces(
    request, arguments, parameter
):
    result = BaseRESTTool(config("NeuroVault_list_collections")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()
