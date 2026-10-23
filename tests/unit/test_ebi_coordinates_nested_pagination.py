"""Regression test for reachable EBI transcript and exon coordinate pages."""

from unittest.mock import Mock

import pytest

from tooluniverse.ebi_proteins_coordinates_tool import EBIProteinsCoordinatesTool

pytestmark = pytest.mark.unit


def test_coordinate_mapping_pages_transcripts_and_exons(monkeypatch):
    mappings = []
    for transcript_index in range(15):
        mappings.append(
            {
                "ensemblGeneId": "ENSG1",
                "ensemblTranscriptId": f"ENST{transcript_index}",
                "ensemblTranslationId": f"ENSP{transcript_index}",
                "genomicLocation": {
                    "chromosome": "12",
                    "exon": [
                        {
                            "id": f"exon-{transcript_index}-{exon_index}",
                            "proteinLocation": {
                                "begin": {"position": exon_index},
                                "end": {"position": exon_index + 1},
                            },
                            "genomeLocation": {
                                "begin": {"position": exon_index + 100},
                                "end": {"position": exon_index + 101},
                            },
                        }
                        for exon_index in range(30)
                    ],
                },
            }
        )
    response = Mock()
    response.json.return_value = {
        "accession": "Q13936",
        "name": "CAC1C_HUMAN",
        "taxid": 9606,
        "gnCoordinate": mappings,
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.ebi_proteins_coordinates_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    tool = EBIProteinsCoordinatesTool(
        {
            "name": "EBIProteins_get_coordinate_mapping",
            "fields": {"endpoint": "get_coordinates"},
            "parameter": {"properties": {}},
        }
    )

    result = tool.run(
        {
            "accession": "Q13936",
            "coordinate_offset": 10,
            "coordinate_limit": 2,
            "exon_offset": 20,
            "exon_limit": 3,
        }
    )["data"]

    assert result["total_coordinate_mappings"] == 15
    assert result["next_coordinate_offset"] == 12
    assert [
        item["ensembl_transcript_id"] for item in result["coordinate_mappings"]
    ] == [
        "ENST10",
        "ENST11",
    ]
    mapping = result["coordinate_mappings"][0]
    assert mapping["num_exons"] == 30
    assert [item["exon_id"] for item in mapping["exons"]] == [
        "exon-10-20",
        "exon-10-21",
        "exon-10-22",
    ]
    assert mapping["exons_returned"] == 3
    assert mapping["exons_truncated"] is True
    assert mapping["next_exon_offset"] == 23
