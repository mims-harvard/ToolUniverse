"""Regression tests for Bioconductor r-universe skip pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/bioconductor_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "Bioconductor_search_packages"
    )


def _response(payload):
    response = Mock(status_code=200, text="")
    response.json.return_value = payload
    return response


def test_offset_maps_to_skip_and_exact_total_drives_next(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response(
            {"total": 8, "limit": 3, "skip": 3, "results": [{}, {}, {}]}
        )

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"q": "single cell", "limit": 3, "offset": 3}
    )
    assert requested == {"q": "single cell", "limit": 3, "skip": 3}
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "x", "limit": 0}, "limit"),
        ({"q": "x", "limit": 101}, "limit"),
        ({"q": "x", "limit": True}, "limit"),
        ({"q": "x", "offset": -1}, "offset"),
        ({"q": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
