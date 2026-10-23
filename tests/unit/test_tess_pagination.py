"""Regression tests for ELIXIR TeSS one-based page pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/elixir_tess_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


@pytest.mark.parametrize(
    "name", ["ELIXIRTeSS_search_materials", "ELIXIRTeSS_search_events"]
)
def test_full_page_exposes_next_without_inventing_total(monkeypatch, name):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"id": 4}, {"id": 5}, {"id": 6}])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run(
        {"q": "RNA-seq", "page_size": 3, "page": 2}
    )
    assert requested["page_size"] == 3
    assert requested["page"] == 2
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["matches_lower_bound"] == 6


def test_short_final_page_establishes_exact_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"id": 7}]),
    )
    metadata = BaseRESTTool(_config("ELIXIRTeSS_search_events")).run(
        {"page_size": 3, "page": 3}
    )["metadata"]
    assert metadata["has_more"] is False
    assert metadata["total_results"] == 7
    assert metadata["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"page_size": 0}, "page_size"),
        ({"page_size": 101}, "page_size"),
        ({"page_size": True}, "page_size"),
        ({"page": 0}, "page"),
        ({"page": 1.5}, "page"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("ELIXIRTeSS_search_events")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
