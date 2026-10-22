"""Regression tests for GTDB search size and page semantics."""

from unittest.mock import Mock

import pytest

from tooluniverse.gtdb_tool import GTDBTool

pytestmark = pytest.mark.unit


def _tool():
    return GTDBTool({"name": "gtdb_test", "parameter": {}})


def _response(payload):
    response = Mock(status_code=200, headers={})
    response.json.return_value = payload
    return response


def test_genome_page_size_above_old_cap_is_forwarded(monkeypatch):
    tool = _tool()
    requested = {}

    def get(url, params, timeout):
        requested.update(params)
        return _response(
            {"rows": [{"gid": str(i)} for i in range(101)], "totalRows": 250}
        )

    monkeypatch.setattr(tool.session, "get", get)
    result = tool.run(
        {
            "operation": "search_genomes",
            "query": "Escherichia",
            "page": 2,
            "items_per_page": 101,
        }
    )
    assert requested["page"] == 2
    assert requested["itemsPerPage"] == 101
    assert result["metadata"]["total_pages"] == 3
    assert result["metadata"]["next_page"] == 3


def test_taxon_limit_hit_is_qualified_as_potentially_incomplete(monkeypatch):
    tool = _tool()
    monkeypatch.setattr(
        tool.session,
        "get",
        lambda *args, **kwargs: _response(
            {"matches": [f"g__Taxon{i}" for i in range(100)]}
        ),
    )
    data = tool.run({"operation": "search_taxon", "query": "a", "limit": 100})["data"]
    assert data["possible_more"] is True
    assert data["complete_known"] is False
    assert data["limit_scope"] == "per_rank"
    assert data["rank_counts"] == {"g": 100}
    assert data["capped_ranks"] == ["g"]
    assert data["pagination_supported"] is False
    assert "narrow the query" in data["warning"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"operation": "search_genomes", "query": "x", "page": 0},
        {"operation": "search_genomes", "query": "x", "items_per_page": 1001},
        {"operation": "search_genomes", "query": "x", "items_per_page": True},
        {"operation": "search_taxon", "query": "x", "limit": 101},
        {"operation": "search_taxon", "query": "x", "limit": 0},
    ],
)
def test_invalid_pagination_is_explicit(arguments):
    result = _tool().run(arguments)
    assert result["status"] == "error"
