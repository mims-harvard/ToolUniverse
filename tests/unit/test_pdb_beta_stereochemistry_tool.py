"""Natural Ile/Thr beta checks on public and synthetic coordinates only."""

import json
import math
from pathlib import Path

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.pdb_stereochemistry_tool import PDBStereochemistryTool

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
CONFIGS = json.loads(
    (ROOT / "src/tooluniverse/data/pdb_stereochemistry_tools.json").read_text()
)
BETA = next(x for x in CONFIGS if x["name"] == "PDB_check_beta_stereochemistry")
ALPHA = next(x for x in CONFIGS if x["name"] == "PDB_check_alpha_stereochemistry")
PUBLIC = ROOT / "tests/fixtures/pdb_inventory/1ubq_protein.pdb"


def check(content=None, **kwargs):
    result = PDBStereochemistryTool(BETA).run(
        {"pdb_content": PUBLIC.read_text() if content is None else content, **kwargs}
    )
    jsonschema.validate(result, BETA["return_schema"])
    assert result["status"] == "success", result
    return result["data"]


def xyz(line):
    return tuple(float(line[i : i + 8]) for i in (30, 38, 46))


def move(line, point):
    return line[:30] + "".join(f"{x:8.3f}" for x in point) + line[54:]


def atom(name, point, residue="THR", alt=""):
    element = "O" if name == "OG1" else "N" if name == "N" else "C"
    return f"ATOM  {1:5d} {name:>4s}{alt:1s}{residue:>3s} A{1:4d}    {point[0]:8.3f}{point[1]:8.3f}{point[2]:8.3f}{1:6.2f}{10:6.2f}          {element:>2s}\n"


def synthetic(z=1.5, residue="THR", alt=""):
    return "".join(
        atom(n, p, residue, alt if n == "CG2" else "")
        for n, p in [
            ("N", (1.5, 0, 1.5)),
            ("CA", (1.5, 0, 0)),
            ("C", (1.5, 1.5, 0)),
            ("CB", (0, 0, 0)),
            ("OG1" if residue != "ILE" else "CG1", (0, 1.5, 0)),
            ("CG2", (0.5, 0.5, z)),
        ]
    )


def test_public_beta_coverage_and_local_input_stays_local(monkeypatch):
    """Public Ile/Thr centers have complete beta coverage without uploads."""
    monkeypatch.setattr(
        "tooluniverse.pdb_inventory_tool.requests.get",
        lambda *a, **k: pytest.fail("Local input uploaded"),
    )
    result = PDBStereochemistryTool(BETA).run({"pdb_path": str(PUBLIC)})
    jsonschema.validate(result, BETA["return_schema"])
    data = result["data"]
    assert data["checked_centers"] == data["eligible_beta_residues"] == 14
    assert data["matched_centers"] == 14 and data["beta_check_applicable"]
    assert (
        data["checked_center_type"] == "beta"
        and data["all_coordinate_centers_match_expected"]
    )
    assert not data["structure_chemistry_verified"] and not data["binding_verified"]
    crambin = ROOT / "tests/fixtures/pdb_stereochemistry/1crn_protein.pdb"
    assert check(crambin.read_text())["all_coordinate_centers_match_expected"]


@pytest.mark.parametrize("number,branch", [(3, "CG1"), (7, "OG1")])
def test_isolated_beta_mirror_leaves_alpha_and_local_distances(number, branch):
    """A distance-preserving sidechain mirror can pass the alpha checker."""
    lines = PUBLIC.read_text().splitlines(keepends=True)
    positions = {
        line[12:16].strip(): xyz(line)
        for line in lines
        if line.startswith("ATOM") and int(line[22:26]) == number
    }
    cb, ca, first, second = [positions[x] for x in ["CB", "CA", branch, "CG2"]]
    u, v = [tuple(a - b for a, b in zip(p, cb)) for p in [ca, first]]
    normal = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    length = math.sqrt(sum(x * x for x in normal))
    normal = [x / length for x in normal]
    height = sum((x - y) * n for x, y, n in zip(second, cb, normal))
    reflected = tuple(x - 2 * height * n for x, n in zip(second, normal))
    text = "".join(
        move(line, reflected)
        if line.startswith("ATOM")
        and int(line[22:26]) == number
        and line[12:16].strip() == "CG2"
        else line
        for line in lines
    )
    alpha = PDBStereochemistryTool(ALPHA).run({"pdb_content": text})
    assert alpha["data"]["all_coordinate_centers_match_expected"]
    beta = check(text)
    assert beta["opposite_or_degenerate_centers"] == 1
    assert (
        beta["issues"][0]["residue_number"] == number
        and beta["issues"][0]["orientation"] == "opposite"
    )
    assert all(
        math.dist(second, p) == pytest.approx(math.dist(reflected, p))
        for p in [cb, ca, first]
    )


def test_global_mirror_and_proper_rotation_have_distinct_results():
    """Reflections reverse beta orientation; proper rotations preserve it."""
    lines = PUBLIC.read_text().splitlines(keepends=True)
    mirror = "".join(
        move(x, (-xyz(x)[0], *xyz(x)[1:])) if x.startswith("ATOM") else x for x in lines
    )
    assert check(mirror)["opposite_or_degenerate_centers"] == 14
    assert check(mirror, expected_orientation="opposite")[
        "all_coordinate_centers_match_expected"
    ]
    rotated = "".join(
        move(x, (-xyz(x)[1] + 2, xyz(x)[0] + 3, xyz(x)[2] - 4))
        if x.startswith("ATOM")
        else x
        for x in lines
    )
    assert check(rotated)["all_coordinate_centers_match_expected"]


def test_absent_beta_sites_are_explicitly_inapplicable_without_vacuous_pass():
    """No eligible sites is distinct from a coordinate validation pass."""
    for residue in ["ALA", "GLY"]:
        data = check(synthetic(residue=residue))
        assert data["checked_centers"] == data["eligible_beta_residues"] == 0
        assert (
            not data["beta_check_applicable"]
            and data["all_checked_centers_match"] is None
        )
        assert not data["all_coordinate_centers_match_expected"]


def test_planarity_missing_branch_and_undeclared_identity():
    """Degenerate, missing and undeclared centers cannot manufacture coverage."""
    assert check(synthetic(z=0))["opposite_or_degenerate_centers"] == 1
    assert check(synthetic(z=0.05))["center_details"][0]["orientation"] == "degenerate"
    assert check(synthetic(z=0.05), minimum_normalized_volume=0)[
        "all_coordinate_centers_match_expected"
    ]
    missing = "".join(
        x for x in synthetic().splitlines(keepends=True) if x[12:16].strip() != "OG1"
    )
    assert check(missing)["uncheckable_centers"] == 1
    unknown = synthetic(residue="UNK")
    assert check(unknown)["uncheckable_centers"] == 1
    assert check(unknown)["beta_check_applicable"] is None
    assert check(unknown, protein_residue_aliases={"UNK": "THR"})[
        "all_coordinate_centers_match_expected"
    ]


def test_altloc_coverage_duplicates_and_wrong_oxygen_element():
    """Check alternate sidechains separately and reject ambiguous atom identity."""
    data = check(synthetic(alt="A") + atom("CG2", (0.5, 0.5, -1.5), alt="B"))
    assert data["checked_centers"] == 2 and data["matched_centers"] == 1
    assert data["issues"][0]["alternate_location"] == "B"
    assert check(synthetic() + atom("OG1", (0, 1.5, 0)))["uncheckable_centers"] == 1
    wrong = "".join(
        x[:76] + " C" + x[78:] if x[12:16].strip() == "OG1" else x
        for x in synthetic().splitlines(keepends=True)
    )
    assert check(wrong)["uncheckable_centers"] == 1


def test_beta_models_segments_and_truncation_keep_full_counts():
    """Do not pool models or TER segments, or hide failures by truncation."""
    models = (
        "MODEL        1\n"
        + synthetic()
        + "ENDMDL\nMODEL        2\n"
        + synthetic(z=-1.5)
        + "ENDMDL\n"
    )
    assert check(models)["all_coordinate_centers_match_expected"]
    assert not check(models, model_index=2)["all_coordinate_centers_match_expected"]
    data = check(
        synthetic() + "TER                  A\n" + synthetic(z=-1.5),
        max_residue_details=0,
    )
    assert (
        data["checked_centers"] == 2
        and data["opposite_or_degenerate_centers"] == data["issue_count"] == 1
    )
    assert data["issues_truncated"] and data["center_details_truncated"]


@pytest.mark.parametrize(
    "arguments",
    [
        {"pdb_content": "x", "expected_orientation": "L"},
        {"pdb_content": "x", "expected_orientation": False},
        {"pdb_content": "x", "model_index": True},
        {"pdb_content": "x", "minimum_normalized_volume": float("nan")},
        {"pdb_id": "1UBQ", "pdb_content": "x"},
    ],
)
def test_beta_errors_are_structured(arguments):
    """Malformed arguments return schema-valid errors without exceptions."""
    response = PDBStereochemistryTool(BETA).run(arguments)
    jsonschema.validate(response, BETA["return_schema"])
    assert response["status"] == "error"


def test_beta_sdk_registration_and_nullable_source_contract(monkeypatch):
    """Both operations load through the SDK with nullable unused sources."""
    tu = ToolUniverse(tool_files={}, keep_default_tools=False, hooks_enabled=False)
    tu.load_tools(
        tool_config_files={
            "pdb_stereochemistry": str(
                ROOT / "src/tooluniverse/data/pdb_stereochemistry_tools.json"
            )
        }
    )
    result = tu.tools.PDB_check_beta_stereochemistry(
        pdb_path=str(PUBLIC), pdb_content=None, pdb_id=None
    )
    jsonschema.validate(result, BETA["return_schema"])
    assert (
        result["data"]["checked_centers"] == 14
        and result["data"]["all_coordinate_centers_match_expected"]
    )
    alpha = tu.tools.PDB_check_alpha_stereochemistry(pdb_path=str(PUBLIC))
    assert alpha["data"]["checked_centers"] == 70
    from tooluniverse.tools import PDB_check_beta_stereochemistry as generated
    import tooluniverse.tools.PDB_check_beta_stereochemistry as generated_module

    # Patch the generated function's own global, avoiding the default shared client.
    monkeypatch.setitem(generated.__globals__, "get_shared_client", lambda: tu)
    result = generated(pdb_path=str(PUBLIC), use_cache=False)
    assert result["data"]["checked_centers"] == 14
