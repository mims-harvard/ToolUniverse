"""Regression tests for ArtIC ranked-catalog pagination semantics."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/artic_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "ArtIC_search_artworks"
    )


def test_page_is_forwarded_and_ranked_total_is_not_called_exact_matches(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "preference": None,
        "pagination": {
            "total": 132681,
            "limit": 3,
            "offset": 3,
            "total_pages": 44227,
            "current_page": 2,
        },
        "data": [{"id": 4}, {"id": 5}, {"id": 6}],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"q": "monet", "limit": 3, "page": 2})

    assert requested == {"q": "monet", "limit": 3, "page": 2}
    assert result["metadata"]["next_page"] == 3
    assert result["metadata"]["total_results"] == 132681
    assert result["metadata"]["total_count_scope"] == (
        "ranked_catalog_candidates_not_exact_text_matches"
    )
    assert "not a count of exact keyword matches" in result["metadata"]["warning"]


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "monet", "limit": 0}, "limit"),
        ({"q": "monet", "limit": 101}, "limit"),
        ({"q": "monet", "page": 0}, "page"),
        ({"q": "monet", "page": 1.5}, "page"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
