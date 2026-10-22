"""Regression tests for NCI R4R from/size pagination metadata."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/clinical_guidelines_tools.json"
    return next(
        item for item in json.loads(path.read_text())
        if item["name"] == "NCI_search_cancer_resources"
    )


def test_total_results_and_next_from_are_exposed(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "meta": {"totalResults": 136, "from": 3},
        "results": [{"id": 4}, {"id": 5}, {"id": 6}],
    }

    def request(session, method, url, **kwargs):
        requested.update(kwargs["params"])
        return response

    monkeypatch.setattr("tooluniverse.base_rest_tool.request_with_retry", request)
    result = BaseRESTTool(_config()).run({"q": "cancer", "size": 3, "from": 3})

    assert requested == {"q": "cancer", "size": 3, "from": 3}
    assert result["metadata"]["total_results"] == 136
    assert result["metadata"]["next_from"] == 6
    assert result["metadata"]["total_results_is_exact"] is True


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"q": "x", "size": 0}, "size"),
        ({"q": "x", "size": 51}, "size"),
        ({"q": "x", "from": -1}, "from"),
        ({"q": "x", "from": 1.5}, "from"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = BaseRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
