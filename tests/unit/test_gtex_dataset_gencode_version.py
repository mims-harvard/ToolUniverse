"""GTEx resolved every gene ID against GENCODE v26, whatever dataset was asked for.

Each GTEx dataset is annotated against a different GENCODE release and the API
only matches IDs carrying that release's version suffix (TP53 is
ENSG00000141510.16 in gtex_v8/v26 but .18 in gtex_v10/v39). The resolver
hardcoded ``gencodeVersion=v26``, so selecting ``dataset_id="gtex_v10"`` -- a
documented enum value -- sent v26 IDs to a v39 dataset and the API answered
HTTP 200 with an empty list. That surfaced as ``status: "success"`` with
``num_results: 0``, i.e. "this gene has no expression in V10" rather than an ID
mismatch. Confirmed live: median expression for TP53 in gtex_v10 returned 0
rows via the tool but 54 tissues via the API with the .18 ID, and ERAP2/Liver
eQTLs returned 0 via the tool but 250 via the API with the .17 ID.

The resolver also stripped and re-resolved any supplied version suffix, so a
caller who passed the correct v39 ID had it downgraded back to v26 -- there was
no workaround from the outside.
"""

from unittest.mock import patch

from tooluniverse.gtex_v2_tool import (
    DATASET_GENCODE_VERSION,
    GTExV2Tool,
    _resolve_gencode_id,
)

# gencodeVersion -> versioned ID, as returned by /reference/gene
_TP53_BY_VERSION = {
    "v19": "ENSG00000141510.11",
    "v26": "ENSG00000141510.16",
    "v39": "ENSG00000141510.18",
}


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _fake_reference_gene(url, params=None, timeout=None):
    """Stand in for GET /reference/gene, honouring the requested gencodeVersion."""
    version = (params or {}).get("gencodeVersion")
    return _FakeResponse({"data": [{"gencodeId": _TP53_BY_VERSION[version]}]})


def _make(operation):
    cfg = {
        "name": f"GTEx_{operation}",
        "type": "GTExV2Tool",
        "parameter": {
            "type": "object",
            "properties": {"operation": {"enum": [operation]}},
        },
    }
    return GTExV2Tool(cfg)


def test_dataset_gencode_map_matches_api_metadata():
    # Values reported by GTEx /metadata/dataset.
    assert DATASET_GENCODE_VERSION["gtex_v7"] == "v19"
    assert DATASET_GENCODE_VERSION["gtex_v8"] == "v26"
    assert DATASET_GENCODE_VERSION["gtex_v10"] == "v39"
    assert DATASET_GENCODE_VERSION["gtex_snrnaseq_pilot"] == "v26"


def test_resolver_uses_the_datasets_own_gencode_version():
    with patch("tooluniverse.gtex_v2_tool.requests.get", _fake_reference_gene):
        assert _resolve_gencode_id("TP53", "gtex_v8") == "ENSG00000141510.16"
        assert _resolve_gencode_id("TP53", "gtex_v10") == "ENSG00000141510.18"
        assert _resolve_gencode_id("TP53", "gtex_v7") == "ENSG00000141510.11"


def test_resolver_defaults_to_v26_for_unknown_dataset():
    with patch("tooluniverse.gtex_v2_tool.requests.get", _fake_reference_gene):
        assert _resolve_gencode_id("TP53", "some_future_dataset") == (
            "ENSG00000141510.16"
        )


def test_supplied_version_suffix_is_retargeted_not_preserved_blindly():
    # A v26 ID asked for against v10 must come back as the v10 ID, and vice
    # versa -- previously both directions collapsed to .16.
    with patch("tooluniverse.gtex_v2_tool.requests.get", _fake_reference_gene):
        assert (
            _resolve_gencode_id("ENSG00000141510.16", "gtex_v10")
            == "ENSG00000141510.18"
        )
        assert (
            _resolve_gencode_id("ENSG00000141510.18", "gtex_v8") == "ENSG00000141510.16"
        )


def test_median_expression_sends_v39_id_when_dataset_is_v10():
    tool = _make("get_median_gene_expression")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/reference/gene"):
            return _fake_reference_gene(url, params, timeout)
        captured["url"] = url
        captured["params"] = params
        return _FakeResponse({"medianGeneExpression": [{"median": 22.65}]})

    with patch("tooluniverse.gtex_v2_tool.requests.get", fake_get):
        res = tool.run(
            {"operation": "get_median_gene_expression", "gencode_id": "TP53",
             "dataset_id": "gtex_v10"}
        )

    assert res["status"] == "success"
    assert captured["params"]["gencodeId"] == ["ENSG00000141510.18"]
    assert captured["params"]["datasetId"] == "gtex_v10"
    assert res["num_results"] == 1


def test_median_expression_still_sends_v26_id_by_default():
    tool = _make("get_median_gene_expression")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/reference/gene"):
            return _fake_reference_gene(url, params, timeout)
        captured["params"] = params
        return _FakeResponse({"medianGeneExpression": []})

    with patch("tooluniverse.gtex_v2_tool.requests.get", fake_get):
        tool.run({"operation": "get_median_gene_expression", "gencode_id": "TP53"})

    assert captured["params"]["gencodeId"] == ["ENSG00000141510.16"]
    assert captured["params"]["datasetId"] == "gtex_v8"


def test_single_tissue_eqtl_resolves_against_requested_dataset():
    tool = _make("get_single_tissue_eqtls")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/reference/gene"):
            return _fake_reference_gene(url, params, timeout)
        captured["params"] = params
        return _FakeResponse({"data": []})

    with patch("tooluniverse.gtex_v2_tool.requests.get", fake_get):
        tool.run(
            {
                "operation": "get_single_tissue_eqtls",
                "gencode_id": ["TP53"],
                "tissue_site_detail_id": ["Liver"],
                "dataset_id": "gtex_v10",
            }
        )

    assert captured["params"]["gencodeId"] == ["ENSG00000141510.18"]


def test_single_nucleus_defaults_to_pilot_dataset_gencode_version():
    tool = _make("get_single_nucleus_expression")
    captured = {}

    def fake_get(url, params=None, timeout=None):
        if url.endswith("/reference/gene"):
            return _fake_reference_gene(url, params, timeout)
        captured["params"] = params
        return _FakeResponse({"data": []})

    with patch("tooluniverse.gtex_v2_tool.requests.get", fake_get):
        tool.run(
            {"operation": "get_single_nucleus_expression", "gencode_id": "TP53"}
        )

    # snRNA-seq pilot is GENCODE v26, so the .16 ID is the correct one here.
    assert captured["params"]["datasetId"] == "gtex_snrnaseq_pilot"
    assert captured["params"]["gencodeId"] == ["ENSG00000141510.16"]
