"""Regression guard for Fix-R19C-1/3: DepMapTool's search and detail methods
had two related classes of bugs, both confirmed live --

1. DepMap_search_genes/DepMap_search_cell_lines scanned only the first 5
   pages (500 records) of a ~45,751-gene / ~2,266-model catalog looking for
   an exact/prefix match, or relied on filter[gene]/filter[model] query
   params that the Sanger Cell Model Passports API silently ignores
   (confirmed live: filtered and unfiltered requests return identical
   results). Any gene/cell-line not alphabetically within the first ~1%
   was always reported "not found" -- confirmed for KRAS, EGFR, TP53, A549.
   Both now binary-search the full, sorted (sort=symbol / sort=names)
   catalog instead.
2. DepMap_get_cell_line/DepMap_get_cell_lines read field names
   (model_name, tissue, cancer_type, gender, ethnicity, sample_site) that
   don't exist on the model resource's own `attributes` at all -- only
   `names` (a list) does. The real data lives on related sample/tissue/
   cancer_type/patient resources, reachable via the JSON:API `include`
   param. get_cell_line now resolves all fields correctly via `include`;
   get_cell_lines (a list endpoint, where per-row `include` isn't
   practical) fixes model_name and stops silently ignoring a tissue/
   cancer_type filter that has no effect server-side.
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


def _gene_item_model(name, model_id):
    return {"id": model_id, "attributes": {"names": [name]}}


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


def test_get_cell_line_resolves_tissue_cancer_type_gender_via_include(monkeypatch):
    tool = _tool("get_cell_line")

    body = {
        "data": {
            "id": "SIDM01774",
            "attributes": {
                "names": ["PK-59"],
                "growth_properties": "Adherent",
                "ploidy": None,
                "mutations_per_mb": 24.79,
            },
        },
        "included": [
            {"type": "sample", "id": "SIDS01659", "attributes": {
                "sample_site": "Liver", "tissue_status": "Metastasis", "age_at_sampling": None,
            }},
            {"type": "tissue", "id": "16", "attributes": {"name": "Pancreas"}},
            {"type": "cancer_type", "id": "25", "attributes": {"name": "Pancreatic Carcinoma"}},
            {"type": "patient", "id": "SIDP01578", "attributes": {"gender": "Unknown", "ethnicity": "Unknown"}},
            {"type": "model_msi_status", "id": "1", "attributes": {"msi_status": "No Data"}},
        ],
    }
    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["params"] = params
        return _resp(body)

    with patch("tooluniverse.depmap_tool.requests.get", side_effect=fake_get):
        result = tool.run({"model_id": "SIDM01774"})

    assert result["status"] == "success"
    data = result["data"]
    assert data["model_name"] == "PK-59"
    assert data["tissue"] == "Pancreas"
    assert data["cancer_type"] == "Pancreatic Carcinoma"
    assert data["gender"] == "Unknown"
    assert data["sample_site"] == "Liver"
    assert data["msi_status"] == "No Data"
    assert data["mutational_burden"] == 24.79
    assert "include" in captured["params"]


def test_get_cell_lines_fixes_model_name_and_warns_on_ignored_filter(monkeypatch):
    tool = _tool("get_cell_lines")

    body = {
        "meta": {"count": 2266},
        "data": [_gene_item_model("PK-59", "SIDM01774")],
    }

    with patch("tooluniverse.depmap_tool.requests.get", return_value=_resp(body)):
        result = tool.run({"tissue": "Lung", "page_size": 3})

    data = result["data"]
    assert data["cell_lines"][0]["model_name"] == "PK-59"
    assert data["total"] == 2266
    assert "no effect" in data["warning"]


def test_get_cell_lines_no_warning_without_filter(monkeypatch):
    tool = _tool("get_cell_lines")
    body = {"meta": {"count": 1}, "data": [_gene_item_model("A549", "SIDM00903")]}

    with patch("tooluniverse.depmap_tool.requests.get", return_value=_resp(body)):
        result = tool.run({})

    assert "warning" not in result["data"]


def test_search_cell_lines_binary_search_finds_match(monkeypatch):
    tool = _tool("search_cell_lines")

    def fake_get(url, params=None, **kwargs):
        page_num = params["page[number]"]
        if page_num == 1:
            return _resp(
                {
                    "meta": {"count": 2000},
                    "data": [_gene_item_model("1181N1", "SIDM1"), _gene_item_model("293T", "SIDM2")],
                }
            )
        return _resp({"data": [_gene_item_model("A549", "SIDM00903")]})

    with patch("tooluniverse.depmap_tool.requests.get", side_effect=fake_get):
        result = tool.run({"query": "A549"})

    assert result["status"] == "success"
    names = [c["model_name"] for c in result["data"]["cell_lines"]]
    assert "A549" in names
