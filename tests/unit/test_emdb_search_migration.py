"""Regressions for EMDB search migration to the working EBI Search domain."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from tooluniverse.emdb_tool import EMDBRESTTool

pytestmark = pytest.mark.unit


def _config():
    path = Path(__file__).parents[2] / "src/tooluniverse/data/emdb_tools.json"
    return next(
        item
        for item in json.loads(path.read_text())
        if item["name"] == "EMDB_search_structures"
    )


def test_search_uses_ebi_domain_and_start_metadata(monkeypatch):
    requested = {}
    response = Mock(status_code=200, text="")
    response.json.return_value = {
        "hitCount": 3040,
        "entries": [
            {"id": "EMD-4", "source": "emdb"},
            {"id": "EMD-5", "source": "emdb"},
            {"id": "EMD-6", "source": "emdb"},
        ],
        "facets": [],
    }

    def request(session, method, url, **kwargs):
        requested["url"] = url
        requested["params"] = kwargs["params"]
        return response

    monkeypatch.setattr("tooluniverse.emdb_tool.request_with_retry", request)
    result = EMDBRESTTool(_config()).run({"query": "ribosome", "rows": 3, "start": 3})

    assert requested["url"] == "https://www.ebi.ac.uk/ebisearch/ws/rest/emdb"
    assert requested["params"]["query"] == "ribosome"
    assert requested["params"]["size"] == 3
    assert requested["params"]["start"] == 3
    assert result["metadata"]["total_results"] == 3040
    assert result["metadata"]["next_start"] == 6


@pytest.mark.parametrize(
    "arguments, parameter",
    [
        ({"query": "x", "rows": 0}, "rows"),
        ({"query": "x", "rows": 101}, "rows"),
        ({"query": "x", "start": -1}, "start"),
        ({"query": "x", "start": 1.5}, "start"),
    ],
)
def test_invalid_pagination_is_explicit(arguments, parameter):
    result = EMDBRESTTool(_config()).run(arguments)
    assert result["status"] == "error"
    assert result["parameter"] == parameter
