"""Optional ionization models must retain coverage gaps and reject silent data loss."""

import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import jsonschema
import pytest
from tooluniverse import ToolUniverse
from tooluniverse.protein_pkai_tool import ProteinPKAITool, _inventory

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/protein_pkai_tools.json").read_text()
)[0]
PDB = ROOT / "tests/fixtures/protein_pka/1ubq_protein.pdb"


def tool():
    return ProteinPKAITool(CONFIG)


def fake_worker(monkeypatch, mutate=None):
    def run(argv, **kwargs):
        request = json.loads(Path(argv[-2]).read_text())
        expected, _, _ = _inventory(Path(request["pdb_path"]).read_text())
        groups = [
            dict(chain=c, residue_number=n, residue_name=r, pka=6.5)
            for c, n, r in expected
        ]
        if mutate:
            groups = mutate(groups)
        Path(argv[-1]).write_text(
            json.dumps(
                dict(
                    status="success",
                    data=dict(
                        model_variant=request["model_variant"],
                        groups=groups,
                        backend=dict(device="cpu", model_download_performed=False),
                    ),
                )
            )
        )
        assert kwargs["timeout"] <= 600 and "shell" not in kwargs
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("tooluniverse.protein_pkai_tool.subprocess.run", run)


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({}, "exactly one"),
        ({"pdb_id": "1UBQ", "pdb_path": str(PDB)}, "exactly one"),
        ({"pdb_content": ">FASTA\nAAAA\n"}, "ATOM"),
        ({"pdb_path": str(PDB), "model_variant": "unknown"}, "model_variant"),
        ({"pdb_path": str(PDB), "model_variant": ""}, "model_variant"),
        ({"pdb_path": str(PDB), "model_variant": False}, "model_variant"),
        ({"pdb_path": str(PDB), "threads": True}, "integer"),
        ({"pdb_path": str(PDB), "threads": 17}, "integer"),
        ({"pdb_path": str(PDB), "timeout_seconds": 0}, "integer"),
        ({"pdb_path": str(PDB), "python_executable": ""}, "interpreter"),
    ],
)
def test_invalid_inputs_do_not_predict(monkeypatch, arguments, fragment):
    monkeypatch.setattr(
        "tooluniverse.protein_pkai_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Invalid request reached model"),
    )
    result = tool().run(arguments)
    assert result["status"] == "error" and fragment in result["error"]


def test_insertions_and_missing_ionizing_atoms_are_not_silently_skipped(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pkai_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Invalid structure reached model"),
    )
    lines = PDB.read_text().splitlines()
    i = next(
        i
        for i, line in enumerate(lines)
        if line.startswith("ATOM  ") and line[17:20] == "HIS"
    )
    changed = lines.copy()
    changed[i] = changed[i][:26] + "A" + changed[i][27:]
    assert "insertion" in tool().run({"pdb_content": "\n".join(changed)})["error"]
    changed = [
        line
        for line in lines
        if not (
            line.startswith("ATOM  ")
            and line[17:20] == "HIS"
            and line[12:16].strip() == "NE2"
        )
    ]
    assert "ionizing" in tool().run({"pdb_content": "\n".join(changed)})["error"]


def test_duplicate_coordinates_and_chemical_aliases_rejected(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.protein_pkai_tool.subprocess.run",
        lambda *a, **k: pytest.fail("Invalid structure reached model"),
    )
    lines = PDB.read_text().splitlines()
    atom = next(
        line
        for line in lines
        if line.startswith("ATOM  ") and line[12:16].strip() == "CB"
    )
    changed = lines.copy()
    changed.insert(changed.index(atom) + 1, atom)
    assert "Duplicate" in tool().run({"pdb_content": "\n".join(changed)})["error"]
    changed = [
        line[:17] + "HIE" + line[20:]
        if line.startswith("ATOM  ") and line[17:20] == "HIS"
        else line
        for line in lines
    ]
    assert "standard" in tool().run({"pdb_content": "\n".join(changed)})["error"]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda groups: groups[:-1],
        lambda groups: groups + [dict(groups[0])],
        lambda groups: [
            dict(x, pka=float("nan")) if i == 0 else x for i, x in enumerate(groups)
        ],
    ],
)
def test_bad_backend_inventory_is_error_not_partial_success(monkeypatch, mutate):
    fake_worker(monkeypatch, mutate)
    assert tool().run({"pdb_path": str(PDB)})["status"] == "error"


def test_missing_whole_protein_coverage_remains_explicit(monkeypatch):
    fake_worker(monkeypatch)
    response = tool().run({"pdb_path": str(PDB), "pdb_id": None, "pdb_content": None})
    jsonschema.validate(response, CONFIG["return_schema"])
    assert response["status"] == "success"
    data = response["data"]
    assert data["supported_sidechain_inventory_complete"]
    assert not data["complete_protein_ionization_inventory"]
    assert set(data["unsupported_groups"]) == {"ARG", "N+", "C-"}
    assert not data["binding_verified"] and not data["pH_selectivity_verified"]
    assert not tool().supports_caching()


def test_registry_category_and_generated_interface(monkeypatch):
    fake_worker(monkeypatch)
    tu = ToolUniverse()
    tu.load_tools(categories=["protein_pkai"])
    result = tu.tools.PKAI_predict_sidechain_pka(
        pdb_path=str(PDB), model_variant="pKAI"
    )
    assert result["status"] == "success", result
    jsonschema.validate(result, CONFIG["return_schema"])


def test_timeout_is_finite_error(monkeypatch):
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr("tooluniverse.protein_pkai_tool.subprocess.run", timeout)
    result = tool().run({"pdb_path": str(PDB)})
    assert result["status"] == "error" and "exceeded" in result["error"]


def test_close_sg_pairs_are_geometry_flags_not_valid_ionization():
    # Synthetic parser-only boundary: no model prediction or scientific fixture.
    def atom(serial, chain, number, x):
        return f"ATOM  {serial:5d}  SG  CYS {chain}{number:4d}    {x:8.3f}{0.0:8.3f}{0.0:8.3f}  1.00 20.00           S"

    expected, close, _ = _inventory(
        atom(1, "A", 1, 0) + "\n" + atom(2, "B", 2, 2.05) + "\n"
    )
    assert len(expected) == 2 and close == {("A", 1), ("B", 2)}


@pytest.mark.skipif(
    importlib.util.find_spec("pkai") is None, reason="Optional pKAI not installed"
)
@pytest.mark.parametrize("variant", ["pKAI", "pKAI+"])
def test_real_public_ubiquitin_model(variant):
    result = tool().run({"pdb_path": str(PDB), "model_variant": variant, "threads": 1})
    assert result["status"] == "success", result
    jsonschema.validate(result, CONFIG["return_schema"])
    data = result["data"]
    assert len(data["groups"]) == 20
    assert (
        data["backend"]["device"] == "cpu"
        and not data["backend"]["model_download_performed"]
    )
    assert not data["complete_protein_ionization_inventory"]
    assert len(data["backend"]["checkpoint_sha256"]) == 64
