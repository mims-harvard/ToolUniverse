"""Offline unit tests for the peptide-deorphanization skill scripts.

The two scripts (``deorphanize_peptide.py``, ``cofold_screen.py``) live in the
skill directory, not the package, so we load them by path with importlib and mock
``ToolUniverse.run`` (no network). Focus: the cross-species interface alignment,
representative-PDB resolution, ortholog method-count fix, non-canonical detection,
and the co-fold argument shapes (esp. the openfold3 co-fold wrapper + boltz2 cyclic).
"""

import importlib.util
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_SKILL = (
    Path(__file__).resolve().parents[2]
    / "plugin/skills/tooluniverse-peptide-target-deorphanization/scripts"
)


def _load(name):
    spec = importlib.util.spec_from_file_location(name, _SKILL / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dp = _load("deorphanize_peptide")
cs = _load("cofold_screen")


class _FakeTU:
    """Routes ToolUniverse.run({'name','arguments'}) to a canned-response table."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def run(self, call):
        name = call["name"]
        self.calls.append((name, call.get("arguments")))
        data = self.table.get(name)
        if callable(data):
            data = data(call.get("arguments", {}))
        return {"status": "success", "data": data}


# ------------------------------ pure helpers --------------------------------

def test_noncanonical_flags_nonstandard_residues():
    assert dp._noncanonical("HGEGTFTSDLSKQ")["is_canonical_linear"] is True
    nc = dp._noncanonical("HGEGUXZ")
    assert nc["noncanonical_residues"] == ["U", "X", "Z"]
    assert nc["is_canonical_linear"] is False


def test_pairwise_identity_ignores_gap_columns():
    assert dp._pairwise_identity({"a": "ABCYDE", "b": "ABCXDE"}, "a", "b") == {
        "percent_identity": 83.3, "n_substitutions": 1, "aligned_columns": 6,
    }
    # gap-aligned column is excluded, not counted as a substitution
    assert dp._pairwise_identity({"a": "ABC-DE", "b": "ABCXDE"}, "a", "b")["n_substitutions"] == 0
    assert dp._pairwise_identity({"a": "ABC", "b": "ABCDE"}, "a", "b") is None  # length mismatch


def test_parse_fasta_str_multiline_records():
    assert dp._parse_fasta_str(">a\nMKT\nVR\n>b\nMKS\nVR") == {"a": "MKTVR", "b": "MKSVR"}


def test_organism_query_maps_common_names():
    assert dp._organism_query("mus_musculus") == "mouse"
    assert dp._organism_query("tetrahymena_thermophila") == "tetrahymena thermophila"


# --------------------- cross-species interface alignment --------------------

def test_cross_species_alignment_computes_pairwise_identity():
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": ["P_HUMAN"], "hgnc_id": "HGNC:1"},
        "UniProt_search": {"results": [{"accession": "P_MOUSE"}]},
        "UniProt_get_sequence_by_accession": lambda a: "ABCDE" if a["accession"] == "P_HUMAN" else "ABXDE",
        "EBI_msa_align": {"aligned_fasta": ">human\nABCDE\n>assay\nABXDE"},
    })
    out = dp.Pipeline(tu).cross_species_alignment("GIPR", "mus_musculus", None)
    assert out["status"] == "ok"
    pair = out["pairs"][0]
    assert pair["pair"] == "human_vs_assay"
    assert pair["percent_identity"] == 80.0 and pair["n_substitutions"] == 1


def test_cross_species_alignment_three_way_with_source():
    seqs = {"P_HUMAN": "ABCDE", "P_MOUSE": "ABXDE", "P_SRC": "ABCDE"}
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": ["P_HUMAN"]},
        # assay (mouse) then source resolve to different accessions in call order
        "UniProt_search": lambda a: {"results": [{"accession": "P_MOUSE" if a["organism"] == "mouse" else "P_SRC"}]},
        "UniProt_get_sequence_by_accession": lambda a: seqs[a["accession"]],
        "EBI_msa_align": {"aligned_fasta": ">human\nABCDE\n>assay\nABXDE\n>source\nABCDE"},
    })
    out = dp.Pipeline(tu).cross_species_alignment("GIPR", "mus_musculus", "tetrahymena_thermophila")
    pairs = {p["pair"]: p for p in out["pairs"]}
    assert pairs["human_vs_assay"]["percent_identity"] == 80.0
    assert pairs["human_vs_source"]["percent_identity"] == 100.0  # source matches human


def test_cross_species_alignment_insufficient_when_species_absent():
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": ["P_HUMAN"]},
        "UniProt_search": {"results": []},  # ortholog not found (e.g. protist)
        "UniProt_get_sequence_by_accession": "ABCDE",
    })
    out = dp.Pipeline(tu).cross_species_alignment("GIPR", "mus_musculus", None)
    assert out["status"] == "insufficient"
    assert out["resolved"] == ["human"]


# -------------------- representative PDB + ortholog count --------------------

def test_representative_pdb_reads_sifts_accession_keyed_results():
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": ["P43220"]},
        "PDBeSIFTS_get_best_structures": {"P43220": [{"pdb_id": "6x18", "chain_id": "R"}]},
    })
    out = dp.Pipeline(tu).representative_pdb("GLP1R", None)
    assert out["pdb_id"] == "6x18" and out["chain"] == "R" and out["uniprot"] == "P43220"


def test_ortholog_status_counts_methods_list():
    tu = _FakeTU({
        "Alliance_get_gene_orthologs": {"orthologs": [{"species": "Mus musculus", "methods": ["a", "b", "c"]}]},
    })
    out = dp.Pipeline(tu).ortholog_status("HGNC:4324", "mus_musculus")
    assert out["present"] is True and out["best_method_count"] == 3


# ----------------------------- co-fold arg shapes ---------------------------

def _capture():
    cf = cs.CoFolder(_FakeTU({}))
    cf.run = lambda name, args: {"status": "success", "data": {"_name": name, "_args": args}}
    return cf


def test_cofold_openfold3_wraps_both_chains_in_one_input():
    """Regression: openfold3 must co-fold (one input, molecules array), not two monomers."""
    args = _capture().cofold("NvidiaNIM_openfold3", "PEP", "RECEPTOR")["data"]["_args"]
    assert list(args) == ["inputs"] and len(args["inputs"]) == 1
    mols = args["inputs"][0]["molecules"]
    assert [m["sequence"] for m in mols] == ["PEP", "RECEPTOR"]
    assert all(m["type"] == "protein" for m in mols)


def test_cofold_boltz2_two_polymers_and_cyclic_flag():
    plain = _capture().cofold("NvidiaNIM_boltz2", "PEP", "REC")["data"]["_args"]
    assert [p["sequence"] for p in plain["polymers"]] == ["PEP", "REC"]
    assert "cyclic" not in plain["polymers"][0]
    cyc = _capture().cofold("NvidiaNIM_boltz2", "PEP", "REC", cyclic=True)["data"]["_args"]
    assert cyc["polymers"][0]["cyclic"] is True   # peptide cyclic
    assert "cyclic" not in cyc["polymers"][1]      # receptor not cyclic


def test_cofold_multimer_array_of_chains():
    args = _capture().cofold("NvidiaNIM_alphafold2_multimer", "PEP", "REC")["data"]["_args"]
    assert args == {"sequences": ["PEP", "REC"]}


def test_ortholog_sequence_uses_uniprot_path():
    tu = _FakeTU({
        "UniProt_search": {"results": [{"accession": "Q_MOUSE"}]},
        "UniProt_get_sequence_by_accession": "MOUSESEQ",
    })
    assert cs.CoFolder(tu).ortholog_sequence("GIPR", "mus_musculus") == "MOUSESEQ"
    # confirms it queried UniProt with the common-name organism filter
    assert any(n == "UniProt_search" and a["organism"] == "mouse" for n, a in tu.calls)
