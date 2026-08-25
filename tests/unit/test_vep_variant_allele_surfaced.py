"""Regression guard: EnsemblVEPTool discarded `variant_allele`, making
multi-allelic results self-contradictory and unattributable.

rs1815739 is the ACTN3 R577X variant with allele_string "C/A/T". Confirmed
live against https://rest.ensembl.org/vep/human/id/rs1815739 -- every one of
the 128 transcript_consequences entries carries a `variant_allele` field, and
transcript ENST00000502692 appears twice at the *same* protein position 620:

    variant_allele "A" -> synonymous_variant, LOW,  Cga/Aga, R
    variant_allele "T" -> stop_gained,        HIGH, Cga/Tga, R/*

`_format_vep_result`'s field whitelist omitted `variant_allele`, so both rows
came back with identical transcript_id/protein_start and opposite verdicts and
no way to tell them apart -- the T allele is the clinically relevant null (X)
allele, A is benign. Fixed by adding `variant_allele` to the whitelist, which
is shared by the HGVS and rsID annotation modes.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ensembl_vep_tool import EnsemblVEPTool

pytestmark = pytest.mark.unit

# Trimmed from the real rs1815739 response: the two ENST00000502692 rows that
# collided pre-fix, plus one unrelated row.
_RS1815739 = [
    {
        "input": "rs1815739",
        "id": "rs1815739",
        "assembly_name": "GRCh38",
        "seq_region_name": "11",
        "start": 66560624,
        "end": 66560624,
        "strand": 1,
        "allele_string": "C/A/T",
        "most_severe_consequence": "stop_gained",
        "transcript_consequences": [
            {
                "gene_symbol": "ACTN3",
                "gene_id": "ENSG00000248746",
                "transcript_id": "ENST00000502692",
                "biotype": "protein_coding",
                "variant_allele": "A",
                "consequence_terms": ["synonymous_variant"],
                "impact": "LOW",
                "amino_acids": "R",
                "codons": "Cga/Aga",
                "protein_start": 620,
                "protein_end": 620,
                "strand": 1,
            },
            {
                "gene_symbol": "ACTN3",
                "gene_id": "ENSG00000248746",
                "transcript_id": "ENST00000502692",
                "biotype": "protein_coding",
                "variant_allele": "T",
                "consequence_terms": ["stop_gained"],
                "impact": "HIGH",
                "amino_acids": "R/*",
                "codons": "Cga/Tga",
                "protein_start": 620,
                "protein_end": 620,
                "strand": 1,
            },
            {
                "gene_symbol": "CTSF",
                "gene_id": "ENSG00000174080",
                "transcript_id": "ENST00000310325",
                "biotype": "protein_coding",
                "variant_allele": "A",
                "consequence_terms": ["downstream_gene_variant"],
                "impact": "MODIFIER",
                "strand": -1,
            },
        ],
        "colocated_variants": [
            {"id": "rs1815739", "allele_string": "C/A/T", "frequencies": {}}
        ],
    }
]


def _tool(mode):
    return EnsemblVEPTool({"name": "vep_test", "fields": {"mode": mode}})


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


def _run_rsid():
    with patch(
        "tooluniverse.ensembl_vep_tool.requests.get", return_value=_resp(_RS1815739)
    ):
        return _tool("vep_id").run({"variant_id": "rs1815739"})


def test_multiallelic_rows_carry_their_variant_allele():
    """Both ENST00000502692 rows survive AND are now distinguishable."""
    result = _run_rsid()

    assert result["status"] == "success"
    tcs = result["data"]["transcript_consequences"]
    assert len(tcs) == 3, "no consequence row may be dropped"

    same_transcript = [t for t in tcs if t["transcript_id"] == "ENST00000502692"]
    assert len(same_transcript) == 2

    # Every row carries the allele that produced it.
    for row in tcs:
        assert "variant_allele" in row, f"missing variant_allele: {row}"

    # The two colliding rows are no longer identical apart from their verdict.
    assert {t["variant_allele"] for t in same_transcript} == {"A", "T"}


def test_stop_gained_is_attributable_to_the_T_allele():
    """The clinical point of R577X: T is the null (X) allele, A is benign."""
    result = _run_rsid()
    tcs = result["data"]["transcript_consequences"]

    stop_gained = [t for t in tcs if "stop_gained" in t["consequence_terms"]]
    assert len(stop_gained) == 1
    assert stop_gained[0]["variant_allele"] == "T"
    assert stop_gained[0]["impact"] == "HIGH"
    assert stop_gained[0]["codons"] == "Cga/Tga"

    synonymous = next(
        t
        for t in tcs
        if t["transcript_id"] == "ENST00000502692"
        and "synonymous_variant" in t["consequence_terms"]
    )
    assert synonymous["variant_allele"] == "A"
    assert synonymous["impact"] == "LOW"

    # Same transcript, same protein position -- allele is the only discriminator.
    assert stop_gained[0]["protein_start"] == synonymous["protein_start"] == 620


def test_hgvs_mode_shares_the_fix():
    """_format_vep_result is shared, so the HGVS operation gains it too."""
    with patch(
        "tooluniverse.ensembl_vep_tool.requests.get", return_value=_resp(_RS1815739)
    ):
        result = _tool("vep_hgvs").run({"hgvs_notation": "ACTN3:p.Arg577Ter"})

    assert result["status"] == "success"
    tcs = result["data"]["transcript_consequences"]
    assert [t["variant_allele"] for t in tcs] == ["A", "T", "A"]


def test_no_pre_existing_key_changed():
    """Purely additive: variant_allele is the only new key, all old values hold."""
    result = _run_rsid()
    data = result["data"]

    # Top-level record is untouched.
    assert data["input"] == "rs1815739"
    assert data["assembly_name"] == "GRCh38"
    assert data["seq_region_name"] == "11"
    assert data["start"] == 66560624
    assert data["end"] == 66560624
    assert data["strand"] == 1
    assert data["allele_string"] == "C/A/T"
    assert data["most_severe_consequence"] == "stop_gained"
    assert data["colocated_variants"] == [
        {"id": "rs1815739", "allele_string": "C/A/T", "frequencies": {}}
    ]

    # Row ordering is preserved.
    tcs = data["transcript_consequences"]
    assert [t["transcript_id"] for t in tcs] == [
        "ENST00000502692",
        "ENST00000502692",
        "ENST00000310325",
    ]

    # variant_allele is the ONLY key added to any row.
    expected_pre_existing = {
        "gene_symbol": "ACTN3",
        "gene_id": "ENSG00000248746",
        "transcript_id": "ENST00000502692",
        "biotype": "protein_coding",
        "consequence_terms": ["stop_gained"],
        "impact": "HIGH",
        "amino_acids": "R/*",
        "codons": "Cga/Tga",
        "protein_start": 620,
        "protein_end": 620,
        "strand": 1,
    }
    row = tcs[1]
    assert set(row) - set(expected_pre_existing) == {"variant_allele"}
    for key, value in expected_pre_existing.items():
        assert row[key] == value, f"{key} changed"


def test_missing_variant_allele_upstream_is_not_fabricated():
    """None-valued fields are still dropped; the tool must not invent an allele."""
    record = [
        {
            "input": "rs999",
            "id": "rs999",
            "allele_string": "A/G",
            "transcript_consequences": [
                {
                    "transcript_id": "ENST00000000001",
                    "gene_symbol": "FOO",
                    "consequence_terms": ["intron_variant"],
                }
            ],
        }
    ]
    with patch(
        "tooluniverse.ensembl_vep_tool.requests.get", return_value=_resp(record)
    ):
        result = _tool("vep_id").run({"variant_id": "rs999"})

    assert result["status"] == "success"
    row = result["data"]["transcript_consequences"][0]
    assert "variant_allele" not in row
