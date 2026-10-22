from unittest.mock import Mock

from tooluniverse.gtdb_tool import GTDBTool


def test_species_genomes_have_offset_pagination():
    tool = GTDBTool({})
    tool._make_request = Mock(
        return_value={
            "ok": True,
            "data": {
                "name": "Example species",
                "genomes": [{"accession": f"GCF_{i}"} for i in range(5)],
            },
        }
    )

    data = tool.run(
        {
            "operation": "get_species",
            "species": "Example species",
            "max_genomes": 2,
            "offset": 2,
        }
    )["data"]

    assert [g["accession"] for g in data["genomes"]] == ["GCF_2", "GCF_3"]
    assert data["total_genomes"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4
