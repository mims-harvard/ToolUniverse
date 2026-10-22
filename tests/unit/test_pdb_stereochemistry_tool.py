"""Public structure and geometry invariants, without private designs or network."""

import json
import math
from pathlib import Path

import jsonschema
import pytest

pytestmark = pytest.mark.unit

from tooluniverse import ToolUniverse
from tooluniverse.pdb_stereochemistry_tool import PDBStereochemistryTool

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/pdb_stereochemistry_tools.json").read_text()
)[0]
PUBLIC = ROOT / "tests/fixtures/pdb_inventory/1ubq_protein.pdb"


def check(content=None, **kwargs):
    response = PDBStereochemistryTool(CONFIG).run(
        {"pdb_content": PUBLIC.read_text() if content is None else content, **kwargs}
    )
    jsonschema.validate(response, CONFIG["return_schema"])
    assert response["status"] == "success", response
    return response["data"]


def coordinates(line):
    return tuple(float(line[i : i + 8]) for i in (30, 38, 46))


def replace_coordinates(line, point):
    return line[:30] + "".join(f"{x:8.3f}" for x in point) + line[54:]


def atom(name, point, residue="ALA", alt="", number=1):
    return f"ATOM  {1:5d} {name:>4s}{alt:1s}{residue:>3s} A{number:4d}    {point[0]:8.3f}{point[1]:8.3f}{point[2]:8.3f}{1:6.2f}{10:6.2f}          {'N' if name == 'N' else 'C':>2s}\n"


def synthetic_center(z=1.5, residue="ALA", alt=""):
    return "".join(
        atom(n, p, residue, alt if n == "CB" else "")
        for n, p in [
            ("CA", (0, 0, 0)),
            ("N", (1.5, 0, 0)),
            ("C", (0, 1.5, 0)),
            ("CB", (1, 1, z)),
        ]
    )


def test_public_ubiquitin_centers_and_no_upload(monkeypatch):
    """Check known L-coordinate coverage without making network calls."""
    monkeypatch.setattr(
        "tooluniverse.pdb_inventory_tool.requests.get",
        lambda *a, **k: pytest.fail("Local input uploaded"),
    )
    response = PDBStereochemistryTool(CONFIG).run({"pdb_path": str(PUBLIC)})
    jsonschema.validate(response, CONFIG["return_schema"])
    d = response["data"]
    assert d["checked_centers"] == d["matched_centers"] == 70
    assert d["glycine_nonchiral_residues"] == 6
    assert d["all_coordinate_centers_match_expected"]
    assert not d["structure_chemistry_verified"] and not d["binding_verified"]


def test_global_mirror_keeps_distances_but_reverses_orientation():
    """A full reflection keeps distances and reverses all seventy centers."""
    original = PUBLIC.read_text().splitlines(keepends=True)
    reflected = [
        replace_coordinates(line, (-coordinates(line)[0], *coordinates(line)[1:]))
        if line[:6] in ("ATOM  ", "HETATM")
        else line
        for line in original
    ]
    d = check("".join(reflected))
    assert d["checked_centers"] == d["opposite_or_degenerate_centers"] == 70
    assert d["counts_by_chain"]["A"] == {"D": 70}
    assert not d["all_coordinate_centers_match_expected"]
    assert check("".join(reflected), expected_orientation="D")[
        "all_coordinate_centers_match_expected"
    ]
    a = [coordinates(line) for line in original if line.startswith("ATOM")][:10]
    b = [coordinates(line) for line in reflected if line.startswith("ATOM")][:10]
    assert all(
        math.dist(a[i], a[j]) == pytest.approx(math.dist(b[i], b[j]))
        for i in range(10)
        for j in range(10)
    )


def test_single_public_center_reflection_preserves_its_distances():
    """An isolated public alanine mirror changes handedness without length changes."""
    lines = PUBLIC.read_text().splitlines(keepends=True)
    positions = {
        line[12:16].strip(): coordinates(line)
        for line in lines
        if line.startswith("ATOM") and line[21] == "A" and int(line[22:26]) == 28
    }
    ca, n, c, cb = (positions[x] for x in ["CA", "N", "C", "CB"])
    u, v = ([a - b for a, b in zip(p, ca)] for p in [n, c])
    normal = [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]
    norm = math.sqrt(sum(x * x for x in normal))
    normal = [x / norm for x in normal]
    height = sum((x - y) * z for x, y, z in zip(cb, ca, normal))
    mirror = tuple(x - 2 * height * y for x, y in zip(cb, normal))
    modified = [
        replace_coordinates(line, mirror)
        if line.startswith("ATOM")
        and line[21] == "A"
        and int(line[22:26]) == 28
        and line[12:16].strip() == "CB"
        else line
        for line in lines
    ]
    d = check("".join(modified))
    assert d["opposite_or_degenerate_centers"] == 1
    assert d["issues"][0]["residue_number"] == 28
    assert all(
        math.dist(cb, p) == pytest.approx(math.dist(mirror, p)) for p in [ca, n, c]
    )


def test_proper_rotation_and_translation_leave_public_orientation():
    """Rigid proper transformations leave center orientation unchanged."""
    lines = PUBLIC.read_text().splitlines(keepends=True)
    transformed = []
    for line in lines:
        if line[:6] in ("ATOM  ", "HETATM"):
            x, y, z = coordinates(line)
            line = replace_coordinates(line, (-y + 2, x + 3, z - 4))
        transformed.append(line)
    assert check("".join(transformed))["all_coordinate_centers_match_expected"]


def test_planar_nearly_planar_and_missing_atoms_do_not_pass():
    """Degenerate geometry and missing centers cannot manufacture a pass."""
    assert check(synthetic_center(z=0))["opposite_or_degenerate_centers"] == 1
    near = check(synthetic_center(z=0.05))
    assert near["center_details"][0]["orientation"] == "degenerate"
    assert not near["all_coordinate_centers_match_expected"]
    assert check(synthetic_center(z=0.05), minimum_normalized_volume=0)[
        "all_coordinate_centers_match_expected"
    ]
    missing = "".join(
        line
        for line in synthetic_center().splitlines(keepends=True)
        if line[12:16].strip() != "CB"
    )
    d = check(missing)
    assert d["uncheckable_centers"] == 1 and d["all_checked_centers_match"] is None
    assert (
        not d["complete_coordinate_center_coverage"]
        and not d["all_coordinate_centers_match_expected"]
    )


def test_glycine_and_unknown_alias_coverage():
    """Separate nonchiral glycine from undeclared force-field labels."""
    d = check(synthetic_center(residue="GLY"))
    assert d["checked_centers"] == 0 and d["glycine_nonchiral_residues"] == 1
    unknown = check(synthetic_center(residue="HIE"))
    assert unknown["uncheckable_centers"] == 1
    assert check(
        synthetic_center(residue="HIE"), protein_residue_aliases={"HIE": "HIS"}
    )["all_coordinate_centers_match_expected"]


def test_altlocs_are_checked_separately_with_shared_backbone():
    """Preserve distinct alternatives and refuse ambiguous duplicated atoms."""
    a = synthetic_center(alt="A")
    b = atom("CB", (1, 1, -1.5), alt="B")
    d = check(a + b)
    assert d["checked_centers"] == 2 and d["matched_centers"] == 1
    assert d["issues"][0]["alternate_location"] == "B"
    duplicated = check(synthetic_center() + atom("N", (1.5, 0, 0)))
    assert duplicated["uncheckable_centers"] == 1


def test_models_and_repeated_ter_segments_are_not_pooled():
    """Do not mix selected models or reused residue labels after TER."""
    content = (
        "MODEL        1\n"
        + synthetic_center()
        + "ENDMDL\nMODEL        2\n"
        + synthetic_center(z=-1.5)
        + "ENDMDL\n"
    )
    assert check(content)["all_coordinate_centers_match_expected"]
    assert not check(content, model_index=2)["all_coordinate_centers_match_expected"]
    assert check(content, model_index=2)["selected_model_serial"] == 2
    ter = "TER                  A\n"
    assert (
        check(synthetic_center() + ter + synthetic_center(z=-1.5))["checked_centers"]
        == 2
    )


def test_bounded_details_preserve_issues_and_coverage_counts():
    """Detail truncation leaves complete issue and coverage counts."""
    d = check(synthetic_center(z=-1.5), max_residue_details=0)
    assert d["opposite_or_degenerate_centers"] == d["issue_count"] == 1
    assert d["issues"] == [] and d["issues_truncated"]


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"pdb_id": "1UBQ", "pdb_content": "x"},
        {"pdb_content": "x", "model_index": True},
        {"pdb_content": "x", "expected_orientation": "S"},
        {"pdb_content": "x", "minimum_normalized_volume": float("nan")},
        {"pdb_content": "x", "degenerate_tolerance_A3": -1},
    ],
)
def test_errors_return_schema_not_exceptions(arguments):
    """Validate error response contracts for malformed arguments."""
    d = PDBStereochemistryTool(CONFIG).run(arguments)
    jsonschema.validate(d, CONFIG["return_schema"])
    assert d["status"] == "error"


def test_nonfinite_coordinates_and_no_requested_model():
    """Reject nonfinite centers and absent model selections."""
    text = synthetic_center().replace("   1.500", "     nan", 1)
    assert (
        PDBStereochemistryTool(CONFIG).run({"pdb_content": text})["status"] == "error"
    )
    assert (
        PDBStereochemistryTool(CONFIG).run(
            {"pdb_content": synthetic_center(), "model_index": 2}
        )["status"]
        == "error"
    )


def test_sdk_registration_and_nullable_alternatives():
    """Exercise the real SDK wrapper with nullable unused input sources."""
    jsonschema.validate(
        {"pdb_path": str(PUBLIC), "pdb_id": None, "pdb_content": None},
        CONFIG["parameter"],
    )
    tu = ToolUniverse(tool_files={}, keep_default_tools=False, hooks_enabled=False)
    tu.load_tools(
        tool_config_files={
            "pdb_stereochemistry": str(
                ROOT / "src/tooluniverse/data/pdb_stereochemistry_tools.json"
            )
        }
    )
    d = tu.tools.PDB_check_alpha_stereochemistry(
        pdb_path=str(PUBLIC), pdb_id=None, pdb_content=None
    )
    assert d["status"] == "success" and d["data"]["checked_centers"] == 70


def test_natural_cysteine_is_L_orientation_not_CIP_S():
    """Public crambin validates the geometry convention for six natural cysteines."""
    text = (ROOT / "tests/fixtures/pdb_stereochemistry/1crn_protein.pdb").read_text()
    d = check(text)
    cysteines = [x for x in d["center_details"] if x["canonical_residue_name"] == "CYS"]
    assert len(cysteines) == 6 and all(x["orientation"] == "L" for x in cysteines)
    assert d["all_coordinate_centers_match_expected"]
