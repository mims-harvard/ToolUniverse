from unittest.mock import Mock, patch

from tooluniverse.prosite_tool import PROSITETool


@patch("tooluniverse.prosite_tool.requests.post")
def test_reverse_scan_pages_available_matches_and_discloses_server_cap(mock_post):
    response = Mock()
    response.raise_for_status.return_value = None
    response.text = "{}"
    response.json.return_value = {
        "n_match": 5,
        "n_seq": 4,
        "capped": 1,
        "matchset": [
            {"sequence_ac": f"P{i}", "start": i, "stop": i + 1}
            for i in range(5)
        ],
    }
    mock_post.return_value = response
    tool = PROSITETool({"fields": {"endpoint": "find_proteins_with_motif"}})

    result = tool.run(
        {"signature_ac": "PS00029", "max_results": 2, "offset": 2}
    )

    assert [row["sequence_ac"] for row in result["data"]] == ["P2", "P3"]
    assert result["metadata"]["available_matches"] == 5
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 4
    assert result["metadata"]["complete_database_result"] is False
    assert result["metadata"]["capped_note"]
