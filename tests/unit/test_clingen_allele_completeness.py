"""Regression tests for complete ClinGen Allele Registry projections."""

import pytest

from tooluniverse.clingen_allele_tool import ClinGenAlleleTool

pytestmark = pytest.mark.unit


def _tool():
    return ClinGenAlleleTool({"fields": {"operation": "get_allele"}})


def _record():
    return {
        "@id": "http://reg.genome.network/allele/CA000387",
        "communityStandardTitle": ["NM_000546.6(TP53):c.743G>A (p.Arg248Gln)"],
        "externalRecords": {
            "COSMIC": [
                {
                    "@id": f"https://cancer.example/COSM{index}",
                    "active": index % 2 == 0,
                    "id": f"COSM{index}",
                }
                for index in range(6)
            ]
        },
        "genomicAlleles": [
            {
                "chromosome": "17",
                "referenceGenome": "GRCh38",
                "referenceSequence": "http://reg.example/refseq/1",
                "hgvs": ["NC_000017.11:g.7674220C>T"],
                "coordinates": [
                    {
                        "start": 7674219,
                        "end": 7674220,
                        "allele": "T",
                        "referenceAllele": "C",
                    }
                ],
            }
        ],
        "transcriptAlleles": [
            {
                "gene": "http://reg.example/gene/TP53",
                "geneNCBI_id": 7157,
                "geneSymbol": "TP53",
                "referenceSequence": f"http://reg.example/refseq/{index}",
                "hgvs": [f"ENST{index:011d}.1:c.743G>A"],
                "coordinates": [
                    {
                        "start": 742,
                        "end": 743,
                        "allele": "A",
                        "referenceAllele": "G",
                    }
                ],
                "proteinEffect": {
                    "hgvs": f"ENSP{index:011d}.1:p.Arg248Gln",
                    "hgvsWellDefined": f"ENSP{index:011d}.1:p.Arg248Gln",
                },
            }
            for index in range(65)
        ],
    }


def test_formatter_keeps_all_external_and_transcript_records_with_qualifiers():
    data = _tool()._format_allele(_record())["data"]

    assert data["ca_id"] == "CA000387"
    assert data["external_record_count"] == 6
    assert len(data["external_records"]["COSMIC"]) == 6
    assert data["external_records"]["COSMIC"][-1] == "COSM5"
    assert data["external_record_details"]["COSMIC"][-1]["active"] is False
    assert data["transcript_allele_count"] == 65
    assert len(data["transcript_alleles"]) == 65
    assert data["transcript_alleles"][64]["gene_ncbi_id"] == 7157
    assert data["transcript_alleles"][64]["coordinates"][0]["start"] == 742
    assert data["transcript_alleles"][64]["protein_effect_details"][
        "hgvsWellDefined"
    ].endswith("p.Arg248Gln")


def test_genomic_hgvs_and_reference_sequence_are_preserved():
    data = _tool()._format_allele(_record())["data"]

    assert data["genomic_allele_count"] == 1
    assert data["genomic_alleles"][0]["hgvs"] == ["NC_000017.11:g.7674220C>T"]
    assert data["genomic_alleles"][0]["reference_genome"] == "GRCh38"
    assert data["genomic_alleles"][0]["reference_sequence"].endswith("/1")
