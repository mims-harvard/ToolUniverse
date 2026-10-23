"""Regression tests for EBI eQTL Catalogue start/size pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = (
        Path(__file__).parents[2] / "src/tooluniverse/data/broken_apis/eqtl_tools.json"
    )
    configs = json.loads(path.read_text())
    return next(item for item in configs if item["name"] == name)


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


@pytest.mark.parametrize("name", ["eQTL_list_datasets", "eQTL_get_associations"])
def test_start_is_forwarded_and_lookahead_is_hidden(monkeypatch, name):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"id": "a"}, {"id": "b"}, {"id": "lookahead"}])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    arguments = {"size": 2, "start": 4}
    if name == "eQTL_get_associations":
        arguments["dataset_id"] = "QTD000001"
    result = BaseRESTTool(_config(name)).run(arguments)

    assert requested["size"] == 3
    assert requested["start"] == 4
    assert [row["id"] for row in result["data"]] == ["a", "b"]
    assert result["count"] == 2
    assert result["metadata"] == {
        "returned": 2,
        "start": 4,
        "size": 2,
        "has_more": True,
        "next_start": 6,
        "total_results": None,
        "total_results_is_exact": False,
        "matches_lower_bound": 7,
        "truncated": True,
        "result_set_complete": False,
        "pagination_method": "one_record_lookahead",
    }


def test_final_page_exposes_exact_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"dataset_id": "QTD000003"}]),
    )
    result = BaseRESTTool(_config("eQTL_list_datasets")).run({"size": 2, "start": 2})
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["total_results"] == 3
    assert result["metadata"]["total_results_is_exact"] is True


def test_empty_overshoot_does_not_invent_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([]),
    )
    metadata = BaseRESTTool(_config("eQTL_list_datasets")).run(
        {"size": 2, "start": 10000}
    )["metadata"]
    assert metadata["total_results"] is None
    assert metadata["total_results_is_exact"] is False
    assert metadata["matches_lower_bound"] is None


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"size": 0}, "size"),
        ({"size": 1000}, "size"),
        ({"size": True}, "size"),
        ({"start": -1}, "start"),
        ({"start": 1.5}, "start"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("eQTL_list_datasets")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
