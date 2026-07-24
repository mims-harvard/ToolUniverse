"""Unit tests for cross-biobank PheWAS tools (PheWebPheWASTool, GenebassTool).

Network is fully mocked so these run in CI. They cover the logic that the live
APIs cannot exercise deterministically:
  - multi-allelic rsID resolution (try each alt, pick the one present)
  - PheWeb's HTTP-200-with-null body for absent variants
  - input validation and error envelopes
  - Genebass phenotype-description join
  - the relaxed-strict TLS adapter still rejects untrusted certificates
"""

import ssl
from unittest.mock import MagicMock, patch

import requests

from tooluniverse.pheweb_phewas_tool import (
    PheWebPheWASTool,
    GenebassTool,
    _RelaxedStrictAdapter,
    _canonicalize_variant,
)


def _pheweb_cfg(biobank="ukb_topmed"):
    return {
        "name": f"{biobank}_phewas",
        "type": "PheWebPheWASTool",
        "fields": {"biobank": biobank},
        "parameter": {"type": "object", "properties": {}},
    }


def _resp(status=200, json_body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


# --------------------------------------------------------------------------- #
# Input handling / validation
# --------------------------------------------------------------------------- #
def test_canonicalize_variant_formats():
    assert _canonicalize_variant("10:112998590:C:T") == "10:112998590-C-T"
    assert _canonicalize_variant("chr10-112998590-c-t") == "10:112998590-C-T"
    assert _canonicalize_variant("not-a-variant") is None


def test_missing_input_returns_error():
    out = PheWebPheWASTool(_pheweb_cfg()).run({})
    assert out["status"] == "error"
    assert "rsid" in out["error"].lower()


def test_bad_variant_returns_error():
    out = PheWebPheWASTool(_pheweb_cfg()).run({"variant": "garbage"})
    assert out["status"] == "error"
    assert "Invalid variant" in out["error"]


def test_unknown_biobank_returns_error():
    out = PheWebPheWASTool(_pheweb_cfg("atlantis")).run({"variant": "10:1:C:T"})
    assert out["status"] == "error"
    assert "Unknown biobank" in out["error"]


# --------------------------------------------------------------------------- #
# Multi-allelic rsID resolution + absent-variant (HTTP 200 / null) handling
# --------------------------------------------------------------------------- #
def test_multiallelic_rsid_picks_allele_present_in_biobank():
    """rs7903146 is C/G/T; only C-T exists in the biobank. PheWeb returns
    HTTP 200 with body null for the absent C-G allele, so selection must be by
    presence of phenos, not by HTTP status."""
    tool = PheWebPheWASTool(_pheweb_cfg("ukb_topmed"))

    ensembl = _resp(
        200,
        {
            "mappings": [
                {
                    "assembly_name": "GRCh38",
                    "seq_region_name": "10",
                    "start": 112998590,
                    "allele_string": "C/G/T",
                }
            ]
        },
    )
    cg_null = _resp(200, None)  # absent allele -> 200 + null
    ct_hit = _resp(
        200,
        {
            "rsids": "rs7903146",
            "nearest_genes": "TCF7L2",
            "phenos": [
                {"phenocode": "250.2", "phenostring": "Type 2 diabetes",
                 "category": "endocrine", "pval": 1e-134, "beta": 0.3,
                 "num_cases": 18000, "num_controls": 387000},
            ],
        },
    )

    with patch("tooluniverse.pheweb_phewas_tool.requests.get", return_value=ensembl), \
         patch.object(tool, "_get", side_effect=[cg_null, ct_hit]):
        out = tool.run({"rsid": "rs7903146"})

    assert out["status"] == "success"
    assert out["data"]["variant"] == "10:112998590-C-T"
    assert out["data"]["nearest_genes"] == "TCF7L2"
    assert out["data"]["associations"][0]["phenostring"] == "Type 2 diabetes"


def test_absent_variant_returns_empty_success_with_note():
    tool = PheWebPheWASTool(_pheweb_cfg("ukb_topmed"))
    with patch.object(tool, "_get", return_value=_resp(200, None)):
        out = tool.run({"variant": "10:112998590:C:G"})
    assert out["status"] == "success"
    assert out["data"]["associations"] == []
    assert out["metadata"]["total_associations"] == 0
    assert "not present" in out["metadata"]["note"]


def test_associations_sorted_and_pval_filtered():
    tool = PheWebPheWASTool(_pheweb_cfg("ukb_topmed"))
    body = {
        "phenos": [
            {"phenocode": "a", "phenostring": "A", "pval": 1e-3},
            {"phenocode": "b", "phenostring": "B", "pval": 1e-20},
            {"phenocode": "c", "phenostring": "C", "pval": 0.5},
        ]
    }
    with patch.object(tool, "_get", return_value=_resp(200, body)):
        out = tool.run({"variant": "1:1:A:T", "max_pval": 5e-8})
    assoc = out["data"]["associations"]
    assert [a["phenocode"] for a in assoc] == ["b"]  # only B passes 5e-8


def test_all_candidates_failing_returns_error():
    """If every candidate fetch raises a transient error, surface an error
    envelope rather than the misleading 'variant not present' success."""
    tool = PheWebPheWASTool(_pheweb_cfg("ukb_topmed"))
    with patch.object(tool, "_get",
                      side_effect=requests.exceptions.RequestException("503 boom")):
        out = tool.run({"variant": "10:112998590:C:T"})
    assert out["status"] == "error"
    assert "failed for all candidates" in out["error"]
    assert "503 boom" in out["error"]


def test_transient_failure_on_one_allele_still_resolves():
    """A 5xx on the first multi-allelic candidate must not abort the lookup;
    a later candidate that resolves should still yield a success."""
    tool = PheWebPheWASTool(_pheweb_cfg("ukb_topmed"))
    ensembl = _resp(
        200,
        {
            "mappings": [
                {
                    "assembly_name": "GRCh38",
                    "seq_region_name": "10",
                    "start": 112998590,
                    "allele_string": "C/G/T",
                }
            ]
        },
    )
    ct_hit = _resp(
        200,
        {
            "rsids": "rs7903146",
            "nearest_genes": "TCF7L2",
            "phenos": [
                {"phenocode": "250.2", "phenostring": "Type 2 diabetes",
                 "pval": 1e-134, "beta": 0.3},
            ],
        },
    )
    # First candidate raises transiently, second resolves.
    with patch("tooluniverse.pheweb_phewas_tool.requests.get", return_value=ensembl), \
         patch.object(tool, "_get",
                      side_effect=[requests.exceptions.RequestException("502"), ct_hit]):
        out = tool.run({"rsid": "rs7903146"})
    assert out["status"] == "success"
    assert out["data"]["nearest_genes"] == "TCF7L2"


# --------------------------------------------------------------------------- #
# Genebass
# --------------------------------------------------------------------------- #
def _genebass_cfg():
    return {
        "name": "Genebass_gene_burden_phewas",
        "type": "GenebassTool",
        "parameter": {"type": "object", "properties": {}},
    }


def test_genebass_requires_gene():
    out = GenebassTool(_genebass_cfg()).run({})
    assert out["status"] == "error"
    assert "gene" in out["error"].lower()


def test_genebass_invalid_burden_set():
    out = GenebassTool(_genebass_cfg()).run({"gene": "ENSG00000148737", "burden_set": "weird"})
    assert out["status"] == "error"
    assert "burden_set" in out["error"]


def test_genebass_joins_phenotype_descriptions():
    tool = GenebassTool(_genebass_cfg())
    phewas_body = {
        "gene": {"gene_id": "ENSG00000084674", "symbol": "APOB"},
        "phewas": [
            {"phenocode": "LDL", "trait_type": "continuous", "pheno_sex": "both_sexes",
             "coding": "", "modifier": "", "Pvalue_Burden": 1e-299,
             "BETA_Burden": -0.5, "total_variants": 30},
        ],
    }
    with patch.object(tool, "_phenotype_descriptions",
                      return_value={"continuous-LDL-both_sexes--": "LDL direct"}), \
         patch("tooluniverse.pheweb_phewas_tool.requests.get",
               return_value=_resp(200, phewas_body)):
        out = tool.run({"gene": "ENSG00000084674", "burden_set": "pLoF"})
    assert out["status"] == "success"
    assoc = out["data"]["associations"][0]
    assert assoc["description"] == "LDL direct"
    assert assoc["pval"] == 1e-299
    assert "_key" not in assoc  # internal join key stripped


def test_genebass_burden_aliases_normalize():
    tool = GenebassTool(_genebass_cfg())
    captured = {}

    def fake_get(url, **kw):
        captured["url"] = url
        return _resp(200, {"gene": {}, "phewas": []})

    with patch.object(tool, "_phenotype_descriptions", return_value={}), \
         patch("tooluniverse.pheweb_phewas_tool.requests.get", side_effect=fake_get):
        out = tool.run({"gene": "ENSG00000148737", "burden_set": "lof"})
    assert out["status"] == "success"
    assert "pLoF" in captured["url"]  # 'lof' alias -> canonical pLoF


# --------------------------------------------------------------------------- #
# Security: relaxed-strict adapter is NOT verify=False
# --------------------------------------------------------------------------- #
def test_relaxed_strict_adapter_keeps_verification():
    adapter = _RelaxedStrictAdapter()
    captured = {}

    def fake_init(*args, **kwargs):
        captured["ctx"] = kwargs.get("ssl_context")

    with patch.object(_RelaxedStrictAdapter.__mro__[1], "init_poolmanager", fake_init):
        adapter.init_poolmanager()
    ctx = captured["ctx"]
    assert ctx is not None
    # Still verifies the chain + hostname; only the strict flag is cleared.
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True
    assert not (ctx.verify_flags & ssl.VERIFY_X509_STRICT)
