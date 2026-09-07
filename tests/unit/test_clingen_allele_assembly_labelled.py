"""Regression guard: ClinGenAllele_lookup_hgvs / get_allele used to report
``reference_genome: null`` on every genomic_alleles row because the code read
``referenceGenome`` off the inner ``coordinates[j]`` dict, when the upstream
ClinGen Allele Registry API actually puts it on the parent
``genomicAlleles[i]`` object (confirmed via a live probe against
https://reg.clinicalgenome.org/allele?hgvs=...). The inner coordinate dict
only carries start/end/allele/referenceAllele.

This mocks the upstream response with that exact (parent-level
referenceGenome / chromosome, child-level coordinates) nesting and asserts
GRCh38/GRCh37/NCBI36 come through labelled on the right rows, while a
genuinely assembly-less row (e.g. a RefSeqGene entry) stays null.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.clingen_allele_tool import ClinGenAlleleTool

pytestmark = pytest.mark.unit

# Mirrors the real shape returned by reg.clinicalgenome.org for
# NC_000015.10:g.48134287A>G: referenceGenome/chromosome live on the parent
# genomicAlleles[i] object, not inside coordinates[j].
UPSTREAM_RESPONSE = {
    "@id": "http://reg.genome.network/allele/CA7545842",
    "communityStandardTitle": ["NM_205850.3(SLC24A5):c.331A>G (p.Thr111Ala)"],
    "externalRecords": {},
    "genomicAlleles": [
        {
            "referenceGenome": "GRCh38",
            "chromosome": "15",
            "coordinates": [
                {"start": 48134286, "end": 48134287, "allele": "G", "referenceAllele": "A"}
            ],
        },
        {
            "referenceGenome": "GRCh37",
            "chromosome": "15",
            "coordinates": [
                {"start": 48426483, "end": 48426484, "allele": "G", "referenceAllele": "A"}
            ],
        },
        {
            "referenceGenome": "NCBI36",
            "chromosome": "15",
            "coordinates": [
                {"start": 46213775, "end": 46213776, "allele": "G", "referenceAllele": "A"}
            ],
        },
        {
            # RefSeqGene-style row: genuinely has no assembly label upstream.
            "referenceGenome": None,
            "chromosome": None,
            "coordinates": [
                {"start": 18315, "end": 18316, "allele": "G", "referenceAllele": "A"}
            ],
        },
    ],
    "transcriptAlleles": [],
}


def _tool(operation="lookup_hgvs"):
    return ClinGenAlleleTool(
        {"name": "ClinGenAllele_test", "fields": {"operation": operation}}
    )


def _resp(payload, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.text = str(payload)
    r.json = MagicMock(return_value=payload)
    return r


def test_lookup_hgvs_labels_each_assembly_correctly():
    tool = _tool("lookup_hgvs")
    with patch.object(
        tool.session, "get", return_value=_resp(UPSTREAM_RESPONSE)
    ):
        result = tool.run({"hgvs": "NC_000015.10:g.48134287A>G"})

    assert result["status"] == "success"
    genomic = result["data"]["genomic_alleles"]
    assert len(genomic) == 4

    by_start = {row["start"]: row for row in genomic}
    assert by_start[48134286]["reference_genome"] == "GRCh38"
    assert by_start[48426483]["reference_genome"] == "GRCh37"
    assert by_start[46213775]["reference_genome"] == "NCBI36"

    # The genuinely assembly-less (RefSeqGene) row must stay null, not be
    # invented -- and chromosome should be null there too, not "15".
    assert by_start[18315]["reference_genome"] is None
    assert by_start[18315]["chromosome"] is None

    # chromosome should still be correctly labelled on the assembly rows.
    assert by_start[48134286]["chromosome"] == "15"


def test_get_allele_shares_same_fix_via_format_allele():
    """_get_allele() reuses _format_allele(), so the fix should apply there
    too without duplicating the mistake."""
    tool = _tool("get_allele")
    with patch.object(
        tool.session, "get", return_value=_resp(UPSTREAM_RESPONSE)
    ):
        result = tool.run({"ca_id": "CA7545842"})

    assert result["status"] == "success"
    genomic = result["data"]["genomic_alleles"]
    labels = {row["reference_genome"] for row in genomic}
    assert labels == {"GRCh38", "GRCh37", "NCBI36", None}
