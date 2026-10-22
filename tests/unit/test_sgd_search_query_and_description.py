"""Regressions for SGD search query semantics and complete descriptions."""

from unittest.mock import Mock

import pytest

from tooluniverse.sgd_tool import SGDTool

pytestmark = pytest.mark.unit


def test_search_uses_q_and_keeps_full_description(monkeypatch):
    description = "Complete GAL4 literature abstract. " * 90
    response = Mock()
    response.json.return_value = {
        "total": {"value": 1033, "relation": "eq"},
        "results": [
            {
                "name": "GAL4 study",
                "category": "reference",
                "description": description,
                "href": "/reference/S000074673",
                "aliases": None,
            }
        ],
        "aggregations": [],
    }
    response.raise_for_status.return_value = None
    requested = {}

    def get(url, params, headers, timeout):
        requested.update(
            {"url": url, "params": params, "headers": headers, "timeout": timeout}
        )
        return response

    monkeypatch.setattr("tooluniverse.sgd_tool.requests.get", get)
    tool = SGDTool(
        {
            "name": "SGD_search",
            "fields": {"endpoint_type": "search"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run(
        {"query": "GAL4", "category": "reference", "limit": 1, "offset": 5}
    )

    assert requested["params"] == {
        "q": "GAL4",
        "category": "reference",
        "limit": 1,
        "offset": 5,
    }
    assert "query" not in requested["params"]
    assert len(description) > 200
    assert result["data"][0]["description"] == description
    assert result["data"][0]["description_length"] == len(description)
    assert result["metadata"]["total_results"] == 1033
    assert result["metadata"]["returned"] == 1
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
