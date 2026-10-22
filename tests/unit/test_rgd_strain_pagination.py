"""Regression test for recoverable RGD strain-catalog pagination."""

from unittest.mock import patch

from tooluniverse.rgd_strain_tool import RGDStrainTool


def test_strain_search_pages_after_all_filters():
    records = [
        {
            "rgdId": i,
            "symbol": f"STRAIN{i}",
            "name": f"Strain {i}",
            "strainTypeName": "inbred" if i != 1 else "congenic",
        }
        for i in range(8)
    ]
    tool = RGDStrainTool(
        {
            "name": "RGD_search_strains",
            "fields": {"operation": "search_strains"},
        }
    )

    with patch.object(tool, "_load_catalog", return_value=records):
        result = tool.run({"strain_type": "inbred", "limit": 3, "offset": 3})

    assert [row["symbol"] for row in result["data"]] == [
        "STRAIN4",
        "STRAIN5",
        "STRAIN6",
    ]
    assert result["metadata"]["total_matches"] == 7
    assert result["metadata"]["returned"] == 3
    assert result["metadata"]["offset"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 6
