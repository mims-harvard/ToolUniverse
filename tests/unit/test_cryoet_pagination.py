import json
from unittest.mock import patch

import pytest

from tooluniverse.cryoet_tool import CryoETTool


def config(name):
    with open("src/tooluniverse/data/cryoet_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


@pytest.mark.parametrize(
    "name,arguments,key",
    [
        ("CryoET_list_datasets", {}, "datasets"),
        ("CryoET_list_runs", {"dataset_id": 10053}, "runs"),
        ("CryoET_list_tomograms", {"run_id": 3430}, "tomograms"),
        ("CryoET_list_annotations", {"run_id": 3430}, "annotations"),
        ("CryoET_list_tiltseries", {}, "tiltseries"),
        ("CryoET_list_depositions", {}, "depositions"),
    ],
)
@patch("tooluniverse.cryoet_tool._gql")
def test_cryoet_lists_use_lookahead_and_expose_next_offset(gql, name, arguments, key):
    gql.return_value = {"data": {key: [{"id": 3}, {"id": 4}, {"id": 5}]}}
    result = CryoETTool(config(name)).run({**arguments, "limit": 2, "offset": 2})

    assert "limit: 3, offset: 2" in gql.call_args.args[0]
    assert result["data"]["count"] == 2
    assert [x["id"] for x in result["data"][key]] == [3, 4]
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["matches_lower_bound"] == 5
    assert result["metadata"]["total_results_is_exact"] is False


@patch("tooluniverse.cryoet_tool._gql")
def test_cryoet_short_first_page_is_explicitly_complete(gql):
    gql.return_value = {"data": {"datasets": [{"id": 1}]}}
    result = CryoETTool(config("CryoET_list_datasets")).run({"limit": 2})

    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert result["metadata"]["result_set_complete"] is True
    assert result["metadata"]["total_results"] == 1
    assert result["metadata"]["total_results_is_exact"] is True
    assert result["data"]["count"] == 1


@pytest.mark.parametrize(
    "arguments,parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 101}, "limit"),
        ({"limit": True}, "limit"),
        ({"limit": "2"}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": True}, "offset"),
    ],
)
@patch("tooluniverse.cryoet_tool._gql")
def test_cryoet_rejects_silently_coercible_paging_values(gql, arguments, parameter):
    result = CryoETTool(config("CryoET_list_datasets")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
    gql.assert_not_called()
