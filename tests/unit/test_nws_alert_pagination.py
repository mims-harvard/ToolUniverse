"""Regression tests for NWS's unsupported limit and local alert pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/nws_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NWS_get_active_alerts"
    )


def test_limit_is_local_and_offset_reaches_later_alerts(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "type": "FeatureCollection",
        "title": "Current alerts",
        "features": [{"id": str(i)} for i in range(7)],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"area": "tx", "severity": "Severe", "limit": 2, "offset": 2}
    )

    assert requested == {"area": "TX", "severity": "Severe"}
    assert [item["id"] for item in result["data"]["features"]] == ["2", "3"]
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["upstream_limit_supported"] is False


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 501}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": 1.5}, "offset"),
    ],
)
def test_invalid_local_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
