import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool


def config():
    with open("src/tooluniverse/data/marine_regions_tools.json") as handle:
        return json.load(handle)[0]


def response(records):
    result = Mock(status_code=200, text="", headers={"content-type": "application/json"})
    result.json.return_value = records
    return result


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_marine_regions_forwards_official_query_parameters_and_looks_ahead(request):
    first = [{"MRGID": i} for i in range(100)]
    request.side_effect = [response(first), response([{"MRGID": 100}])]
    result = BaseRESTTool(config()).run(
        {"name": "Sea", "like": True, "fuzzy": False, "offset": 0}
    )

    assert "/Sea/" in request.call_args_list[0].args[2]
    assert "/like/" not in request.call_args_list[0].args[2]
    params = request.call_args_list[0].kwargs["params"]
    assert params == {"count": 100, "like": True, "fuzzy": False, "offset": 0}
    probe = request.call_args_list[1].kwargs["params"]
    assert probe["offset"] == 100
    assert probe["count"] == 1
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 100
    assert result["metadata"]["matches_lower_bound"] == 101


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_marine_regions_short_page_exposes_exact_terminal_total_without_probe(request):
    request.return_value = response([{"MRGID": i} for i in range(17)])
    result = BaseRESTTool(config()).run({"name": "specific", "offset": 100})

    assert request.call_count == 1
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["total_results"] == 117
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["metadata"]["result_set_complete"] is False


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
        ({"like": "true"}, "like"),
        ({"fuzzy": 0}, "fuzzy"),
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_marine_regions_rejects_values_the_upstream_silently_ignores(
    request, arguments, parameter
):
    result = BaseRESTTool(config()).run({"name": "Sea", **arguments})
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    request.assert_not_called()
