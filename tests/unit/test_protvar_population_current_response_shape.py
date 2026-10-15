"""ProtVar_get_population returned no variants for positions that have many.

ProtVar 2.x answers /population/{accession}/{position} with one flat "variants"
list; the tool only read the 1.x keys (proteinColocatedVariant /
genomicColocatedVariant), so TP53 R175 -- a cancer hotspot -- came back as
"colocated_variants": []. Payload below is trimmed from the live response for
P04637 position 175.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

PAYLOAD = {
    "accession": "P04637",
    "position": 175,
    "chromosome": None,
    "genomicPosition": None,
    "altBase": None,
    "freqMap": {},
    "variants": [
        {
            "type": "VARIANT",
            "ftId": "VAR_005928",
            "alternativeSequence": "Cys",
            "begin": "175",
            "end": "175",
            "xrefs": [
                {"name": "NCI-TCGA", "id": f"uuid-{i}", "reviewed": False}
                for i in range(40)
            ],
            "cytogeneticBand": "17p13.1",
            "genomicLocation": ["NC_000017.11:g.7675089G>A"],
            "codon": "CGC/TGC",
            "consequenceType": "missense",
            "wildType": "Arg",
            "populationFrequencies": [
                {"populationName": "MAF", "frequency": 0.0002, "source": "ClinVar"}
            ],
            "clinicalSignificances": [
                {"type": "Pathogenic", "sources": ["Ensembl", "ClinVar"]}
            ],
            "predictions": [
                {
                    "predictionValType": "deleterious",
                    "score": 0.0,
                    "predAlgorithmNameType": "SIFT",
                },
                {
                    "predictionValType": "deleterious",
                    "score": 0.0,
                    "predAlgorithmNameType": "SIFT",
                },
            ],
            "association": [
                {"name": "Adenomas and Adenocarcinomas", "disease": True},
                {"name": "Adenomas and Adenocarcinomas", "disease": True},
                {"name": "Li-Fraumeni syndrome", "disease": True},
            ],
            "sourceType": "mixed",
        },
        {
            "type": "VARIANT",
            "alternativeSequence": "Gln",
            "begin": "175",
            "end": "175",
            "xrefs": [],
            "wildType": "Arg",
            "sourceType": "uniprot",
        },
    ],
}


def _run(arguments):
    from tooluniverse.protvar_tool import ProtVarPopulationTool

    tool = ProtVarPopulationTool({"name": "ProtVar_get_population"})
    urls = []

    def fake_get(url, timeout=30):
        urls.append(url)
        return PAYLOAD

    with patch("tooluniverse.protvar_tool._get_json", side_effect=fake_get):
        return tool.run(arguments), urls


def test_variants_list_is_parsed_into_rows():
    result, _ = _run({"accession": "P04637", "position": 175})
    assert result["status"] == "success"
    rows = result["data"]["colocated_variants"]
    assert [r["alt_sequence"] for r in rows] == ["Cys", "Gln"]
    first = rows[0]
    assert first["wild_type"] == "Arg"
    assert first["consequence"] == "missense"
    assert first["genomic_location"] == "NC_000017.11:g.7675089G>A"
    assert first["cytogenetic_band"] == "17p13.1"
    assert first["clinical_significance"] == [
        {"type": "Pathogenic", "sources": ["Ensembl", "ClinVar"]}
    ]
    assert first["frequencies"] == [
        {"population": "MAF", "frequency": 0.0002, "source": "ClinVar"}
    ]
    assert len(first["predictions"]) == 1
    assert first["diseases"] == ["Adenomas and Adenocarcinomas", "Li-Fraumeni syndrome"]
    assert first["source"] == "mixed"


def test_xrefs_are_capped_but_counted():
    result, _ = _run({"accession": "P04637", "position": 175})
    first = result["data"]["colocated_variants"][0]
    assert first["xref_count"] == 40
    assert len(first["xrefs"]) == 25


def test_genomic_location_is_optional():
    result, urls = _run({"accession": "P04637", "position": 175})
    assert result["status"] == "success"
    assert result["data"]["genomic_location"] is None
    assert urls == ["https://www.ebi.ac.uk/ProtVar/api/population/P04637/175"]


def test_genomic_location_is_passed_through_when_given():
    result, urls = _run(
        {"accession": "P04637", "position": 175, "genomic_location": 7675088}
    )
    assert result["data"]["genomic_location"] == 7675088
    assert urls[0].endswith("/population/P04637/175?genomicLocation=7675088")
