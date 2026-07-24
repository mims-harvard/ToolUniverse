"""Unit tests for the variant-clinical depth tools.

Covers three new ToolUniverse tools that close confirmed, keyless capability
gaps. Each tool is exercised with a mocked HTTP layer for both the success
(parse) path and an error path. No network access is performed.

Tools under test:
  - VariantValidator_format_genomic_to_transcripts (BaseRESTTool config):
    projects a genomic variant onto every overlapping RefSeq transcript via the
    VariantFormatter endpoint (the standard endpoint rejects all-transcripts for
    genomic input).
  - GeneBe_classify_variants_batch (GeneBeTool batch branch): POSTs a JSON array
    of up to 1000 variants and returns the full per-variant ACMG output.
  - ClinGenAR_lookup_by_external_id (ClinGenARTool endpoint): reverse-resolves a
    dbSNP rsID or ClinVar variation id to the canonical allele (CA id).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.base_rest_tool import BaseRESTTool
from tooluniverse.clingen_ar_tool import ClinGenARTool
from tooluniverse.genebe_tool import GeneBeTool

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _fake_response(status_code=200, json_body=None, text=""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"content-type": "application/json"}
    resp.text = text if text else json.dumps(json_body or {})
    if json_body is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_body
    resp.raise_for_status.return_value = None
    return resp


# --------------------------------------------------------------------------- #
# VariantValidator_format_genomic_to_transcripts  (BaseRESTTool)
# --------------------------------------------------------------------------- #
_VF_CONFIG = {
    "name": "VariantValidator_format_genomic_to_transcripts",
    "type": "BaseRESTTool",
    "fields": {
        "endpoint": "https://rest.variantvalidator.org/VariantFormatter/variantformatter/{genome_build}/{variant_description}/refseq/all/False",
        "headers": {"Accept": "application/json"},
    },
    "parameter": {
        "type": "object",
        "properties": {
            "genome_build": {"type": "string", "default": "GRCh38"},
            "variant_description": {"type": "string"},
        },
        "required": ["variant_description"],
    },
}

_VF_BODY = {
    "NC_000017.11:g.50198002C>A": {
        "NC_000017.11:g.50198002C>A": {
            "g_hgvs": "NC_000017.11:g.50198002C>A",
            "genomic_variant_error": None,
            "hgvs_t_and_p": {
                "NM_000088.4": {
                    "gene_info": {"hgnc_id": "HGNC:2197", "symbol": "COL1A1"},
                    "p_hgvs_slc": "NP_000079.2:p.(G197C)",
                    "p_hgvs_tlc": "NP_000079.2:p.(Gly197Cys)",
                    "select_status": {"mane_select": True, "refseq_select": True},
                    "t_hgvs": "NM_000088.4:c.589G>T",
                    "transcript_variant_error": None,
                }
            },
            "p_vcf": "17:50198002:C:A",
            "selected_build": "GRCh38",
        },
        "errors": [],
        "flag": None,
    },
    "metadata": {"variantformatter_version": "4.0.0"},
}


def _vf_tool():
    return BaseRESTTool(_VF_CONFIG)


def test_variantformatter_url_encodes_genomic_path():
    """The g.HGVS path segment (with ':' and '>') must be URL-encoded so the
    request reaches VariantFormatter rather than 404'ing."""
    tool = _vf_tool()
    url = tool._build_url(
        {"genome_build": "GRCh38", "variant_description": "NC_000017.11:g.50198002C>A"}
    )
    assert "GRCh38" in url
    assert "%3A" in url  # ':' encoded
    assert "%3E" in url  # '>' encoded
    assert url.endswith("/refseq/all/False")


def test_variantformatter_parses_all_transcripts():
    """The per-transcript c./p. HGVS, gene info and MANE/RefSeq flags parse out."""
    tool = _vf_tool()
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=_fake_response(200, _VF_BODY),
    ):
        out = tool.run(
            {
                "genome_build": "GRCh38",
                "variant_description": "NC_000017.11:g.50198002C>A",
            }
        )
    assert out["status"] == "success"
    block = out["data"]["NC_000017.11:g.50198002C>A"]["NC_000017.11:g.50198002C>A"]
    tx = block["hgvs_t_and_p"]["NM_000088.4"]
    assert tx["t_hgvs"] == "NM_000088.4:c.589G>T"
    assert tx["p_hgvs_tlc"] == "NP_000079.2:p.(Gly197Cys)"
    assert tx["gene_info"]["symbol"] == "COL1A1"
    assert tx["select_status"]["mane_select"] is True
    assert block["p_vcf"] == "17:50198002:C:A"


def test_variantformatter_http_error_returns_error_status():
    """A non-2xx response is surfaced as status=error, never raised."""
    tool = _vf_tool()
    with patch(
        "tooluniverse.base_rest_tool.request_with_retry",
        return_value=_fake_response(404, json_body=None, text="not found"),
    ):
        out = tool.run({"genome_build": "GRCh38", "variant_description": "bogus"})
    assert out["status"] == "error"
    assert out.get("status_code") == 404


# --------------------------------------------------------------------------- #
# GeneBe_classify_variants_batch  (GeneBeTool batch branch)
# --------------------------------------------------------------------------- #
_GENEBE_BATCH_CONFIG = {
    "name": "GeneBe_classify_variants_batch",
    "type": "GeneBeTool",
    "parameter": {"type": "object", "properties": {}},
}

_GENEBE_BATCH_BODY = {
    "message": None,
    "variants": [
        {
            "chr": "7",
            "pos": 140753336,
            "ref": "A",
            "alt": "T",
            "acmg_classification": "Pathogenic",
            "acmg_score": 14,
            "acmg_criteria": "PS3,PM1,PM2,PM5,PP2,PP3_Moderate,PP5",
            "acmg_by_gene": [
                {
                    "gene_symbol": "BRAF",
                    "hgvs_c": "c.1799T>A",
                    "hgvs_p": "p.Val600Glu",
                    "verdict": "Pathogenic",
                    "score": 14,
                }
            ],
            "alphamissense_score": 0.9927,
        },
        {
            "chr": "22",
            "pos": 28695868,
            "ref": "AG",
            "alt": "A",
            "acmg_classification": "Pathogenic",
            "acmg_by_gene": [{"gene_symbol": "CHEK2"}],
        },
    ],
}


def _genebe_tool():
    return GeneBeTool(_GENEBE_BATCH_CONFIG)


def test_genebe_batch_parses_per_variant_acmg():
    """A batch POST returns full ACMG output for every submitted variant."""
    tool = _genebe_tool()
    with patch(
        "tooluniverse.genebe_tool.requests.post",
        return_value=_fake_response(200, _GENEBE_BATCH_BODY),
    ) as mock_post:
        out = tool.run(
            {
                "variants": [
                    {"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"},
                    {"chr": "22", "pos": 28695868, "ref": "AG", "alt": "A"},
                ],
                "genome": "hg38",
            }
        )
    assert out["status"] == "success"
    variants = out["data"]["variants"]
    assert len(variants) == 2
    assert variants[0]["acmg_classification"] == "Pathogenic"
    assert variants[0]["acmg_score"] == 14
    assert variants[0]["acmg_by_gene"][0]["gene_symbol"] == "BRAF"
    assert variants[0]["acmg_by_gene"][0]["hgvs_p"] == "p.Val600Glu"
    assert variants[1]["acmg_by_gene"][0]["gene_symbol"] == "CHEK2"
    assert out["metadata"]["result_count"] == 2
    # The build alias maps GRCh38->hg38 and is sent as a query param, body is
    # the raw variant array.
    _, kwargs = mock_post.call_args
    assert kwargs["params"]["genome"] == "hg38"
    assert isinstance(kwargs["json"], list) and len(kwargs["json"]) == 2


def test_genebe_batch_missing_field_returns_error_without_network():
    """A variant missing 'alt' is rejected before any HTTP call is made."""
    tool = _genebe_tool()
    with patch("tooluniverse.genebe_tool.requests.post") as mock_post:
        out = tool.run({"variants": [{"chr": "7", "pos": 140753336, "ref": "A"}]})
    assert out["status"] == "error"
    assert "alt" in out["error"]
    mock_post.assert_not_called()


def test_genebe_batch_http_error_returns_error_status():
    """A GeneBe HTTP 500 is surfaced as status=error, never raised."""
    tool = _genebe_tool()
    with patch(
        "tooluniverse.genebe_tool.requests.post",
        return_value=_fake_response(500, json_body=None, text="boom"),
    ):
        out = tool.run(
            {"variants": [{"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"}]}
        )
    assert out["status"] == "error"
    assert "500" in out["error"]


def test_genebe_single_path_still_works():
    """Adding the batch branch must not break the original single-variant GET."""
    tool = _genebe_tool()
    single_body = {
        "variants": [
            {
                "gene_symbol": "BRAF",
                "acmg_classification": "Pathogenic",
                "acmg_score": 14,
            }
        ]
    }
    with patch(
        "tooluniverse.genebe_tool.requests.get",
        return_value=_fake_response(200, single_body),
    ):
        out = tool.run({"chr": "7", "pos": 140753336, "ref": "A", "alt": "T"})
    assert out["status"] == "success"
    assert out["data"]["gene_symbol"] == "BRAF"


# --------------------------------------------------------------------------- #
# ClinGenAR_lookup_by_external_id  (ClinGenARTool endpoint)
# --------------------------------------------------------------------------- #
def _clingen_external_tool():
    return ClinGenARTool(
        {
            "name": "ClinGenAR_lookup_by_external_id",
            "type": "ClinGenARTool",
            "fields": {"endpoint": "lookup_by_external_id"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


_CLINGEN_ALLELES_BODY = [
    {
        "@id": "http://reg.genome.network/allele/CA123643",
        "communityStandardTitle": ["NM_004333.6(BRAF):c.1799T>A (p.Val600Glu)"],
        "externalRecords": {
            "COSMIC": [{"id": "COSM476"}],
            "ClinVarVariations": [{"variationId": 13961}],
        },
        "genomicAlleles": [
            {"hgvs": ["NC_000007.14:g.140753336A>T"], "referenceGenome": "GRCh38"}
        ],
    }
]


def test_clingen_external_id_resolves_dbsnp_rs():
    """A dbSNP rsID reverse-resolves to the canonical CA allele + cross-refs."""
    tool = _clingen_external_tool()
    with patch(
        "tooluniverse.clingen_ar_tool.requests.get",
        return_value=_fake_response(200, _CLINGEN_ALLELES_BODY),
    ) as mock_get:
        out = tool.run({"dbsnp_rs": "113488022"})
    assert out["status"] == "success"
    assert out["data"]["allele_count"] == 1
    allele = out["data"]["alleles"][0]
    assert allele["allele_id"] == "CA123643"
    assert allele["community_standard_title"].startswith("NM_004333.6(BRAF)")
    assert "COSMIC" in allele["external_records"]
    assert allele["genomic_alleles"][0]["reference_genome"] == "GRCh38"
    # The 'rs' prefix is stripped and the dbSNP.rs query key is used.
    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"dbSNP.rs": "113488022"}


def test_clingen_external_id_resolves_clinvar_variation_id():
    """A ClinVar VariationID reverse-resolves to the canonical CA allele."""
    tool = _clingen_external_tool()
    with patch(
        "tooluniverse.clingen_ar_tool.requests.get",
        return_value=_fake_response(200, _CLINGEN_ALLELES_BODY),
    ) as mock_get:
        out = tool.run({"clinvar_variation_id": "13961"})
    assert out["status"] == "success"
    assert out["data"]["alleles"][0]["allele_id"] == "CA123643"
    _, kwargs = mock_get.call_args
    assert kwargs["params"] == {"ClinVar.variationId": "13961"}


def test_clingen_external_id_requires_an_identifier():
    """With neither identifier provided, an error is returned without network."""
    tool = _clingen_external_tool()
    with patch("tooluniverse.clingen_ar_tool.requests.get") as mock_get:
        out = tool.run({})
    assert out["status"] == "error"
    assert "dbsnp_rs" in out["error"]
    mock_get.assert_not_called()


def test_clingen_external_id_empty_result_is_error():
    """An empty allele array (no match) is surfaced as status=error."""
    tool = _clingen_external_tool()
    with patch(
        "tooluniverse.clingen_ar_tool.requests.get",
        return_value=_fake_response(200, []),
    ):
        out = tool.run({"dbsnp_rs": "999999999"})
    assert out["status"] == "error"
    assert "No ClinGen allele" in out["error"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
