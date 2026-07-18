"""Regression guard for Fix-R2A-003: PDBeLigandsTool 404 disambiguation.

The ligand_monomers/residue_listing PDBe endpoints 404 whenever an entry has
no data there (e.g. an entry whose only "ligand" is modeled as a polymer
chain, like SARS-CoV-2 Mpro 6LU7's N3 inhibitor) -- not only when the entry
genuinely doesn't exist. The tool used to report every such 404 as "PDB
entry not found", which is false for real, well-known entries.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pdbe_ligands_tool import PDBeLigandsTool

pytestmark = pytest.mark.unit


def _resp(status_code):
    r = MagicMock()
    r.status_code = status_code
    return r


def _ligands_tool():
    return PDBeLigandsTool(
        {
            "name": "PDBe_get_structure_ligands",
            "fields": {"endpoint": "ligand_monomers"},
        }
    )


def test_404_with_existing_entry_returns_empty_success_not_error():
    tool = _ligands_tool()
    with patch("tooluniverse.pdbe_ligands_tool.requests.get") as mock_get:
        mock_get.side_effect = [_resp(404), _resp(200)]  # ligand_monomers 404, summary 200
        result = tool.run({"pdb_id": "6lu7"})

    assert result["status"] == "success"
    assert result["data"]["ligands"] == []
    assert "note" in result
    assert "6lu7" in result["note"]


def test_404_with_nonexistent_entry_still_returns_error():
    tool = _ligands_tool()
    with patch("tooluniverse.pdbe_ligands_tool.requests.get") as mock_get:
        mock_get.side_effect = [_resp(404), _resp(404)]  # ligand_monomers 404, summary 404 too
        result = tool.run({"pdb_id": "9zzz"})

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


def test_real_ligand_data_unaffected():
    tool = _ligands_tool()
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.json.return_value = {
        "4hhb": [{"chem_comp_id": "HEM", "chem_comp_name": "HEME", "weight": 616.5}]
    }
    with patch("tooluniverse.pdbe_ligands_tool.requests.get", return_value=ok_resp):
        result = tool.run({"pdb_id": "4hhb"})

    assert result["status"] == "success"
    assert result["data"]["ligands"][0]["chem_comp_id"] == "HEM"
    assert "note" not in result
