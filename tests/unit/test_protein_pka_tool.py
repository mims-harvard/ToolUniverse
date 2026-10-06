"""Empirical-state diagnostics must not confuse numbering or missing predictions."""

import importlib.util
import json
import math
import subprocess
from pathlib import Path

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.protein_pka_tool import ProteinPKATool
from tooluniverse.protein_pka_worker import compare, protonated_fraction

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = json.loads(
    (ROOT / "src/tooluniverse/data/protein_pka_tools.json").read_text()
)
PDB = ROOT / "tests/fixtures/protein_pka/1ubq_protein.pdb"
HAS_PROPKA = importlib.util.find_spec("propka") is not None


def tool(index=0):
    return ProteinPKATool(CONFIGS[index])


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({}, "exactly one"),
        ({"pdb_id": "1UBQ", "pdb_path": str(PDB)}, "exactly one"),
        ({"pdb_content": ""}, "nonempty"),
        ({"pdb_id": "../1UBQ"}, "identifier"),
        ({"pdb_content": ">fasta\nAAAA\n"}, "ATOM"),
        ({"pdb_path": str(PDB), "ph_values": [float("nan")]}, "finite"),
        ({"pdb_path": str(PDB), "ph_values": [15]}, "finite"),
        ({"pdb_path": str(PDB), "ph_values": [True]}, "finite"),
        ({"pdb_path": str(PDB), "ph_values": []}, "1 to 20"),
        ({"pdb_path": str(PDB), "timeout_seconds": True}, "integer"),
        ({"pdb_path": str(PDB), "timeout_seconds": 601}, "integer"),
    ],
)
def test_invalid_input_never_calculates(monkeypatch, arguments, fragment):
    def unexpected(*args, **kwargs):
        pytest.fail("Invalid input reached an external service or model")

    monkeypatch.setattr("tooluniverse.protein_pka_tool.requests.get", unexpected)
    monkeypatch.setattr("tooluniverse.protein_pka_tool.subprocess.run", unexpected)
    result = tool().run(arguments)
    assert result["status"] == "error" and fragment in result["error"]


def test_multi_model_and_altloc_rejected():
    content = PDB.read_text()
    assert (
        "Multiple"
        in tool().run(
            {"pdb_content": "MODEL        1\n" + content + "MODEL        2\n" + content}
        )["error"]
    )
    atom = next(line for line in content.splitlines() if line.startswith("ATOM  "))
    alternate = atom[:16] + "A" + atom[17:]
    assert "Alternate" in tool().run({"pdb_content": alternate})["error"]


def test_wrong_partner_rejected_before_model(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Model ran"),
    )
    assert (
        "no protein"
        in tool(1).run({"pdb_path": str(PDB), "partner_chain": "B"})["error"]
    )


def test_dependency_is_optional_and_actionable(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.importlib.util.find_spec", lambda name: None
    )
    result = tool().run({"pdb_path": str(PDB)})
    assert result["status"] == "error" and "protein-pka" in result["error"]


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_prediction_preserves_residue_number_and_fractions():
    result = tool().run({"pdb_path": str(PDB), "ph_values": [6.5, 7.4]})
    jsonschema.validate(result, CONFIGS[0]["return_schema"])
    assert result["status"] == "success", result
    data = result["data"]
    his = next(g for g in data["prediction"]["groups"] if g["group_type"] == "HIS")
    assert (his["chain"], his["residue_number"], his["insertion_code"]) == ("A", 68, "")
    assert math.isfinite(his["pka"])
    assert (
        his["protonated_fractions"][0]["fraction"]
        > his["protonated_fractions"][1]["fraction"]
    )
    assert (
        data["binding_verified"] is False and data["pH_selectivity_verified"] is False
    )


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_same_coordinate_partner_zero_shift_and_registration():
    tu = ToolUniverse()
    tu.load_tools(tool_type=["protein_pka"])
    result = tu.tools.PROPKA_compare_partner_pka(pdb_path=str(PDB), partner_chain="A")
    jsonschema.validate(result, CONFIGS[1]["return_schema"])
    assert result["status"] == "success", result
    rows = result["data"]["comparison"]["matched_groups"]
    assert rows and all(abs(row["bound_minus_free_pka"]) < 1e-10 for row in rows)
    assert "identical" in result["data"]["comparison_geometry"]


def group(chain="A", residue=68, insertion="", kind="HIS", pka=6):
    return {
        "chain": chain,
        "residue_number": residue,
        "insertion_code": insertion,
        "group_type": kind,
        "pka": pka,
        "protonated_fractions": [],
    }


def test_comparison_matches_insertion_code_and_type_not_just_position():
    bound = {"groups": [group(insertion="A", pka=7), group(kind="N+", pka=8)]}
    free = {"groups": [group(insertion="B"), group(kind="N+", pka=7.5)]}
    result = compare(bound, free, "A")
    assert len(result["matched_groups"]) == 1
    assert result["matched_groups"][0]["group_type"] == "N+"
    assert result["matched_groups"][0]["bound_minus_free_pka"] == 0.5
    assert (
        len(result["unmatched_bound_groups"])
        == len(result["unmatched_free_groups"])
        == 1
    )


def test_no_matching_groups_is_failure_not_zero_shift():
    with pytest.raises(ValueError, match="No matching"):
        compare({"groups": [group()]}, {"groups": [group(chain="B")]}, "A")


@pytest.mark.parametrize("pka,ph,expected", [(6, 6, 0.5), (-1000, 14, 0), (1000, 0, 1)])
def test_fraction_is_numerically_stable(pka, ph, expected):
    assert protonated_fraction(pka, ph) == pytest.approx(expected)


def test_timeout_is_failure(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.importlib.util.find_spec", lambda name: True
    )

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr("tooluniverse.protein_pka_tool.subprocess.run", timeout)
    result = tool().run({"pdb_path": str(PDB)})
    assert result["status"] == "error" and "exceeded" in result["error"]


def test_optional_nulls_do_not_create_ambiguous_source():
    arguments = {"pdb_path": str(PDB), "pdb_content": None, "pdb_id": None}
    jsonschema.validate(arguments, CONFIGS[0]["parameter"])


def test_cache_disabled_for_mutable_paths():
    assert not tool().supports_caching()
