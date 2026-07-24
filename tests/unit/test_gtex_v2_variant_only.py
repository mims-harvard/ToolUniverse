"""Regression test: GTEx single-tissue eQTL variant-only query must not crash.

Previously, run() injected gencode_id=None when no gene symbol was given, and
_get_single_tissue_eqtls did `for gid in gencode_ids` -> "'NoneType' object is
not iterable". A variant-only query is valid (GTEx supports filtering by variantId
alone) and must work.
"""

from unittest.mock import MagicMock, patch

from tooluniverse.gtex_v2_tool import GTExV2Tool


def _tool():
    return GTExV2Tool(
        {
            "name": "GTEx_get_single_tissue_eqtls",
            "type": "GTExV2Tool",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"operation": "get_single_tissue_eqtls"},
        }
    )


def _resp(json_body, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    return r


def test_variant_only_query_does_not_crash():
    body = {"data": [{"variantId": "chr1_55054539_G_A_b38"}], "paging_info": {}}
    with patch("tooluniverse.gtex_v2_tool.requests.get", return_value=_resp(body)) as g:
        out = _tool().run({"operation": "get_single_tissue_eqtls", "variant_id": ["chr1_55054539_G_A_b38"]})
    assert out["status"] == "success"
    assert out["num_eqtls"] == 1
    # variantId forwarded, no gencodeId injected
    params = g.call_args.kwargs["params"]
    assert params["variantId"] == ["chr1_55054539_G_A_b38"]
    assert "gencodeId" not in params


def test_explicit_none_gencode_id_coerced():
    body = {"data": [], "paging_info": {}}
    with patch("tooluniverse.gtex_v2_tool.requests.get", return_value=_resp(body)):
        out = _tool().run({"operation": "get_single_tissue_eqtls", "gencode_id": None, "variant_id": ["chr1_55054539_G_A_b38"]})
    assert out["status"] == "success"


def test_gene_query_still_resolves_and_works():
    # gene_symbol path still injects + resolves gencode_id (regression guard).
    body = {"data": [{"variantId": "x"}], "paging_info": {}}
    with patch("tooluniverse.gtex_v2_tool.requests.get", return_value=_resp(body)) as g:
        with patch(
            "tooluniverse.gtex_v2_tool._resolve_gencode_id",
            side_effect=lambda x, *a, **k: "ENSG00000169174.11",
        ):
            out = _tool().run({"operation": "get_single_tissue_eqtls", "gene_symbol": "GBA"})
    assert out["status"] == "success"
    assert g.call_args.kwargs["params"]["gencodeId"] == ["ENSG00000169174.11"]
