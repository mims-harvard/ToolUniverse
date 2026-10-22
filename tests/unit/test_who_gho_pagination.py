"""Regression tests for WHO GHO OData skip/count pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _configs():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/who_gho_tools.json"
    wanted = {"WHOGHO_search_indicators", "WHOGHO_get_indicator_data"}
    return {item["name"]: item for item in json.loads(path.read_text()) if item["name"] in wanted}


@pytest.mark.parametrize(
    "name,arguments,expected_order",
    [
        (
            "WHOGHO_search_indicators",
            {"filter": "contains(IndicatorName,'mortality')", "top": 3, "skip": 3},
            "IndicatorCode asc",
        ),
        (
            "WHOGHO_get_indicator_data",
            {"indicator_code": "WHOSIS_000001", "top": 3, "skip": 3},
            "SpatialDim asc,TimeDim asc,Dim1 asc,Dim2 asc,Dim3 asc",
        ),
    ],
)
def test_skip_count_and_stable_order_are_forwarded(
    monkeypatch, name, arguments, expected_order
):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "@odata.count": 31,
        "value": [{"IndicatorCode": "a"}, {"IndicatorCode": "b"}, {"IndicatorCode": "c"}],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_configs()[name]).run(arguments)
    assert requested["$skip"] == 3
    assert requested["$count"] == "true"
    assert requested["$orderby"] == expected_order
    assert result["metadata"]["total_results"] == 31
    assert result["metadata"]["next_skip"] == 6


@pytest.mark.parametrize(
    "name,arguments,parameter",
    [
        ("WHOGHO_search_indicators", {"top": 101}, "top"),
        ("WHOGHO_get_indicator_data", {"indicator_code": "x", "top": 1001}, "top"),
        ("WHOGHO_search_indicators", {"skip": -1}, "skip"),
        ("WHOGHO_get_indicator_data", {"indicator_code": "x", "skip": 1.5}, "skip"),
    ],
)
def test_invalid_pagination_is_explicit(name, arguments, parameter):
    result = BaseRESTTool(_configs()[name]).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
