"""Pagination regression tests for whole-protein AlphaMissense retrieval."""

from unittest.mock import patch

import pytest

from tooluniverse.alphamissense_tool import AlphaMissenseTool


pytestmark = pytest.mark.unit


def _tool():
    return AlphaMissenseTool(
        {
            "name": "AlphaMissense_get_protein_scores",
            "fields": {"operation": "get_protein_scores"},
        }
    )


def _score(_accession, position):
    return {"uid": "TEST", "resi": position, "mean_all": position / 10}, False


def test_residue_offset_reaches_middle_page_and_exposes_continuation():
    tool = _tool()
    with (
        patch.object(tool, "_fetch_protein_length", return_value=6),
        patch.object(tool, "_fetch_single_residue", side_effect=_score) as fetch,
    ):
        result = tool.run(
            {"uniprot_id": "TEST", "max_residues": 2, "residue_offset": 2}
        )

    data = result["data"]
    assert [row["position"] for row in data["scores"]] == [3, 4]
    assert {call.args[1] for call in fetch.call_args_list} == {3, 4}
    assert data["n_positions_attempted"] == 2
    assert data["residue_offset"] == 2
    assert data["has_more"] is True
    assert data["next_residue_offset"] == 4
    assert data["result_set_complete"] is False


def test_tail_page_terminates_without_repeating_first_positions():
    tool = _tool()
    with (
        patch.object(tool, "_fetch_protein_length", return_value=6),
        patch.object(tool, "_fetch_single_residue", side_effect=_score),
    ):
        result = tool.run(
            {"uniprot_id": "TEST", "max_residues": 2, "residue_offset": 5}
        )

    data = result["data"]
    assert [row["position"] for row in data["scores"]] == [6]
    assert data["has_more"] is False
    assert data["next_residue_offset"] is None


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"max_residues": -1}, "max_residues"),
        ({"max_residues": True}, "max_residues"),
        ({"max_residues": "3"}, "max_residues"),
        ({"residue_offset": -1}, "residue_offset"),
        ({"residue_offset": True}, "residue_offset"),
    ],
)
def test_invalid_pagination_is_rejected_before_network(arguments, message):
    tool = _tool()
    with patch.object(tool, "_fetch_protein_length") as length:
        result = tool.run({"uniprot_id": "TEST", **arguments})

    assert result["status"] == "error"
    assert message in result["error"]
    length.assert_not_called()


def test_offset_beyond_tail_returns_explicit_empty_page():
    tool = _tool()
    with (
        patch.object(tool, "_fetch_protein_length", return_value=6),
        patch.object(tool, "_fetch_single_residue") as fetch,
    ):
        result = tool.run(
            {"uniprot_id": "TEST", "max_residues": 2, "residue_offset": 6}
        )

    assert result["status"] == "success"
    assert result["data"]["scores"] == []
    assert result["data"]["has_more"] is False
    assert result["data"]["next_residue_offset"] is None
    fetch.assert_not_called()
