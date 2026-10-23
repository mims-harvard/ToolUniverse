"""Regression tests for PanelApp gene-symbol casing and next-page metadata."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/panelapp_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "PanelApp_search_genes"
    )


def test_lowercase_symbol_is_uppercased_and_next_link_is_exposed(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "count": 125,
        "next": "https://panelapp.example/api/v1/genes/TTN/?page=2",
        "results": [{"panel": {"id": 1}}],
    }

    def request(session, method, url, **kwargs):
        requested["url"] = url
        requested["params"] = kwargs["params"]
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"gene_symbol": "ttn", "page": 1})

    assert requested["url"].endswith("/genes/TTN/")
    assert requested["params"] == {"format": "json", "page": 1}
    assert result["metadata"]["total_results"] == 125
    assert result["metadata"]["next_page"] == 2
    assert result["metadata"]["has_more"] is True


@pytest.mark.parametrize("page", [0, -1, 1.5, True])
def test_invalid_page_is_explicit(page):
    result = BaseRESTTool(_config()).run({"gene_symbol": "TTN", "page": page})
    assert result["status"] == "error"
    assert result["parameter"] == "page"
