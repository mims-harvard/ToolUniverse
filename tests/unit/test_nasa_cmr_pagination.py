"""Regression tests for NASA CMR page_num and CMR-Hits pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/nasa_cmr_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(records, hits="8"):
    response = Mock(status_code=200, text="")
    response.json.return_value = {"feed": {"entry": records}}
    response.headers = {"CMR-Hits": hits}
    return response


@pytest.mark.parametrize(
    "name,args",
    [
        ("NASACMR_search_collections", {"keyword": "ocean"}),
        ("NASACMR_search_granules", {"short_name": "MODIS"}),
    ],
)
def test_page_maps_to_page_num_and_header_total_drives_next(
    monkeypatch, name, args
):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"id": "4"}, {"id": "5"}, {"id": "6"}])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run(
        {**args, "page_size": 3, "page": 2}
    )
    assert requested["page_size"] == 3
    assert requested["page_num"] == 2
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_page"] == 3


def test_last_page_stops_at_exact_header_total(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response([{"id": "7"}, {"id": "8"}]),
    )
    metadata = BaseRESTTool(_config("NASACMR_search_collections")).run(
        {"keyword": "ocean", "page_size": 3, "page": 3}
    )["metadata"]
    assert metadata["has_more"] is False
    assert metadata["next_page"] is None
    assert metadata["total_results"] == 8


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"keyword": "x", "page_size": 0}, "page_size"),
        ({"keyword": "x", "page_size": 2001}, "page_size"),
        ({"keyword": "x", "page_size": True}, "page_size"),
        ({"keyword": "x", "page": 0}, "page"),
        ({"keyword": "x", "page": 1.5}, "page"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config("NASACMR_search_collections")).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
