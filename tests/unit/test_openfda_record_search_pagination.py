import json
from unittest.mock import Mock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.openfda_tool import OpenFDADrugEventsTool


def _config(name):
    with open("src/tooluniverse/data/openfda_tools.json") as handle:
        return next(item for item in json.load(handle) if item["name"] == name)


def _response(ids, total, skip, limit):
    response = Mock()
    response.status_code = 200
    response.text = ""
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {
        "meta": {"results": {"skip": skip, "limit": limit, "total": total}},
        "results": [{"id": item} for item in ids],
    }
    return response


def _tool(name):
    cls = (
        OpenFDADrugEventsTool if name == "OpenFDA_search_drug_events" else BaseRESTTool
    )
    return cls(_config(name))


@pytest.mark.parametrize(
    "name",
    [
        "OpenFDA_search_drug_labels",
        "OpenFDA_search_drug_ndc",
        "OpenFDA_search_device_510k",
        "OpenFDA_search_drug_shortages",
        "OpenFDA_search_device_adverse_events",
        "OpenFDA_search_device_recalls",
        "OpenFDA_search_food_adverse_events",
        "OpenFDA_search_animalvet_adverse_events",
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_record_search_forwards_skip_and_exposes_exact_navigation(mock_request, name):
    mock_request.return_value = _response([3, 4], 439, 2, 2)
    result = BaseRESTTool(_config(name)).run(
        {"search": "field:value", "limit": 2, "skip": 2}
    )

    params = mock_request.call_args.kwargs["params"]
    assert params["limit"] == 2
    assert params["skip"] == 2
    assert result["metadata"] == {
        "returned": 2,
        "total_results": 439,
        "total_results_is_exact": True,
        "accessible_results": 439,
        "upstream_truncated": False,
        "skip": 2,
        "limit": 2,
        "has_more": True,
        "next_skip": 4,
        "truncated": True,
        "result_set_complete": False,
        "warning": None,
    }


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_large_openfda_match_set_discloses_unreachable_tail(mock_request):
    mock_request.return_value = _response(list(range(100)), 30000, 25000, 100)
    result = BaseRESTTool(_config("OpenFDA_search_drug_labels")).run(
        {"search": "broad:true", "limit": 100, "skip": 25000}
    )

    assert result["metadata"]["accessible_results"] == 25100
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_skip"] is None
    assert "Refine" in result["metadata"]["warning"]


@pytest.mark.parametrize(
    "arguments,parameter", [({"limit": 0}, "limit"), ({"skip": 25001}, "skip")]
)
def test_invalid_openfda_paging_is_rejected(arguments, parameter):
    result = BaseRESTTool(_config("OpenFDA_search_drug_labels")).run(
        {"search": "x", **arguments}
    )
    assert result["status"] == "error"
    assert result["parameter"] == parameter


@pytest.mark.parametrize(
    "name",
    [
        "OpenFDA_search_drug_shortages",
        "OpenFDA_search_device_adverse_events",
        "OpenFDA_search_device_recalls",
        "OpenFDA_search_food_adverse_events",
        "OpenFDA_search_animalvet_adverse_events",
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_newer_openfda_searches_use_advertised_default_page(mock_request, name):
    mock_request.return_value = _response(list(range(5)), 12, 0, 5)
    result = BaseRESTTool(_config(name)).run({"search": "field:value"})

    assert mock_request.call_args.kwargs["params"]["limit"] == 5
    assert mock_request.call_args.kwargs["params"]["skip"] == 0
    assert result["metadata"]["next_skip"] == 5


@pytest.mark.parametrize(
    "name",
    [
        "OpenFDA_search_drug_events",
        "OpenFDA_search_drug_enforcement",
        "OpenFDA_search_device_enforcement",
        "OpenFDA_search_food_enforcement",
    ],
)
@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_mixed_search_record_mode_supports_skip(mock_request, name):
    mock_request.return_value = _response([3, 4], 2500, 2, 2)
    result = _tool(name).run({"search": "status:Ongoing", "limit": 2, "skip": 2})
    assert mock_request.call_args.kwargs["params"]["skip"] == 2
    assert result["metadata"]["next_skip"] == 4
    assert result["metadata"]["total_results"] == 2500


@patch("tooluniverse.base_rest_tool.request_with_retry")
def test_count_mode_omits_skip_and_discloses_term_limit(mock_request):
    response = Mock()
    response.status_code = 200
    response.text = ""
    response.headers = {"content-type": "application/json"}
    response.json.return_value = {
        "meta": {"last_updated": "2026-08-05"},
        "results": [
            {"term": "Class II", "count": 100},
            {"term": "Class I", "count": 10},
        ],
    }
    mock_request.return_value = response
    result = _tool("OpenFDA_search_drug_enforcement").run(
        {
            "search": "status:Ongoing",
            "count": "classification.exact",
            "limit": 2,
            "skip": 0,
        }
    )

    params = mock_request.call_args.kwargs["params"]
    assert "skip" not in params
    assert result["metadata"]["mode"] == "count_aggregation"
    assert result["metadata"]["returned_terms"] == 2
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["next_skip"] is None


def test_count_mode_rejects_nonzero_skip_before_network():
    result = _tool("OpenFDA_search_food_enforcement").run(
        {"count": "classification.exact", "limit": 2, "skip": 2}
    )
    assert result["status"] == "error"
    assert result["parameter"] == "skip"
