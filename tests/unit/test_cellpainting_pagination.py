from unittest.mock import patch

from tooluniverse.cellpainting_tool import CellPaintingTool


def test_well_offset_is_forwarded_and_total_is_preserved():
    tool = CellPaintingTool({"name": "CellPainting_get_well_data"})
    payload = {
        "data": [
            {"@id": 4, "Row": 3, "Column": 0, "WellSamples": []},
            {"@id": 5, "Row": 4, "Column": 0, "WellSamples": []},
            {"@id": 6, "Row": 5, "Column": 0, "WellSamples": []},
        ],
        "meta": {"offset": 3, "limit": 3, "maxLimit": 1000, "totalCount": 384},
    }

    with patch.object(tool, "_make_request", return_value={"ok": True, "data": payload}) as request:
        result = tool.run(
            {"operation": "get_well_data", "plate_id": 5104, "limit": 3, "offset": 3}
        )

    assert request.call_args.args[1] == {"limit": 3, "offset": 3}
    assert [well["well_id"] for well in result["data"]] == [4, 5, 6]
    assert result["pagination"] == {
        "total_count": 384,
        "returned": 3,
        "limit": 3,
        "offset": 3,
        "has_more": True,
        "next_offset": 6,
    }
