"""Regression tests for Anaconda search's silent 100-record default cap."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/anaconda_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "Anaconda_search_packages"
    )


def test_offset_and_one_record_lookahead(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = [{"full_name": f"owner/pkg{i}"} for i in range(4)]

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"name": "python", "limit": 3, "offset": 3})

    assert requested == {"name": "python", "limit": 4, "offset": 3}
    assert len(result["data"]) == 3
    assert result["metadata"]["next_offset"] == 6
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["matches_lower_bound"] == 7


def test_short_page_establishes_exact_total(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = [{"full_name": "owner/only"}]
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run({"name": "rare", "limit": 3, "offset": 6})
    assert result["metadata"]["total_results"] == 7
    assert result["metadata"]["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"name": "x", "limit": 0}, "limit"),
        ({"name": "x", "limit": 101}, "limit"),
        ({"name": "x", "offset": -1}, "offset"),
        ({"name": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
