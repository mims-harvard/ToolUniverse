"""Regression test for reachable PDBe SIFTS chain mappings."""

from unittest.mock import Mock

import pytest

from tooluniverse.pdbe_sifts_tool import PDBeSIFTSTool

pytestmark = pytest.mark.unit


def test_pdb_to_uniprot_pages_chain_mappings(monkeypatch):
    mappings = [
        {
            "chain_id": f"chain-{index}",
            "start": {"residue_number": index},
            "end": {"residue_number": index + 10},
            "unp_start": index + 100,
            "unp_end": index + 110,
        }
        for index in range(30)
    ]
    response = Mock()
    response.json.return_value = {
        "3j3q": {
            "UniProt": {
                "P0A7V0": {"identifier": "RL10_ECOLI", "mappings": mappings}
            }
        }
    }
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.pdbe_sifts_tool.requests.get",
        lambda *args, **kwargs: response,
    )
    tool = PDBeSIFTSTool(
        {
            "name": "PDBeSIFTS_get_pdb_to_uniprot",
            "fields": {"endpoint": "pdb_to_uniprot"},
            "parameter": {"properties": {}},
        }
    )

    protein = tool.run(
        {"pdb_id": "3j3q", "mapping_offset": 20, "mapping_limit": 3}
    )["data"]["proteins"][0]

    assert [item["chain_id"] for item in protein["chain_mappings"]] == [
        "chain-20",
        "chain-21",
        "chain-22",
    ]
    assert protein["total_chain_mappings"] == 30
    assert protein["mapping_offset"] == 20
    assert protein["chain_mappings_returned"] == 3
    assert protein["chain_mappings_truncated"] is True
    assert protein["next_mapping_offset"] == 23

