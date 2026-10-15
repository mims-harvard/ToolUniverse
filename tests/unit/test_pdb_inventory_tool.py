"""Content, model and classification controls for coordinate inventories."""

import json
from pathlib import Path
from unittest.mock import Mock

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.pdb_inventory_tool import MAX_BYTES, PDBInventoryTool

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/pdb_inventory_tools.json").read_text()
)[0]
PDB = ROOT / "tests/fixtures/pdb_inventory/1ubq_protein.pdb"


def tool():
    return PDBInventoryTool(CONFIG)


def atom(
    residue="NAG",
    chain="G",
    number=1,
    insertion="",
    record="ATOM  ",
    name="C1",
    symbol="C",
    alt="",
):
    return f"{record}{1:5d} {name:>4s}{alt:1s}{residue:>3s} {chain}{number:4d}{insertion:1s}   {1:8.3f}{2:8.3f}{3:8.3f}{1:6.2f}{10:6.2f}          {symbol:>2s}\n"


def result(content, **kwargs):
    response = tool().run({"pdb_content": content, **kwargs})
    jsonschema.validate(response, CONFIG["return_schema"])
    assert response["status"] == "success", response
    return response["data"]


def test_public_ubiquitin_sequence_and_actual_contents(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.pdb_inventory_tool.requests.get",
        lambda *a, **k: pytest.fail("Local input uploaded"),
    )
    response = tool().run({"pdb_path": str(PDB), "expected_chain_lengths": {"A": 76}})
    jsonschema.validate(response, CONFIG["return_schema"])
    data = response["data"]
    assert data["observed_protein_chain_lengths"] == {"A": 76}
    assert data["chains"]["A"]["coordinate_sequence"].startswith("MQIFVKTLTG")
    assert data["coordinate_records"] == 602
    assert data["expected_chain_lengths_match"] is True
    assert data["recognized_glycan_heavy_coordinate_records"] == 0
    assert (
        data["binding_verified"] is False
        and data["structure_chemistry_verified"] is False
    )


def test_glycans_in_atom_and_hetatm_and_hydrogens():
    data = result(
        atom() + atom(number=2, record="HETATM") + atom(number=2, name="H1", symbol="H")
    )
    assert data["recognized_glycan_coordinate_records"] == 3
    assert data["recognized_glycan_heavy_coordinate_records"] == 2
    assert data["recognized_glycan_record_types"] == {"ATOM": 2, "HETATM": 1}
    assert len(data["recognized_glycan_residues"]) == 2


def test_exact_placeholder_coordinates_are_reported_with_bounded_examples():
    text = "".join(
        atom(residue="ALA", chain="A", number=i, name="CB") for i in range(1, 101)
    )
    data = result(text)
    assert data["coincident_heavy_coordinate_group_count"] == 1
    assert data["coincident_heavy_coordinate_extra_records"] == 99
    assert len(data["coincident_heavy_coordinate_groups"][0]["examples"]) == 8
    assert data["structure_chemistry_verified"] is False


def test_force_field_labels_require_explicit_declarations():
    raw = atom(residue="0YB") + "".join(
        atom(residue="NLN", chain="A", name=n, symbol="N" if n == "N" else "C")
        for n in ["N", "CA", "C"]
    )
    without = result(raw)
    assert without["recognized_glycan_coordinate_records"] == 0
    assert without["chains"]["A"]["coordinate_sequence"] == "X"
    declared = result(
        raw, glycan_residue_names=["0YB"], protein_residue_aliases={"NLN": "ASN"}
    )
    assert declared["recognized_glycan_heavy_coordinate_records"] == 1
    assert declared["chains"]["A"]["coordinate_sequence"] == "N"
    assert declared["protein_residue_aliases"] == {"NLN": "ASN"}


def test_merged_chain_length_is_reported_not_silently_split():
    data = result(PDB.read_text(), expected_chain_lengths={"A": 40, "B": 36})
    assert data["expected_chain_lengths_match"] is False
    assert data["observed_protein_chain_lengths"] == {"A": 76}
    assert any("merged" in w for w in data["warnings"])


def test_detail_limit_does_not_truncate_counts_or_sequences():
    data = result(PDB.read_text(), max_residue_details=2)
    assert data["observed_protein_chain_lengths"] == {"A": 76}
    assert len(data["chains"]["A"]["coordinate_sequence"]) == 76
    assert len(data["chains"]["A"]["protein_rows"]) == 2
    assert data["residue_details_truncated"] is True


def test_model_selection_does_not_pool():
    data = result(
        "MODEL        4\n"
        + atom()
        + "ENDMDL\nMODEL        9\n"
        + atom()
        + atom(number=2)
        + "ENDMDL\n",
        model_index=2,
    )
    assert data["input_model_count"] == 2 and data["selected_model_serial"] == 9
    assert data["coordinate_records"] == 2


def test_insertion_codes_are_distinct_and_altlocs_are_visible():
    data = result(
        atom(residue="ALA", chain="A", name="CA", insertion="A", alt="A")
        + atom(residue="ALA", chain="A", name="CA", insertion="A", alt="B")
        + atom(residue="ALA", chain="A", name="CA", insertion="B")
    )
    assert data["observed_protein_chain_lengths"] == {"A": 2}
    assert data["alternate_location_records"] == 2
    assert data["coordinate_records"] == 3


def test_ambiguous_identity_does_not_choose_one_amino_acid():
    text = "".join(
        atom(residue=r, chain="A", name=n, alt=a)
        for r, a in [("ALA", "A"), ("SER", "B")]
        for n in ["N", "CA", "C"]
    )
    data = result(text)
    assert data["chains"]["A"]["coordinate_sequence"] == "X"
    assert len(data["ambiguous_residue_identifiers"]) == 1


def test_ter_and_noncontiguous_residue_identifiers_are_visible():
    data = result(
        atom(residue="ALA", chain="A", name="CA")
        + "TER                  A\n"
        + atom(residue="ALA", chain="A", name="CA")
    )
    assert data["chains"]["A"]["TER_records"] == 1
    assert data["noncontiguous_residue_identifier_count"] == 1


def test_element_alignment_distinguishes_carbon_from_calcium():
    carbon = atom(residue="ALA", chain="A", name="CA", symbol="")
    calcium = atom(residue="CA", chain="G", name="CA", symbol="")
    calcium = calcium[:12] + "CA  " + calcium[16:]
    data = result(carbon + calcium)
    assert (
        data["heavy_coordinate_records"] == 2 and data["element_inferred_records"] == 2
    )
    assert data["observed_protein_chain_lengths"] == {"A": 1}


@pytest.mark.parametrize(
    "args",
    [
        {},
        {"pdb_id": "../1UBQ"},
        {"pdb_content": ""},
        {"pdb_id": "1UBQ", "pdb_path": str(PDB)},
        {"pdb_content": ">FASTA\nAAAA"},
        {"pdb_content": atom(), "model_index": True},
        {"pdb_content": atom(), "model_index": 2},
        {"pdb_content": atom(), "max_residue_details": True},
        {"pdb_content": atom(), "protein_residue_aliases": []},
        {"pdb_content": atom(), "protein_residue_aliases": {"ALA": "GLU"}},
        {"pdb_content": atom(), "glycan_residue_names": ["ASP"]},
        {"pdb_content": atom(), "expected_chain_lengths": {"A": True}},
        {"pdb_content": atom(), "expected_chain_lengths": {}},
        {"pdb_content": "ENDMDL\n" + atom()},
        {"pdb_content": "MODEL        1\n" + atom()},
        {"pdb_content": "MODEL        1\nMODEL        2\n" + atom()},
        {"pdb_content": "MODEL        1\n" + atom() + "ENDMDL\n" + atom()},
        {"pdb_content": atom()[:30] + "     nan" + atom()[38:]},
        {"pdb_content": "ATOM      1\n"},
    ],
)
def test_invalid_inputs_never_reach_network(monkeypatch, args):
    monkeypatch.setattr(
        "tooluniverse.pdb_inventory_tool.requests.get",
        lambda *a, **k: pytest.fail("Invalid input reached HTTP"),
    )
    response = tool().run(args)
    assert response["status"] == "error"
    jsonschema.validate(response, CONFIG["return_schema"])


def test_mutable_path_input_is_not_cached(tmp_path):
    path = tmp_path / "protein_with_glycans.pdb"
    path.write_text(PDB.read_text())
    first = tool().run({"pdb_path": str(path)})["data"]
    path.write_text(PDB.read_text() + atom())
    second = tool().run({"pdb_path": str(path)})["data"]
    assert first["recognized_glycan_coordinate_records"] == 0
    assert second["recognized_glycan_coordinate_records"] == 1
    assert first["input_sha256"] != second["input_sha256"]
    assert not tool().supports_caching()


def test_registered_wrapper_accepts_unused_null_source():
    tu = ToolUniverse()
    tu.load_tools(categories=["pdb_inventory"])
    response = tu.tools.PDB_inspect_structure(
        pdb_path=str(PDB), pdb_content=None, pdb_id=None
    )
    assert response["status"] == "success"
    jsonschema.validate(response, CONFIG["return_schema"])
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"pdb_id": "1UBQ", "pdb_path": str(PDB)}, CONFIG["parameter"]
        )


def test_explicit_id_download_is_bounded_and_not_an_upload(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_content.return_value = [PDB.read_bytes()]
    get = Mock(return_value=response)
    monkeypatch.setattr("tooluniverse.pdb_inventory_tool.requests.get", get)
    result_ = tool().run({"pdb_id": "1ubq"})
    assert result_["status"] == "success"
    get.assert_called_once_with(
        "https://files.rcsb.org/download/1UBQ.pdb", stream=True, timeout=30
    )
    response.iter_content.return_value = [b"x" * (MAX_BYTES + 1)]
    assert "4 MiB" in tool().run({"pdb_id": "1UBQ"})["error"]


def test_path_size_bound(tmp_path):
    path = tmp_path / "large.pdb"
    path.write_bytes(b"x" * (MAX_BYTES + 1))
    assert "4 MiB" in tool().run({"pdb_path": str(path)})["error"]


def seqres(names, declared=None, serial=1, chain="A"):
    length = len(names) if declared is None else declared
    return f"SEQRES {serial:3d} {chain} {length:4d}  " + " ".join(names) + "\n"


def test_seqres_and_coordinates_are_compared_separately():
    text = seqres(["ALA", "GLY", "SER", "CYS", "ASP"])
    text += atom("ALA", "A", 1) + atom("CYS", "A", 4) + atom("ASP", "A", 5)
    d = result(text, expected_chain_lengths={"A": 5})
    assert not d["expected_chain_lengths_match"]
    assert d["expected_chain_lengths_match_seqres"] is True
    assert d["declared_protein_seqres_chain_lengths"] == {"A": 5}
    assert d["seqres_chains"]["A"]["unobserved_declared_protein_residue_count"] == 2
    assert d["coordinate_only_protein_chains"] == []
    assert d["seqres_metadata_consistent"]


def test_missing_seqres_does_not_establish_complete_sequence():
    d = result(atom("ALA", "A"), expected_chain_lengths={"A": 1})
    assert d["expected_chain_lengths_match"] is True
    assert d["expected_chain_lengths_match_seqres"] is False
    assert not d["seqres_records_present"]
    assert d["coordinate_only_protein_chains"] == ["A"]
    assert any("Coordinate-only" in w for w in d["warnings"])


def test_seqres_malformed_inconsistent_and_duplicate_serials_are_visible():
    for header in [
        "SEQRES broken\n",
        seqres(["ALA"], declared=2),
        seqres(["ALA"], declared=2) + seqres(["GLY"], declared=2),
        seqres(["ALA"], declared=2) + seqres(["GLY"], declared=3, serial=2),
    ]:
        d = result(header + atom("ALA", "A"), expected_chain_lengths={"A": 1})
        assert d["seqres_metadata_consistent"] is False
        assert d["seqres_metadata_errors"]
        assert d["expected_chain_lengths_match_seqres"] is None
        assert d["coordinate_records"] == 1


def test_seqres_identity_mismatch_is_not_described_as_missing_coordinates():
    d = result(seqres(["GLY", "SER"]) + atom("ALA", "A"))
    assert (
        d["seqres_chains"]["A"]["coordinate_sequence_is_ordered_subsequence"] is False
    )
    assert d["seqres_chains"]["A"]["unobserved_declared_protein_residue_count"] is None
    assert d["seqres_metadata_consistent"] is False


def test_global_seqres_is_compared_to_selected_model_only():
    text = seqres(["ALA", "GLY"])
    text += "MODEL        1\n" + atom("ALA", "A", 1) + "ENDMDL\n"
    text += "MODEL        2\n" + atom("ALA", "A", 1) + atom("GLY", "A", 2) + "ENDMDL\n"
    one, two = result(text), result(text, model_index=2)
    assert one["seqres_chains"]["A"]["unobserved_declared_protein_residue_count"] == 1
    assert two["seqres_chains"]["A"]["unobserved_declared_protein_residue_count"] == 0
    assert two["coordinate_records"] == 2


def test_seqres_unknown_names_need_caller_aliases_not_automatic_protein_labels():
    text = (
        seqres(["NLN", "GLY"])
        + atom("NLN", "A", name="N")
        + atom("NLN", "A", name="CA")
        + atom("NLN", "A", name="C")
    )
    unknown = result(text)
    assert (
        unknown["seqres_chains"]["A"]["coordinate_sequence_is_ordered_subsequence"]
        is None
    )
    known = result(text, protein_residue_aliases={"NLN": "ASN"})
    assert known["seqres_chains"]["A"]["unobserved_declared_protein_residue_count"] == 1
    assert known["declared_protein_seqres_chain_lengths"] == {"A": 2}


def test_seqres_completely_unobserved_declared_protein_chain_is_reported():
    d = result(seqres(["GLY"], chain="B") + atom("ALA", "A"))
    assert d["seqres_chains"]["B"]["observed_protein_residue_count"] == 0
    assert d["seqres_chains"]["B"]["unobserved_declared_protein_residue_count"] == 1
    assert d["coordinate_only_protein_chains"] == ["A"]
