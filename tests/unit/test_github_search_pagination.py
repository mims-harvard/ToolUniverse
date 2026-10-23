"""Regression tests for GitHub Search pagination and its 1,000-result cap."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/github_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "GitHub_search_repositories"
    )


def test_page_is_forwarded_and_1000_result_cap_is_explicit(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "total_count": 16092,
        "incomplete_results": False,
        "items": [{"id": 4}, {"id": 5}, {"id": 6}],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"q": "bioinformatics", "per_page": 3, "page": 2}
    )

    assert requested == {"q": "bioinformatics", "per_page": 3, "page": 2}
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["total_results"] == 16092
    assert result["metadata"]["accessible_results"] == 1000
    assert result["metadata"]["retrieval_capped"] is True
    assert "only the first 1000" in result["metadata"]["warning"]


def test_incomplete_results_are_not_reported_as_exact(monkeypatch):
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "total_count": 20,
        "incomplete_results": True,
        "items": [{"id": 1}],
    }
    monkeypatch.setattr(
        "tooluniverse.base_rest_tool.request_with_retry",
        lambda *args, **kwargs: response,
    )
    result = BaseRESTTool(_config()).run({"q": "x", "per_page": 1, "page": 1})
    assert result["metadata"]["total_results_is_exact"] is False
    assert result["metadata"]["upstream_incomplete_results"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "x", "per_page": 0}, "per_page"),
        ({"q": "x", "per_page": 101}, "per_page"),
        ({"q": "x", "page": 0}, "page"),
        ({"q": "x", "page": 11, "per_page": 100}, "page"),
    ],
)
def test_invalid_or_inaccessible_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
