"""Regression tests for NASA/JPL CAD limit-from pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/nasa_sbdb_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NASASBDB_close_approaches"
    )


def test_offset_maps_to_limit_from_and_total_drives_next_offset(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "signature": {"version": "1.5", "source": "NASA/JPL CAD"},
        "count": 3,
        "total": 1795,
        "fields": ["des", "cd"],
        "data": [["a", "date1"], ["b", "date2"], ["c", "date3"]],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"date-min": "2025-01-01", "limit": 3, "offset": 3}
    )

    assert requested == {
        "date-min": "2025-01-01",
        "limit": 3,
        "limit-from": 3,
        "sort": "date",
    }
    assert result["metadata"]["total_results"] == 1795
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 10001}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
