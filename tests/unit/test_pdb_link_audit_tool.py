"""Declared-connectivity controls with synthetic atoms; no private research data."""

import json
from pathlib import Path
import jsonschema
import pytest
from tooluniverse import ToolUniverse
from tooluniverse.pdb_link_audit_tool import PDBLinkAuditTool

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/pdb_link_audit_tools.json").read_text()
)[0]
EXAMPLE = CONFIG["test_examples"][0]


def run(**changes):
    response = PDBLinkAuditTool(CONFIG).run({**EXAMPLE, **changes})
    jsonschema.validate(response, CONFIG["return_schema"])
    return response


def test_stretched_link_is_reported_without_chemical_claim():
    d = run()["data"]
    assert d["reference_link_count"] == d["resolved_link_count"] == 1
    assert d["max_length_error_angstrom"] == pytest.approx(2.57)
    assert not d["all_declared_distances_agree"] and not d["chemical_validation"]


def test_matching_reference_geometry_is_only_distance_agreement():
    d = run(observed_pdb_content=EXAMPLE["reference_pdb_content"])["data"]
    assert d["all_declared_distances_agree"]
    assert d["max_length_error_angstrom"] == 0


def test_missing_endpoint_cannot_pass():
    d = run(observed_pdb_content=EXAMPLE["observed_pdb_content"].splitlines(True)[0])[
        "data"
    ]
    assert d["unresolved_link_count"] == 1
    assert not d["all_declared_distances_agree"]
    assert d["max_length_error_angstrom"] is None


def test_residue_names_cannot_silently_change_atom_identity():
    d = run(observed_pdb_content=EXAMPLE["observed_pdb_content"].replace("ASN", "GLN"))[
        "data"
    ]
    assert d["unresolved_link_count"] == 1
    assert "residue_name_mismatch" in d["links"][0]["resolution_errors"][0]


def test_chain_and_residue_remapping_is_explicit():
    observed = EXAMPLE["reference_pdb_content"].replace(" A   1", " B   8")
    d = run(
        observed_pdb_content=observed,
        chain_map={"A": "B"},
        residue_map=[
            {"reference_chain": "A", "reference_residue": 1, "observed_residue": 8}
        ],
    )["data"]
    assert d["all_declared_distances_agree"]
    assert not run(observed_pdb_content=observed)["data"][
        "all_declared_distances_agree"
    ]


def test_insertion_code_mapping():
    lines = EXAMPLE["reference_pdb_content"].splitlines(True)
    line = list(lines[1])
    line[26] = "A"
    lines[1] = "".join(line)
    observed = "".join(lines)
    d = run(
        observed_pdb_content=observed,
        residue_map=[
            {
                "reference_chain": "A",
                "reference_residue": 1,
                "observed_residue": 1,
                "observed_insertion_code": "A",
            }
        ],
    )["data"]
    assert d["all_declared_distances_agree"]


def test_duplicate_altloc_endpoint_is_unresolved():
    observed = EXAMPLE["observed_pdb_content"]
    line = list(observed.splitlines(True)[0])
    line[16] = "B"
    d = run(observed_pdb_content=observed + "".join(line))["data"]
    assert d["unresolved_link_count"] == 1 and not d["all_declared_distances_agree"]


def test_declared_altloc_requires_the_same_observed_altloc():
    ref = EXAMPLE["reference_pdb_content"].splitlines(True)
    line = list(ref[0])
    line[16] = "B"
    ref[0] = "".join(line)
    line = list(ref[1])
    line[16] = "B"
    ref[1] = "".join(line)
    d = run(
        reference_pdb_content="".join(ref),
        observed_pdb_content=EXAMPLE["observed_pdb_content"],
    )["data"]
    assert d["unresolved_link_count"] == 1


def test_model_selection_never_pools_endpoints():
    atoms = EXAMPLE["observed_pdb_content"].splitlines(True)
    obs = (
        "MODEL        1\n"
        + atoms[0]
        + "ENDMDL\nMODEL        2\n"
        + atoms[1]
        + "ENDMDL\n"
    )
    d = run(observed_pdb_content=obs, observed_model_index=2)["data"]
    assert d["unresolved_link_count"] == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"reference_pdb_content": EXAMPLE["observed_pdb_content"]},
        {
            "reference_pdb_content": EXAMPLE["reference_pdb_content"].splitlines(True)[
                0
            ]
            * 2
            + EXAMPLE["observed_pdb_content"]
        },
        {"reference_pdb_content": "LINK  bad"},
        {
            "reference_pdb_content": EXAMPLE["reference_pdb_content"][:59]
            + "  2555"
            + EXAMPLE["reference_pdb_content"][65:]
        },
        {"observed_model_index": 0},
        {"reference_model_index": False},
        {"observed_model_index": 2},
        {"chain_map": []},
        {"chain_map": {"AB": "B"}},
        {"residue_map": {}},
        {
            "residue_map": [
                {
                    "reference_chain": "A",
                    "reference_residue": True,
                    "observed_residue": 8,
                }
            ]
        },
        {
            "residue_map": [
                {"reference_chain": "A", "reference_residue": 1, "observed_residue": 8}
            ]
            * 2
        },
        {"max_length_error_angstrom": float("nan")},
        {"max_length_error_angstrom": -1},
        {"max_length_error_angstrom": True},
        {"reference_pdb_path": "missing"},
        {"observed_pdb_content": None},
        {"reference_pdb_content": "x" * (4 * 1024 * 1024 + 1)},
    ],
)
def test_invalid_inputs_fail_closed(changes):
    assert run(**changes)["status"] == "error"


def test_input_files_are_local_and_uncached(tmp_path):
    ref = tmp_path / "reference.pdb"
    obs = tmp_path / "observed.pdb"
    ref.write_text(EXAMPLE["reference_pdb_content"])
    obs.write_text(EXAMPLE["reference_pdb_content"])
    args = {
        "reference_pdb_content": None,
        "observed_pdb_content": None,
        "reference_pdb_path": str(ref),
        "observed_pdb_path": str(obs),
    }
    a = run(**args)["data"]
    obs.write_text(EXAMPLE["observed_pdb_content"])
    b = run(**args)["data"]
    assert a["all_declared_distances_agree"] and not b["all_declared_distances_agree"]
    assert a["observed_sha256"] != b["observed_sha256"]


def test_registered_wrapper_and_return_schema():
    tu = ToolUniverse(
        tool_files={
            "pdb_link_audit": str(
                ROOT / "src/tooluniverse/data/pdb_link_audit_tools.json"
            )
        },
        keep_default_tools=False,
        hooks_enabled=False,
    )
    tu.load_tools()
    response = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": EXAMPLE}, use_cache=False
    )
    jsonschema.validate(response, CONFIG["return_schema"])
    assert (
        response["status"] == "success"
        and not response["data"]["all_declared_distances_agree"]
    )


def test_delivered_sdk_import_and_call():
    from tooluniverse.tools import PDB_compare_declared_links

    response = PDB_compare_declared_links(**EXAMPLE)
    jsonschema.validate(response, CONFIG["return_schema"])
    assert response["status"] == "success"
    assert response["data"]["resolved_link_count"] == 1
    assert not response["data"]["all_declared_distances_agree"]
