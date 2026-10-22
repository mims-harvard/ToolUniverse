"""Regression tests for reachable PDBe ligand and residue pages."""

from unittest.mock import Mock

import pytest

from tooluniverse.pdbe_ligands_tool import PDBeLigandsTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return PDBeLigandsTool(
        {
            "name": f"PDBe_{endpoint}",
            "fields": {"endpoint": endpoint},
            "parameter": {"properties": {}},
        }
    )


def _mock_get(monkeypatch, payload):
    response = Mock(status_code=200)
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.pdbe_ligands_tool.requests.get",
        lambda *args, **kwargs: response,
    )


def test_ligand_and_annotation_pages_are_reachable(monkeypatch):
    ligands = [
        {
            "chem_comp_id": f"L{i}",
            "annotations": [
                {
                    "type": f"type-{j}",
                    "interacting_entity": {
                        "entity_id": j,
                        "auth_asym_id": "A",
                        "best_unp_accession": f"P{j}",
                    },
                }
                for j in range(5)
            ],
        }
        for i in range(4)
    ]
    _mock_get(monkeypatch, {"7k00": ligands})

    result = _tool("ligand_monomers").run(
        {
            "pdb_id": "7k00",
            "ligand_offset": 2,
            "ligand_limit": 1,
            "annotation_offset": 2,
            "annotation_limit": 2,
        }
    )["data"]

    assert result["total_ligands"] == 4
    assert result["next_ligand_offset"] == 3
    ligand = result["ligands"][0]
    assert ligand["chem_comp_id"] == "L2"
    assert [item["type"] for item in ligand["annotations"]] == [
        "type-2",
        "type-3",
    ]
    assert ligand["annotations_total"] == 5
    assert ligand["next_annotation_offset"] == 4


def test_molecule_chain_and_residue_pages_are_reachable(monkeypatch):
    molecules = [
        {
            "entity_id": molecule_index,
            "chains": [
                {
                    "chain_id": f"{molecule_index}-{chain_index}",
                    "struct_asym_id": f"S{chain_index}",
                    "residues": [
                        {
                            "residue_number": residue_index,
                            "residue_name": "ALA",
                            "author_residue_number": residue_index + 100,
                            "observed_ratio": 1.0,
                        }
                        for residue_index in range(6)
                    ],
                }
                for chain_index in range(4)
            ],
        }
        for molecule_index in range(3)
    ]
    _mock_get(monkeypatch, {"4hhb": {"molecules": molecules}})

    result = _tool("residue_listing").run(
        {
            "pdb_id": "4hhb",
            "molecule_offset": 1,
            "molecule_limit": 1,
            "chain_offset": 2,
            "chain_limit": 1,
            "residue_offset": 3,
            "residue_limit": 2,
        }
    )["data"]

    assert result["total_molecules"] == 3
    assert result["next_molecule_offset"] == 2
    molecule = result["molecules"][0]
    assert molecule["entity_id"] == 1
    assert molecule["total_chains"] == 4
    assert molecule["next_chain_offset"] == 3
    chain = molecule["chains"][0]
    assert chain["chain_id"] == "1-2"
    assert chain["total_residues"] == 6
    assert [item["residue_number"] for item in chain["residues"]] == [3, 4]
    assert chain["next_residue_offset"] == 5

