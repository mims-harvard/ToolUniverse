"""Regression guard for Fix-R22D-1: VEP_predict_pathogenicity's rsid-mode
predictions had no way to tell which alt allele a given AlphaMissense/SIFT/
PolyPhen score applied to, for the common case of an rsID mapping to a
multiallelic site (e.g. allele_string "G/A/T").

Confirmed live for rs75527207 (CFTR): the raw Ensembl VEP REST API already
includes a `variant_allele` field on every transcript_consequences entry
(e.g. "A" for the G551D missense change, "T" for a different substitution
at the same position) -- the tool's `_parse_consequences` just never
extracted it, silently discarding the exact disambiguating field a caller
needs. Fixed by adding `variant_allele` to each parsed prediction.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.vep_pathogenicity_tool import VEPPathogenicityTool

pytestmark = pytest.mark.unit

_MULTIALLELIC_RECORD = [
    {
        "input": "rs75527207",
        "id": "rs75527207",
        "assembly_name": "GRCh38",
        "seq_region_name": "7",
        "start": 117587806,
        "end": 117587806,
        "allele_string": "G/A/T",
        "most_severe_consequence": "missense_variant",
        "transcript_consequences": [
            {
                "transcript_id": "ENST00000003084",
                "gene_symbol": "CFTR",
                "gene_id": "ENSG00000001626",
                "biotype": "protein_coding",
                "variant_allele": "A",
                "consequence_terms": ["missense_variant"],
                "amino_acids": "G/D",
                "codons": "gGt/gAt",
                "impact": "MODERATE",
            },
            {
                "transcript_id": "ENST00000003084",
                "gene_symbol": "CFTR",
                "gene_id": "ENSG00000001626",
                "biotype": "protein_coding",
                "variant_allele": "T",
                "consequence_terms": ["missense_variant"],
                "amino_acids": "G/V",
                "codons": "gGt/gTt",
                "impact": "MODERATE",
            },
        ],
    }
]


def _tool():
    return VEPPathogenicityTool(
        {"name": "vep_test", "fields": {"operation": "predict_by_rsid"}}
    )


def _resp(status_code, json_body):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body
    return r


def test_multiallelic_predictions_carry_variant_allele():
    tool = _tool()
    resp = _resp(200, _MULTIALLELIC_RECORD)

    with patch("tooluniverse.vep_pathogenicity_tool.requests.get", return_value=resp):
        result = tool.run({"rsid": "rs75527207"})

    assert result["status"] == "success"
    preds = result["data"][0]["predictions"]
    assert len(preds) == 2
    alleles = {p["variant_allele"] for p in preds}
    assert alleles == {"A", "T"}

    a_pred = next(p for p in preds if p["variant_allele"] == "A")
    t_pred = next(p for p in preds if p["variant_allele"] == "T")
    assert a_pred["amino_acids"] == "G/D"
    assert t_pred["amino_acids"] == "G/V"


def test_biallelic_single_prediction_unaffected():
    tool = _tool()
    record = [
        {
            "input": "rs699",
            "id": "rs699",
            "allele_string": "A/G",
            "transcript_consequences": [
                {
                    "transcript_id": "ENST00000001",
                    "gene_symbol": "AGT",
                    "variant_allele": "G",
                    "consequence_terms": ["missense_variant"],
                }
            ],
        }
    ]
    resp = _resp(200, record)

    with patch("tooluniverse.vep_pathogenicity_tool.requests.get", return_value=resp):
        result = tool.run({"rsid": "rs699"})

    assert result["status"] == "success"
    preds = result["data"][0]["predictions"]
    assert len(preds) == 1
    assert preds[0]["variant_allele"] == "G"
