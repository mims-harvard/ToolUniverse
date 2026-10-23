"""Independent pagination regression tests for PomBase interactions."""

from unittest.mock import patch

import pytest

from tooluniverse.pombase_tool import PomBaseTool


pytestmark = pytest.mark.unit


def _tool():
    return PomBaseTool({"fields": {"endpoint_type": "gene_interactions"}})


def _payload():
    return {
        "uniquename": "SPBC11B10.09",
        "physical_interactions": [{"gene_uniquename": f"P{i}"} for i in range(100)],
        "genetic_interactions": [
            [{"gene_a_uniquename": "SPBC11B10.09", "gene_b_uniquename": f"G{i}"}, []]
            for i in range(118)
        ],
        "genes_by_uniquename": {},
    }


def test_physical_and_genetic_offsets_advance_independently():
    tool = _tool()
    with patch.object(tool, "_fetch_gene", return_value=_payload()):
        result = tool.run(
            {
                "gene_id": "SPBC11B10.09",
                "limit": 25,
                "physical_offset": 75,
                "genetic_offset": 100,
            }
        )

    data = result["data"]
    assert [row["interactor_id"] for row in data["physical_interactions"]] == [
        f"P{i}" for i in range(75, 100)
    ]
    assert data["physical_has_more"] is False
    assert data["next_physical_offset"] is None
    assert [row["interactor_id"] for row in data["genetic_interactions"]] == [
        f"G{i}" for i in range(100, 118)
    ]
    assert data["genetic_has_more"] is False
    assert data["next_genetic_offset"] is None


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"limit": 0}, "limit"),
        ({"limit": True}, "limit"),
        ({"physical_offset": -1}, "physical_offset"),
        ({"genetic_offset": True}, "genetic_offset"),
    ],
)
def test_invalid_interaction_pagination_is_rejected_before_fetch(arguments, message):
    tool = _tool()
    with patch.object(tool, "_fetch_gene") as fetch:
        result = tool.run({"gene_id": "SPBC11B10.09", **arguments})

    assert result["status"] == "error"
    assert message in result["error"]
    fetch.assert_not_called()
