"""Regression tests for USGS FDSN offset pagination and exact count lookup."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/usgs_earthquake_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "USGS_query_earthquakes"
    )


def _response(status, data=None, text=""):
    response = Mock(status_code=status, text=text)
    if data is not None:
        response.json.return_value = data
    return response


def test_offset_and_exact_count_are_exposed(monkeypatch):
    requested = []
    count = _response(200, text="99")
    query = _response(
        200,
        data={
            "type": "FeatureCollection",
            "metadata": {"limit": 3, "offset": 4},
            "features": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
        },
    )

    def request(session, method, url, **kwargs):
        requested.append((url, kwargs["params"]))
        return count if url.endswith("/count") else query

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {
            "starttime": "2024-01-01",
            "endtime": "2024-12-31",
            "minmagnitude": 6,
            "limit": 3,
            "offset": 4,
        }
    )

    assert requested[0][1] == {
        "starttime": "2024-01-01",
        "endtime": "2024-12-31",
        "minmagnitude": 6,
    }
    assert requested[1][1]["offset"] == 4
    assert requested[1][1]["orderby"] == "time"
    assert result["metadata"]["total_results"] == 99
    assert result["metadata"]["next_offset"] == 7
    assert result["metadata"]["offset_base"] == 1


def test_count_failure_falls_back_without_false_total(monkeypatch):
    count = _response(503, text="unavailable")
    query = _response(
        200,
        data={
            "type": "FeatureCollection",
            "metadata": {},
            "features": [{"id": "a"}, {"id": "b"}],
        },
    )
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda session, method, url, **kwargs: (
            count if url.endswith("/count") else query
        ),
    )
    result = BaseRESTTool(_config()).run({"limit": 2, "offset": 1})
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["total_results_is_exact"] is False
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["count_endpoint_error"] == "HTTP 503"


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 20001}, "limit"),
        ({"offset": 0}, "offset"),
        ({"offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
