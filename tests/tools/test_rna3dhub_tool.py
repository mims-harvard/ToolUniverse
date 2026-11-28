"""Live smoke test for the RNA 3D Hub tools (needs network)."""

import pytest

from tooluniverse import ToolUniverse

pytestmark = [pytest.mark.integration, pytest.mark.network]


@pytest.fixture(scope="module")
def tu():
    universe = ToolUniverse()
    universe.load_tools(
        include_tools=[
            "RNA3DHub_get_representative_set",
            "RNA3DHub_list_motifs",
            "RNA3DHub_get_motif",
            "RNA3DHub_get_structure_loops",
        ]
    )
    return universe


def test_trna_phe_round_trip(tu):
    """From a PDB entry to its class, its loops, and a motif group and back."""
    classes = tu.run(
        {
            "name": "RNA3DHub_get_representative_set",
            "arguments": {"resolution": "all", "pdb_id": "4TNA"},
        }
    )
    assert classes["status"] == "success"
    assert classes["metadata"]["total_classes"] > 1000
    assert any("4TNA|1|A" in row["matched_members"] for row in classes["data"])

    loops = tu.run(
        {"name": "RNA3DHub_get_structure_loops", "arguments": {"pdb_id": "4TNA"}}
    )
    assert loops["metadata"]["loop_type_counts"] == {"HL": 4, "J4": 1}
    assert loops["data"][0]["sequence"] == "CAG(H2U)(H2U)GGGAG"

    groups = tu.run(
        {
            "name": "RNA3DHub_list_motifs",
            "arguments": {"loop_type": "HL", "query": "GNRA", "limit": 1},
        }
    )
    assert groups["status"] == "success"
    top = groups["data"][0]
    assert any("GNRA" in text for text in top["instance_annotations"])

    motif = tu.run(
        {
            "name": "RNA3DHub_get_motif",
            "arguments": {"motif_id": top["motif_id"], "limit": 3},
        }
    )
    assert motif["data"]["motif_id"] == top["motif_id"]
    assert motif["data"]["num_instances"] == top["num_instances"]
    first = motif["data"]["instances"][0]
    assert first["loop_id"].startswith("HL_")
    assert len(first["unit_ids"]) == motif["data"]["num_nucleotides"]


def test_quiet_failures_come_back_as_errors(tu):
    """Both requests answer HTTP 200 with one line of text."""
    release = tu.run(
        {
            "name": "RNA3DHub_get_representative_set",
            "arguments": {"resolution": "1.5", "release": "9.99"},
        }
    )
    assert release["status"] == "error"
    assert "no representative-set release '9.99'" in release["error"]

    protein = tu.run(
        {"name": "RNA3DHub_get_structure_loops", "arguments": {"pdb_id": "1UBQ"}}
    )
    assert protein["status"] == "error"
    assert "holds no RNA structure" in protein["error"]


def test_nmr_entry_reports_its_models(tu):
    """2KZL is an NMR entry: the Hub lists each loop one time per model."""
    run = {"name": "RNA3DHub_get_structure_loops", "arguments": {"pdb_id": "2KZL"}}
    every_model = tu.run(run)
    models = every_model["metadata"]["model_count"]
    assert models > 1 and "models" in every_model["metadata"]["note"]

    run["arguments"]["model"] = 1
    one = tu.run(run)
    assert (
        one["metadata"]["total_loops"] * models
        == every_model["metadata"]["total_loops"]
    )
    assert {row["model"] for row in one["data"]} == {1}
