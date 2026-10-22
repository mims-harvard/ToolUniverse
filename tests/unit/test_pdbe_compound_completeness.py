"""Regression tests for complete PDBe compound metadata and structures."""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.pdbe_compound_tool import PDBECompoundTool

pytestmark = pytest.mark.unit


def _response(payload):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload
    return response


def _compound(comp_id="CFF"):
    return {
        comp_id: [
            {
                "name": "CAFFEINE",
                "formula": "C8 H10 N4 O2",
                "weight": 194.19,
                "formal_charge": 0,
                "compound_type": "NON-POLYMER",
                "smiles": [
                    {"program": "one", "name": "smiles-1"},
                    {"program": "two", "name": "smiles-2"},
                ],
                "systematic_names": [
                    {"program": "one", "name": "name-1"},
                    {"program": "two", "name": "name-2"},
                ],
                "cross_links": [
                    {"resource": "ClinicalTrials", "resource_id": f"NCT{i:08d}"}
                    for i in range(20)
                ],
                "first_observed_in": ["1abc"],
            }
        ]
    }


def _tool(endpoint):
    return PDBECompoundTool({"fields": {"endpoint": endpoint}})


def test_summary_keeps_every_cross_reference_and_reports_counts():
    with patch(
        "tooluniverse.pdbe_compound_tool.requests.get",
        return_value=_response(_compound()),
    ):
        result = _tool("get_summary").run({"comp_id": "CFF"})

    data = result["data"]
    assert len(data["cross_references"]) == 20
    assert data["cross_reference_count"] == 20
    assert data["smiles_count"] == 2
    assert data["systematic_name_count"] == 2
    assert data["cross_references"][-1]["resource_id"] == "NCT00000019"


def test_structures_uses_in_pdb_endpoint_and_exposes_second_page():
    occurrences = [
        {
            "pdb_id": f"{index:04x}"[-4:],
            "ligand_type": "b",
            "ligand_total_number": float(index + 1),
            "ligand_distinct_number": 1.0,
        }
        for index in range(120)
    ]
    with patch(
        "tooluniverse.pdbe_compound_tool.requests.get",
        side_effect=[_response(_compound("ATP")), _response({"ATP": occurrences})],
    ) as mock_get:
        result = _tool("get_structures").run(
            {"comp_id": "ATP", "limit": 10, "offset": 50}
        )

    assert mock_get.call_args_list[1].args[0].endswith("/compound/in_pdb/ATP")
    data = result["data"]
    assert data["total_structures"] == 120
    assert data["returned"] == 10
    assert data["offset"] == 50
    assert data["next_offset"] == 60
    assert data["pdb_entries"] == [row["pdb_id"] for row in occurrences[50:60]]
    assert data["occurrences"][0]["ligand_total_number"] == 51.0


def test_invalid_structure_pagination_makes_no_request():
    with patch("tooluniverse.pdbe_compound_tool.requests.get") as mock_get:
        result = _tool("get_structures").run({"comp_id": "ATP", "offset": "bad"})

    assert result["status"] == "error"
    assert "integers" in result["error"]
    mock_get.assert_not_called()
