"""Regression guard for Fix-R13B-1 and Fix-R13B-2.

Fix-R13B-1: WormBase_get_gene 500'd on a "WB:"-prefixed WBGene ID (e.g.
"WB:WBGene00006746", exactly what a sibling tool like Alliance_search_genes
returns for the same gene) because the old check `startswith("WBGENE")`
didn't strip the "WB:" CURIE prefix, so the colon-containing string was
interpolated straight into the WormBase REST URL.

Fix-R13B-2: WormBase's own /api/search endpoint with `category=gene` and
`species=...` params silently returns zero results for any real gene symbol
(confirmed live) -- Alliance no longer honours those params there. The
working endpoint is /api/search_autocomplete with just `q`, filtering gene
hits client-side by category and by the "WB:" curie prefix.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.wormbase_tool import _resolve_wbgene_id, _WBGENE_CACHE

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_cache():
    _WBGENE_CACHE.clear()
    yield
    _WBGENE_CACHE.clear()


def test_wb_prefixed_id_is_stripped_without_any_api_call(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("should not call the Alliance API for an already-resolved ID")

    monkeypatch.setattr("tooluniverse.wormbase_tool.requests.get", fail_if_called)

    assert _resolve_wbgene_id("WB:WBGene00006746") == "WBGene00006746"


def test_bare_wbgene_id_returned_unchanged():
    assert _resolve_wbgene_id("WBGene00006746") == "WBGene00006746"


def test_gene_symbol_resolves_via_autocomplete_endpoint(monkeypatch):
    captured = {}

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {
                "results": [
                    {"symbol": "unc-6", "curie": "WB:WBGene00006746", "category": "gene_search_result"},
                    {"symbol": "unc-60", "curie": "WB:WBGene00006794", "category": "gene_search_result"},
                    {"symbol": "unc-6", "curie": "MGI:1234", "category": "gene_search_result"},
                    {"symbol": "unc-6", "curie": "WB:WBGene00006746", "category": "disease_search_result"},
                ]
            }

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse()

    monkeypatch.setattr("tooluniverse.wormbase_tool.requests.get", fake_get)

    resolved = _resolve_wbgene_id("unc-6")

    assert resolved == "WBGene00006746"
    assert "search_autocomplete" in captured["url"]
    assert "category" not in captured["params"]
    assert "species" not in captured["params"]


def test_unresolvable_symbol_falls_back_to_original_input(monkeypatch):
    class _FakeResponse:
        status_code = 200

        def json(self):
            return {"results": []}

    monkeypatch.setattr(
        "tooluniverse.wormbase_tool.requests.get",
        lambda url, params=None, timeout=None: _FakeResponse(),
    )

    assert _resolve_wbgene_id("not-a-real-gene") == "not-a-real-gene"


def test_resolution_result_is_cached(monkeypatch):
    calls = []

    class _FakeResponse:
        status_code = 200

        def json(self):
            return {
                "results": [
                    {"symbol": "unc-6", "curie": "WB:WBGene00006746", "category": "gene_search_result"}
                ]
            }

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return _FakeResponse()

    monkeypatch.setattr("tooluniverse.wormbase_tool.requests.get", fake_get)

    assert _resolve_wbgene_id("unc-6") == "WBGene00006746"
    assert _resolve_wbgene_id("unc-6") == "WBGene00006746"
    assert len(calls) == 1
