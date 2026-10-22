from unittest.mock import Mock, patch

from tooluniverse.ucsc_genome_tool import UCSCGenomeTool


def _tool(endpoint):
    return UCSCGenomeTool({"fields": {"endpoint_type": endpoint}})


@patch("tooluniverse.ucsc_genome_tool.requests.get")
def test_track_list_has_recoverable_offset(mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "hg38": {f"track{i}": {"shortLabel": str(i)} for i in range(5)}
    }
    mock_get.return_value = response

    data = _tool("list_tracks").run({"genome": "hg38", "max_tracks": 2, "offset": 2})[
        "data"
    ]

    assert [track["track"] for track in data["tracks"]] == ["track2", "track3"]
    assert data["track_count"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4


@patch("tooluniverse.ucsc_genome_tool.requests.get")
def test_get_track_preserves_ucsc_limit_flag(mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "trackType": "bigBed",
        "itemsReturned": 2,
        "maxItemsLimit": True,
        "knownGene": [{"name": "a"}, {"name": "b"}],
    }
    mock_get.return_value = response

    data = _tool("get_track").run(
        {"genome": "hg38", "track": "knownGene", "chrom": "chr1", "start": 0, "end": 10}
    )["data"]

    assert data["truncated"] is True
    assert data["max_items_limit_reached"] is True
    assert "split" in data["truncation_note"]
