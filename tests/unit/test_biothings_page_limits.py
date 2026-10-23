"""Regression tests for BioThings page-size and result-window semantics."""

from unittest.mock import Mock

import pytest

from tooluniverse.mygene_tool import MyChemTool, MyGeneTool, MyVariantTool

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("tool_class", "name"),
    [
        (MyGeneTool, "MyGene_query_genes"),
        (MyVariantTool, "MyVariant_query_variants"),
        (MyChemTool, "MyChem_query_chemicals"),
    ],
)
def test_size_1000_is_forwarded_and_large_total_is_qualified(
    monkeypatch, tool_class, name
):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "total": 20_000,
        "hits": [{"_id": str(index)} for index in range(1000)],
    }
    requested = {}

    def get(url, params, timeout):
        requested.update({"url": url, "params": params, "timeout": timeout})
        return response

    monkeypatch.setattr("tooluniverse.mygene_tool.requests.get", get)
    result = tool_class({"name": name, "fields": {"operation": "query"}}).run(
        {"query": "kinase", "size": 1000, "offset": 9000}
    )

    assert requested["params"]["size"] == 1000
    assert requested["params"]["from"] == 9000
    assert result["metadata"]["total_results"] == 20_000
    assert result["metadata"]["accessible_results"] == 10_000
    assert result["metadata"]["has_more"] is False
    assert result["metadata"]["next_offset"] is None
    assert result["metadata"]["upstream_truncated"] is True
    assert result["metadata"]["all_results_reachable"] is False
    assert "Narrow or partition" in result["metadata"]["warning"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"query": "x", "size": 0},
        {"query": "x", "size": 1001},
        {"query": "x", "size": True},
        {"query": "x", "offset": -1},
        {"query": "x", "offset": 10_000},
        {"query": "x", "offset": 9999, "size": 2},
    ],
)
def test_invalid_or_unreachable_pages_are_explicit(arguments):
    result = MyGeneTool(
        {"name": "MyGene_query_genes", "fields": {"operation": "query"}}
    ).run(arguments)
    assert result["status"] == "error"
