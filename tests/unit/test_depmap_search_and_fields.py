"""Regression guard for Fix-R19C-1: DepMap_search_genes scanned only the
first 5 pages (500 records) of a ~45,751-gene catalog looking for an
exact/prefix match, or relied on filter[gene], a query param the Sanger
Cell Model Passports API silently ignores (confirmed live: filtered and
unfiltered requests return identical results). Any gene not alphabetically
within the first ~1% was always reported "not found" -- confirmed for
KRAS, EGFR, TP53. Now binary-searches the full, sorted (sort=symbol)
catalog instead.

DepMap_search_cell_lines/get_cell_line/get_cell_lines had a related but
distinct set of bugs, fixed and covered separately in
test_depmap_cell_line_lookup.py (Fix-R27A): those use the real
/search/models?q=... endpoint (discovered live) rather than a filter or a
binary search, and resolve tissue/cancer_type/gender/etc. via the JSON:API
`include` relationship graph.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.depmap_tool import DepMapTool

pytestmark = pytest.mark.unit


def _tool(operation):
    return DepMapTool({"name": "depmap_test", "fields": {"operation": operation}})


def _resp(json_body, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


def _gene_item(symbol, gene_id="SIDGxxxxx"):
    return {"id": gene_id, "attributes": {"symbol": symbol, "name": None, "hgnc_id": None}}


def test_search_genes_binary_search_finds_mid_alphabet_gene(monkeypatch):
    """KRAS-like case: target isn't on page 1, must be found via search."""
    tool = _tool("search_genes")

    # Simulate a full sorted 26-page catalog, one page per letter of the
    # alphabet (A on page 1, K on page 11, Z on page 26) -- large enough
    # that the original "scan up to 5 pages" bug would never reach K, and
    # that a truly-linear scan (not a real binary search) would take 11
    # requests instead of ~5 (log2(26)).
    letters = [chr(ord("A") + i) for i in range(26)]
    pages = {
        i + 1: [_gene_item(f"{letters[i]}AA1"), _gene_item(f"{letters[i]}ZZ9")]
        for i in range(26)
    }
    # Page 11 ('K') deliberately contains the exact target plus a prefix match.
    pages[11] = [_gene_item("KRAS"), _gene_item("KRASP1")]

    call_log = []

    def fake_get(url, params=None, **kwargs):
        page_num = params["page[number]"]
        call_log.append(page_num)
        if page_num == 1:
            # page_size in the implementation is 1000; 26000 -> 26 pages,
            # matching the 26-page mock catalog above.
            body = {"meta": {"count": 26000}, "data": pages[1]}
        else:
            body = {"data": pages[page_num]}
        return _resp(body)

    with patch("tooluniverse.depmap_tool.requests.get", side_effect=fake_get):
        result = tool.run({"query": "KRAS"})

    assert result["status"] == "success"
    symbols = [g["symbol"] for g in result["data"]["genes"]]
    assert "KRAS" in symbols
    assert "KRASP1" in symbols
    exact = [g for g in result["data"]["genes"] if g["exact_match"]]
    assert len(exact) == 1 and exact[0]["symbol"] == "KRAS"
    # Confirms it landed on the exact right page (11) via genuine binary
    # search, not a linear scan or a lucky guess.
    assert call_log[-1] == 11
    assert len(call_log) <= 8  # log2(26) ~= 5; generous upper bound


def test_search_genes_no_match_returns_empty_not_stale_page(monkeypatch):
    tool = _tool("search_genes")

    def fake_get(url, params=None, **kwargs):
        page_num = params["page[number]"]
        if page_num == 1:
            return _resp({"meta": {"count": 100}, "data": [_gene_item("AAAS")]})
        return _resp({"data": [_gene_item("ZZZ1")]})

    with patch("tooluniverse.depmap_tool.requests.get", side_effect=fake_get):
        result = tool.run({"query": "NOTAREALGENE"})

    assert result["status"] == "success"
    assert result["data"]["genes"] == []
    assert result["data"]["count"] == 0
