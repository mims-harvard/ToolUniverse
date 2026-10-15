"""Empirical-state diagnostics must not confuse numbering or missing predictions."""

import importlib.util
import inspect
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


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("displacement", [30.0, 0.0])
def test_broken_carbonyl_rejected_before_worker(monkeypatch, index, displacement):
    lines = PDB.read_text().splitlines()
    carbon = next(
        line
        for line in lines
        if line.startswith("ATOM  ")
        and line[12:16].strip() == "C"
        and int(line[22:26]) == 76
    )
    for i, line in enumerate(lines):
        if (
            line.startswith("ATOM  ")
            and line[12:16].strip() == "O"
            and int(line[22:26]) == 76
        ):
            # Two distinct defects: displaced oxygen or an oxygen coincident with C.
            xyz = (
                carbon[30:54]
                if displacement == 0
                else f"{float(line[30:38]) + displacement:8.3f}" + line[38:54]
            )
            lines[i] = line[:30] + xyz + line[54:]
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Broken backbone reached PROPKA"),
    )
    args = {"pdb_content": "\n".join(lines) + "\n"}
    if index == 1:
        args["partner_chain"] = "A"
    response = tool(index).run(args)
    assert response["status"] == "error" and "backbone bond C-O" in response["error"]
    assert "76" in response["error"]


def test_backbone_sanity_does_not_claim_missing_or_ligand_atoms_are_valid():
    from tooluniverse.protein_pka_tool import _backbone_geometry

    content = PDB.read_text()
    report = _backbone_geometry(content)
    assert report["checked_observed_bonds"] >= 3 * 76
    assert report["missing_N_CA_C_O_atoms"] == 0
    n = next(line for line in content.splitlines() if line.startswith("ATOM  "))
    partial = _backbone_geometry(n + "\n")
    assert partial["checked_observed_bonds"] == 0
    assert partial["missing_N_CA_C_O_atoms"] == 3
    # A ligand named LIG with CA/C/O-like names is outside the protein sanity scope.
    ligand = n[:17] + "LIG" + n[20:]
    assert _backbone_geometry(ligand + "\n")["standard_protein_residues"] == 0


def test_backbone_sanity_keeps_insertion_codes_and_TER_segments_distinct():
    from tooluniverse.protein_pka_tool import _backbone_geometry

    atom = next(
        line for line in PDB.read_text().splitlines() if line.startswith("ATOM  ")
    )
    inserted = atom[:26] + "A" + atom[27:]
    assert _backbone_geometry(atom + "\n" + inserted)["standard_protein_residues"] == 2
    assert _backbone_geometry(atom + "\nTER\n" + atom)["standard_protein_residues"] == 2
    with pytest.raises(ValueError, match="Duplicate protein backbone atom"):
        _backbone_geometry(atom + "\n" + atom)


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
    assert data["input_backbone_geometry"]["checked_observed_bonds"] >= 3 * 76
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


@pytest.mark.parametrize(
    "keep", ["G", {}, [True], [""], ["AB"], ["A"], ["W", "W"], ["Z"]]
)
def test_invalid_retained_components_do_not_predict(monkeypatch, keep):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Invalid free components reached prediction"),
    )
    content = (
        ROOT / "tests/fixtures/protein_pka/1ubq_with_associated_water.pdb"
    ).read_text()
    result = tool(1).run(
        {"pdb_content": content, "partner_chain": "A", "free_keep_chains": keep}
    )
    assert result["status"] == "error" and "free_keep_chains" in result["error"]


def test_associated_chain_does_not_replace_missing_primary_partner(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Missing primary partner reached prediction"),
    )
    result = tool(1).run(
        {"pdb_path": str(PDB), "partner_chain": "B", "free_keep_chains": ["A"]}
    )
    assert result["status"] == "error" and "no protein" in result["error"]


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_retained_component_preserves_same_composition():
    path = ROOT / "tests/fixtures/protein_pka/1ubq_with_associated_water.pdb"
    response = tool(1).run(
        {"pdb_path": str(path), "partner_chain": "A", "free_keep_chains": ["W"]}
    )
    jsonschema.validate(response, CONFIGS[1]["return_schema"])
    assert response["status"] == "success", response
    data = response["data"]
    assert data["free_partner_chains"] == ["A", "W"]
    assert data["free_partner_coordinate_records"] == 603
    assert len(data["comparison"]["matched_groups"]) == 26
    assert all(
        abs(g["bound_minus_free_pka"]) < 1e-10
        for g in data["comparison"]["matched_groups"]
    )


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_null_retention_keeps_existing_single_chain_default():
    response = tool(1).run(
        {"pdb_path": str(PDB), "partner_chain": "A", "free_keep_chains": None}
    )
    assert response["status"] == "success", response
    assert response["data"]["free_partner_chains"] == ["A"]


def test_exact_worker_free_input_retains_requested_component_only(monkeypatch):
    from types import SimpleNamespace

    path = ROOT / "tests/fixtures/protein_pka/1ubq_with_associated_water.pdb"
    original = path.read_text()
    other = next(line for line in original.splitlines() if line.startswith("ATOM  "))
    other = other[:21] + "B" + other[22:]
    content = original.replace("END\n", other + "\nEND\n")
    seen = {}
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.importlib.util.find_spec", lambda name: True
    )

    def capture(command, **kwargs):
        request = json.loads(Path(command[2]).read_text())
        seen["free"] = Path(request["free_path"]).read_text()
        Path(command[3]).write_text(
            json.dumps({"status": "error", "error": "captured"})
        )
        return SimpleNamespace(returncode=0, stderr="")

    monkeypatch.setattr("tooluniverse.protein_pka_tool.subprocess.run", capture)
    response = tool(1).run(
        {"pdb_content": content, "partner_chain": "A", "free_keep_chains": ["W"]}
    )
    assert response == {"status": "error", "error": "captured"}
    records = [
        line for line in seen["free"].splitlines() if line[:6] in ("ATOM  ", "HETATM")
    ]
    assert {line[21] for line in records} == {"A", "W"}
    assert len(records) == 603
    assert "HETATM" in seen["free"]


def test_retention_limit_is_bounded(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pka_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Unbounded components reached prediction"),
    )
    result = tool(1).run(
        {"pdb_path": str(PDB), "partner_chain": "A", "free_keep_chains": ["W"] * 63}
    )
    assert result["status"] == "error" and "free_keep_chains" in result["error"]


def test_auxiliary_protein_groups_do_not_hide_real_primary_mismatches():
    bound = {
        "groups": [
            group(residue=68),
            group(residue=69),
            group(chain="B"),
            group(chain="B", residue=69),
        ]
    }
    free = {
        "groups": [
            group(residue=68),
            group(residue=70),
            group(chain="B"),
            group(chain="B", residue=70),
        ]
    }
    result = compare(bound, free, "A")
    assert [g["residue_number"] for g in result["matched_groups"]] == [68]
    assert [
        (g["chain"], g["residue_number"]) for g in result["unmatched_bound_groups"]
    ] == [("A", 69)]
    assert [
        (g["chain"], g["residue_number"]) for g in result["unmatched_free_groups"]
    ] == [("A", 70)]


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_kept_protein_chain_remains_in_environment_not_primary_comparison():
    lines = [line for line in PDB.read_text().splitlines() if line.startswith("ATOM  ")]
    other = [
        line[:21] + "B" + line[22:30] + f"{float(line[30:38]) + 100:8.3f}" + line[38:]
        for line in lines
    ]
    content = "\n".join(lines + other) + "\nEND\n"
    result = tool(1).run(
        {"pdb_content": content, "partner_chain": "A", "free_keep_chains": ["B"]}
    )
    assert result["status"] == "success", result
    data = result["data"]
    assert data["free_partner_chains"] == ["A", "B"]
    assert any(g["chain"] == "B" for g in data["free_prediction"]["groups"])
    assert not data["comparison"]["unmatched_bound_groups"]
    assert not data["comparison"]["unmatched_free_groups"]
    assert len(data["comparison"]["matched_groups"]) == 26
    assert (
        sum(
            g["group_type"] in {"ASP", "GLU", "C-"}
            for g in data["comparison"]["matched_groups"]
        )
        == 12
    )
    assert all(
        g["chain"] == "A" and abs(g["bound_minus_free_pka"]) < 1e-10
        for g in data["comparison"]["matched_groups"]
    )


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_prediction_keeps_all_ubiquitin_carboxylates_and_c_terminus():
    result = tool().run({"pdb_path": str(PDB)})
    assert result["status"] == "success", result
    groups = result["data"]["prediction"]["groups"]
    acidic = {
        g["residue_number"]: g
        for g in groups
        if g["group_type"] in {"ASP", "GLU", "C-"}
    }
    assert set(acidic) == {16, 18, 21, 24, 32, 34, 39, 51, 52, 58, 64, 76}
    assert acidic[21]["group_type"] == "ASP"
    assert acidic[16]["group_type"] == "GLU"
    assert acidic[76]["group_type"] == "C-"
    assert all(
        g["propka_group_type"] == "COO" and math.isfinite(g["pka"])
        for g in acidic.values()
    )
    comparison = tool(1).run({"pdb_path": str(PDB), "partner_chain": "A"})
    matched = comparison["data"]["comparison"]["matched_groups"]
    assert len(matched) == len(groups)
    assert all(abs(g["bound_minus_free_pka"]) < 1e-10 for g in matched)


@pytest.mark.parametrize(
    "residue,terminal,kind",
    [
        ("ASP", None, "ASP"),
        ("GLU", None, "GLU"),
        ("ASP", "C-", "C-"),
        ("GLY", None, None),
    ],
)
def test_upstream_carboxylate_identity_and_ligand_exclusion(residue, terminal, kind):
    from types import SimpleNamespace
    from tooluniverse.protein_pka_worker import protein_group_type

    atom = SimpleNamespace(type="atom", res_name=residue, terminal=terminal)
    upstream = SimpleNamespace(type="COO", atom=atom)
    assert protein_group_type(upstream) == kind
    atom.type = "hetatm"
    assert protein_group_type(upstream) is None


@pytest.mark.parametrize("kind", ["ASP", "GLU", "C-", "HIS", "N+"])
def test_existing_group_identities_remain_compatible(kind):
    from types import SimpleNamespace
    from tooluniverse.protein_pka_worker import protein_group_type

    assert protein_group_type(SimpleNamespace(type=kind)) == kind


def test_delivered_pka_sdk_accepts_all_declared_parameters():
    from tooluniverse import tools as sdk

    for config in CONFIGS:
        wrapper = getattr(sdk, config["name"])
        parameters = inspect.signature(wrapper).parameters
        assert set(config["parameter"]["properties"]) <= set(parameters)


@pytest.mark.parametrize("retained", [None, ["W"]])
def test_sdk_forwards_retained_components_without_changing_defaults(
    monkeypatch, retained
):
    from tooluniverse.tools import PROPKA_compare_partner_pka

    wrapper_module = importlib.import_module(PROPKA_compare_partner_pka.__module__)
    calls = []
    response = {"status": "success", "data": {"sdk_dispatch_reached": True}}

    class Client:
        def run_one_function(self, call, **options):
            calls.append((call, options))
            return response

    monkeypatch.setattr(wrapper_module, "get_shared_client", lambda: Client())
    result = PROPKA_compare_partner_pka(
        pdb_path=str(PDB), partner_chain="A", free_keep_chains=retained
    )
    assert result is response
    assert len(calls) == 1
    call, options = calls[0]
    assert call["name"] == "PROPKA_compare_partner_pka"
    assert call["arguments"]["partner_chain"] == "A"
    if retained is None:
        assert "free_keep_chains" not in call["arguments"]
    else:
        assert call["arguments"]["free_keep_chains"] == retained
    assert options["use_cache"] is False and options["validate"] is True


@pytest.mark.skipif(not HAS_PROPKA, reason="Optional PROPKA not installed")
def test_real_delivered_sdk_retains_public_component():
    from tooluniverse.tools import PROPKA_compare_partner_pka

    path = ROOT / "tests/fixtures/protein_pka/1ubq_with_associated_water.pdb"
    response = PROPKA_compare_partner_pka(
        pdb_path=str(path), partner_chain="A", free_keep_chains=["W"]
    )
    jsonschema.validate(response, CONFIGS[1]["return_schema"])
    assert response["status"] == "success", response
    data = response["data"]
    assert data["free_partner_chains"] == ["A", "W"]
    assert data["free_partner_coordinate_records"] == 603
    assert len(data["comparison"]["matched_groups"]) == 26
    assert all(
        g["chain"] == "A" and abs(g["bound_minus_free_pka"]) < 1e-10
        for g in data["comparison"]["matched_groups"]
    )
    assert not data["binding_verified"] and not data["pH_selectivity_verified"]
