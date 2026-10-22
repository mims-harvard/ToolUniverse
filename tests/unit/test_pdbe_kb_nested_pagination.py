"""Regression tests for PDBe-KB nested result pagination."""

from unittest.mock import Mock

import pytest

from tooluniverse.pdbe_kb_tool import PDBe_KB_Tool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return PDBe_KB_Tool(
        {
            "name": f"PDBe_KB_{endpoint}",
            "fields": {"endpoint": endpoint},
            "parameter": {"properties": {}},
        }
    )


def _mock_get(monkeypatch, payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    monkeypatch.setattr(
        "tooluniverse.pdbe_kb_tool.requests.get", lambda *args, **kwargs: response
    )


def test_ligand_sites_pages_ligands_residues_and_pdb_entries(monkeypatch):
    ligands = []
    for ligand_index in range(3):
        residues = [
            {
                "startIndex": residue_index,
                "endIndex": residue_index,
                "allPDBEntries": [
                    f"{ligand_index}-{residue_index}-{i}" for i in range(5)
                ],
            }
            for residue_index in range(4)
        ]
        ligands.append(
            {
                "name": f"Ligand {ligand_index}",
                "accession": f"L{ligand_index}",
                "residues": residues,
                "additionalData": {},
            }
        )
    _mock_get(monkeypatch, {"P04637": {"length": 393, "data": ligands}})

    result = _tool("ligand_sites").run(
        {
            "uniprot_accession": "P04637",
            "ligand_offset": 1,
            "max_ligands": 1,
            "residue_offset": 1,
            "residue_limit": 1,
            "pdb_entry_offset": 2,
            "pdb_entry_limit": 2,
        }
    )["data"]

    assert result["total_ligands"] == 3
    assert result["next_ligand_offset"] == 2
    ligand = result["ligands"][0]
    assert ligand["accession"] == "L1"
    assert ligand["binding_residues_total"] == 4
    assert ligand["next_residue_offset"] == 2
    residue = ligand["binding_residues"][0]
    assert residue["pdb_entries"] == ["1-1-2", "1-1-3"]
    assert residue["pdb_entries_total"] == 5
    assert residue["next_pdb_entry_offset"] == 4


def test_interface_residues_pages_every_nested_level(monkeypatch):
    partners = [
        {
            "name": f"Partner {partner_index}",
            "accession": f"P{partner_index}",
            "residues": [
                {
                    "startIndex": residue_index,
                    "endIndex": residue_index,
                    "allPDBEntries": [
                        f"p{partner_index}r{residue_index}e{i}" for i in range(6)
                    ],
                }
                for residue_index in range(5)
            ],
        }
        for partner_index in range(3)
    ]
    _mock_get(monkeypatch, {"P04637": {"length": 393, "data": partners}})

    result = _tool("interface_residues").run(
        {
            "uniprot_accession": "P04637",
            "partner_offset": 1,
            "max_partners": 1,
            "residue_offset": 2,
            "residue_limit": 1,
            "pdb_entry_offset": 3,
            "pdb_entry_limit": 2,
        }
    )["data"]

    assert result["total_partners"] == 3
    assert result["next_partner_offset"] == 2
    partner = result["interaction_partners"][0]
    assert partner["partner_accession"] == "P1"
    assert partner["interface_residues_total"] == 5
    assert partner["next_residue_offset"] == 3
    residue = partner["interface_residues"][0]
    assert residue["pdb_entries"] == ["p1r2e3", "p1r2e4"]
    assert residue["pdb_entries_total"] == 6
    assert residue["next_pdb_entry_offset"] == 5


def test_superposition_pages_segments_clusters_and_members(monkeypatch):
    segments = []
    for segment_index in range(3):
        clusters = []
        for cluster_index in range(3):
            clusters.append(
                [
                    {
                        "pdb_id": f"{segment_index}{cluster_index}{member_index}",
                        "auth_asym_id": "A",
                        "struct_asym_id": "A",
                        "entity_id": member_index,
                        "is_representative": member_index == 0,
                    }
                    for member_index in range(6)
                ]
            )
        segments.append(
            {
                "segment_start": segment_index * 10,
                "segment_end": segment_index * 10 + 9,
                "clusters": clusters,
            }
        )
    _mock_get(monkeypatch, {"P04637": segments})

    result = _tool("superposition").run(
        {
            "uniprot_accession": "P04637",
            "segment_offset": 1,
            "segment_limit": 1,
            "cluster_offset": 1,
            "cluster_limit": 1,
            "member_offset": 2,
            "member_limit": 2,
        }
    )["data"]

    assert result["total_segments"] == 3
    assert result["next_segment_offset"] == 2
    segment = result["segments"][0]
    assert segment["segment_start"] == 10
    assert segment["num_clusters"] == 3
    assert segment["next_cluster_offset"] == 2
    cluster = segment["clusters"][0]
    assert [member["pdb_id"] for member in cluster["members"]] == ["112", "113"]
    assert cluster["total_members"] == 6
    assert cluster["next_member_offset"] == 4
    assert cluster["representative"]["pdb_id"] == "110"
