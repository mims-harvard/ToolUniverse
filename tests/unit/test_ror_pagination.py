"""Regression tests for ROR v2's fixed-size page pagination."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/ror_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "ROR_search_organizations"
    )


def test_page_is_forwarded_and_fixed_page_size_is_explicit(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "number_of_results": 1151,
        "items": [{"id": f"https://ror.org/{i}"} for i in range(20)],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"query": "cancer", "page": 2})

    assert requested == {"query": "cancer", "page": 2}
    assert result["metadata"]["total_results"] == 1151
    assert result["metadata"]["page_size"] == 20
    assert result["metadata"]["page_size_fixed_by_upstream"] is True
    assert result["metadata"]["next_page"] == 3


def test_http_200_error_envelope_is_not_reported_as_success(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = {"errors": ["query parameter 'page_size' is illegal"]}
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run({"query": "cancer", "page": 1})
    assert result["status"] == "error"
    assert "ROR rejected" in result["error"]


@pytest.mark.parametrize("page", [0, -1, 1.5, True])
def test_invalid_page_is_explicit(page):
    result = BaseRESTTool(_config()).run({"query": "cancer", "page": page})
    assert result["status"] == "error"
    assert result["parameter"] == "page"
