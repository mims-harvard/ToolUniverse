"""Regression test for reachable AlphaFill source structures."""

from unittest.mock import Mock

from tooluniverse.alphafill_tool import AlphaFillTransplantsTool


def test_transplants_page_source_pdb_ids(monkeypatch):
    response = Mock(status_code=200)
    response.json.return_value = {
        "hits": [
            {
                "pdb_id": f"pdb-{index:02d}",
                "transplants": [{"compound_id": "NA", "local_rmsd": 1.0}],
            }
            for index in range(12)
        ]
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.alphafill_tool.requests.get", lambda *a, **k: response
    )
    tool = AlphaFillTransplantsTool({"name": "AlphaFill_get_transplants"})

    item = tool.run(
        {"uniprot": "P00918", "source_pdb_offset": 5, "source_pdb_limit": 3}
    )["data"]["transplants"][0]

    assert item["source_pdb_ids"] == ["pdb-05", "pdb-06", "pdb-07"]
    assert item["source_pdb_ids_total"] == 12
    assert item["source_pdb_ids_returned"] == 3
    assert item["source_pdb_ids_truncated"] is True
    assert item["next_source_pdb_offset"] == 8
