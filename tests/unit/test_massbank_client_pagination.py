"""Regression tests for MassBank's client-side paging shim."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config(name):
    path = Path(__file__).parents[2] / "src/tooluniverse/data/massbank_tools.json"
    return next(item for item in json.loads(path.read_text()) if item["name"] == name)


def _response(records):
    response = Mock(status_code=200, text="")
    response.json.return_value = records
    return response


@pytest.mark.parametrize(
    "name,filter_args",
    [
        ("MassBank_search_by_compound", {"compound_name": "glucose"}),
        ("MassBank_search_by_formula", {"formula": "C6H12O6"}),
    ],
)
def test_filter_is_sent_but_limit_and_offset_are_local(
    monkeypatch, name, filter_args
):
    requested = {}

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return _response([{"accession": str(i)} for i in range(8)])

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config(name)).run(
        {**filter_args, "limit": 3, "offset": 3}
    )
    assert requested == filter_args
    assert [row["accession"] for row in result["data"]] == ["3", "4", "5"]
    assert result["metadata"]["total_results"] == 8
    assert result["metadata"]["next_offset"] == 6


def test_default_page_size_is_ten(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(
            [{"accession": str(i)} for i in range(12)]
        ),
    )
    result = BaseRESTTool(_config("MassBank_search_by_compound")).run(
        {"compound_name": "glucose"}
    )
    assert len(result["data"]) == 10
    assert result["metadata"]["next_offset"] == 10
