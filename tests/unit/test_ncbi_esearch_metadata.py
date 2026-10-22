"""Regression tests for normalized NCBI Gene ESearch pagination metadata."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/ncbi_gene_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "NCBIGene_search"
    )


def test_string_count_and_offsets_are_normalized(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "esearchresult": {
            "count": "2272",
            "retmax": "3",
            "retstart": "3",
            "idlist": ["7422", "2475", "3569"],
        }
    }
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run(
        {"term": "insulin", "retmax": 3, "retstart": 3}
    )
    assert result["metadata"]["total_results"] == 2272
    assert result["metadata"]["retstart"] == 3
    assert result["metadata"]["next_retstart"] == 6
    assert result["metadata"]["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"term": "x", "retmax": 0}, "retmax"),
        ({"term": "x", "retmax": 101}, "retmax"),
        ({"term": "x", "retstart": -1}, "retstart"),
        ({"term": "x", "retstart": 1.5}, "retstart"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
