"""Regression guard for Fix-R19D-1: HPASearchGenesTool's underlying
search_download.php call does a broad full-text match with no server-side
limit param (confirmed live: a "limit" query param has no effect) -- a
short, valid gene symbol like "INS" returned 8,441 genes (1.4MB), many not
even containing the query as a substring. Exact gene-symbol matches are now
ranked first and the response is capped client-side (default 50, overridable
via max_results), with total_matches/truncated exposed for transparency.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.hpa_tool import HPASearchGenesTool

pytestmark = pytest.mark.unit


def _tool():
    return HPASearchGenesTool({"name": "HPA_search_genes_by_query", "fields": {}})


def _many_genes(query, count):
    genes = [
        {"Gene": query, "Gene synonym": "", "Ensembl": "ENSG00000254647"}
    ]
    genes += [
        {"Gene": f"NOISE{i}", "Gene synonym": "", "Ensembl": f"ENSG{i:011d}"}
        for i in range(count - 1)
    ]
    return genes


def test_exact_match_ranked_first_and_capped_at_default():
    tool = _tool()
    raw = _many_genes("INS", 8441)

    with patch.object(tool, "_make_api_request", return_value=raw):
        result = tool.run({"search_query": "INS"})

    data = result["data"]
    assert data["genes"][0]["gene_name"] == "INS"
    assert data["match_count"] == 50
    assert data["total_matches"] == 8441
    assert data["truncated"] is True
    assert data["has_more"] is True
    assert data["next_offset"] == 50


def test_max_results_override_returns_more():
    tool = _tool()
    raw = _many_genes("INS", 200)

    with patch.object(tool, "_make_api_request", return_value=raw):
        result = tool.run({"search_query": "INS", "max_results": 150})

    data = result["data"]
    assert data["match_count"] == 150
    assert data["truncated"] is True


def test_small_result_set_is_not_marked_truncated():
    tool = _tool()
    raw = _many_genes("BRCA1", 3)

    with patch.object(tool, "_make_api_request", return_value=raw):
        result = tool.run({"search_query": "BRCA1"})

    data = result["data"]
    assert data["total_matches"] == 3
    assert data["truncated"] is False
    assert data["genes"][0]["gene_name"] == "BRCA1"


def test_offset_exposes_later_matches_and_tail_terminates():
    tool = _tool()
    raw = _many_genes("INS", 5)

    with patch.object(tool, "_make_api_request", return_value=raw):
        middle = tool.run({"search_query": "INS", "max_results": 2, "offset": 2})
        tail = tool.run({"search_query": "INS", "max_results": 2, "offset": 4})

    assert [g["gene_name"] for g in middle["data"]["genes"]] == [
        "NOISE1",
        "NOISE2",
    ]
    assert middle["data"]["next_offset"] == 4
    assert [g["gene_name"] for g in tail["data"]["genes"]] == ["NOISE3"]
    assert tail["data"]["has_more"] is False
    assert tail["data"]["next_offset"] is None
