from unittest.mock import Mock

from tooluniverse.ucsc_genome_tool import UCSCGenomeTool


def test_search_flattens_all_track_matches_before_paging(monkeypatch) -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "positionMatches": [
            {
                "trackName": track,
                "description": track,
                "matches": [
                    {
                        "position": f"chr1:{index}-{index + 1}",
                        "posName": f"{track}-{index}",
                    }
                    for index in range(25)
                ],
            }
            for track in ("knownGene", "refGene")
        ]
    }
    monkeypatch.setattr(
        "tooluniverse.ucsc_genome_tool.requests.get", Mock(return_value=response)
    )
    tool = UCSCGenomeTool({"fields": {"endpoint_type": "search"}})

    result = tool.run(
        {"search_term": "BRCA", "genome": "hg38", "limit": 5, "offset": 20}
    )

    data = result["data"]
    # match_count describes the returned page (main convention); total beside it.
    assert data["match_count"] == 5
    assert data["total_matches"] == 50
    assert data["returned_count"] == 5
    assert [match["name"] for match in data["matches"]] == [
        "knownGene-20",
        "knownGene-21",
        "knownGene-22",
        "knownGene-23",
        "knownGene-24",
    ]
    assert data["has_more"] is True
    assert data["next_offset"] == 25
