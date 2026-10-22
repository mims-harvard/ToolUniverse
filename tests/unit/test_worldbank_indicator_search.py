"""Regressions for World Bank's ignored query and local indicator search."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/worldbank_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "WorldBank_search_indicators"
    )


def _response():
    records = [
        {"id": "GDP.1", "name": "Gross domestic product", "sourceNote": "GDP current USD"},
        {"id": "MORT.1", "name": "Child mortality", "sourceNote": "Deaths under five"},
        {"id": "GDP.2", "name": "GDP per capita", "sourceNote": "Income per person"},
        {"id": "LIFE.1", "name": "Life expectancy", "sourceNote": "Health"},
    ]
    response = Mock(status_code=200, text="")
    response.json.return_value = [
        {"page": 1, "pages": 1, "per_page": "32767", "total": 5},
        records,
    ]
    return response


def test_query_is_local_and_different_queries_produce_different_hits(monkeypatch):
    requested = []

    def request(session, method, url, **kwargs):
        requested.append(kwargs["params"])
        return _response()

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    tool = BaseRESTTool(_config())
    gdp = tool.run({"query": "GDP", "per_page": 1, "offset": 0})
    mortality = tool.run({"query": "mortality", "per_page": 1, "offset": 0})
    assert requested[0] == {"format": "json", "per_page": "32767", "page": "1"}
    assert requested[1] == requested[0]
    assert gdp["data"][1][0]["id"] == "GDP.1"
    assert mortality["data"][1][0]["id"] == "MORT.1"
    assert gdp["metadata"]["next_offset"] == 1
    assert gdp["metadata"]["upstream_catalog_omitted"] == 1
    assert gdp["metadata"]["total_results_is_exact"] is False


def test_second_local_page_reaches_later_match(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: _response(),
    )
    result = BaseRESTTool(_config()).run(
        {"query": "GDP", "per_page": 1, "offset": 1}
    )
    assert result["data"][1][0]["id"] == "GDP.2"
    assert result["metadata"]["has_more"] is False


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"query": "", "per_page": 10}, "query"),
        ({"query": "x", "per_page": 0}, "per_page"),
        ({"query": "x", "per_page": 1001}, "per_page"),
        ({"query": "x", "offset": -1}, "offset"),
        ({"query": "x", "offset": 1.5}, "offset"),
    ],
)
def test_invalid_search_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
