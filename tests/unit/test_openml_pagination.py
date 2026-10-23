"""Regression tests for OpenML path-based offset pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/openml_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "OpenML_search_datasets"
    )


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = {"data": {"dataset": records}}
    return response


def test_limit_and_offset_are_embedded_in_path(monkeypatch):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update({"url": url, "params": kwargs["params"]})
        return _response([{"did": 4}, {"did": 5}, {"did": 6}])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"limit": 3, "offset": 3})
    assert requested["url"].endswith("/limit/3/offset/3")
    assert requested["params"] == {}
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["total_results"] is None


def test_short_page_establishes_exact_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"did": 7}]),
    )
    metadata = BaseRESTTool(_config()).run({"limit": 3, "offset": 6})["metadata"]
    assert metadata["has_more"] is False
    assert metadata["total_results"] == 7
    assert metadata["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"limit": 0}, "limit"),
        ({"limit": 10001}, "limit"),
        ({"limit": True}, "limit"),
        ({"offset": -1}, "offset"),
        ({"offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
