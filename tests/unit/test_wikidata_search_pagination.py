"""Regression tests for Wikidata entity-search continuation."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/wikidata_entity_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "Wikidata_search_entities"
    )


def test_continue_is_forwarded_and_next_cursor_is_exposed(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "searchinfo": {"search": "TP53"},
        "search": [{"id": "Q4"}, {"id": "Q5"}, {"id": "Q6"}],
        "search-continue": 6,
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run(
        {"search": "TP53", "language": "en", "limit": 3, "continue": 3}
    )

    assert requested["continue"] == 3
    assert requested["limit"] == 3
    assert result["metadata"]["next_continue"] == 6
    assert result["metadata"]["total_results"] is None
    assert result["metadata"]["matches_lower_bound"] == 7


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"search": "x", "limit": 0}, "limit"),
        ({"search": "x", "limit": 51}, "limit"),
        ({"search": "x", "continue": -1}, "continue"),
        ({"search": "x", "continue": 1.5}, "continue"),
    ],
)
def test_invalid_continuation_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
