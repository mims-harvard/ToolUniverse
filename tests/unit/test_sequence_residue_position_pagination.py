from tooluniverse.sequence_analyze_tool import SequenceAnalyzeTool


def test_residue_positions_after_the_old_cutoff_are_reachable() -> None:
    tool = SequenceAnalyzeTool({})

    result = tool.run(
        {
            "operation": "count_residues",
            "sequence": "A" * 60,
            "residue": "A",
            "position_limit": 3,
            "position_offset": 50,
        }
    )

    assert result["status"] == "success"
    assert result["data"]["positions_1based"] == [51, 52, 53]
    assert result["data"]["total_positions"] == 60
    assert result["data"]["positions_returned"] == 3
    assert result["data"]["positions_truncated"] is True
    assert result["data"]["next_position_offset"] == 53
