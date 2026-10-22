"""Regression tests for recoverable OpenCitations client-side pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/opencitations_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "OpenCitations_get_citations"
    )


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


def test_offset_and_limit_are_local_and_later_records_are_reachable(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"oci": str(i)} for i in range(8)])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"doi": "10.1000/example", "limit": 3, "offset": 3}
    )
    assert requested == {}
    assert [row["oci"] for row in result["data"]] == ["3", "4", "5"]
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["upstream_supports_pagination"] is False


def test_final_page_and_overshoot_are_safe(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"oci": str(i)} for i in range(5)]),
    )
    tool = BaseRESTTool(_config())
    final = tool.run({"doi": "10.1000/example", "limit": 3, "offset": 3})
    assert len(final["data"]) == 2
    assert final["metadata"]["has_more"] is False
    assert final["metadata"]["total_results"] == 5
    over = tool.run({"doi": "10.1000/example", "limit": 3, "offset": 9})
    assert over["data"] == []
    assert over["metadata"]["next_offset"] is None


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"doi": "x", "limit": 0}, "limit"),
        ({"doi": "x", "limit": True}, "limit"),
        ({"doi": "x", "offset": -1}, "offset"),
        ({"doi": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
