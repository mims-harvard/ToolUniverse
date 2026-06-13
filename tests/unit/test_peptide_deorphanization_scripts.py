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


# ------------- generality: target-class router (A) --------------------------

def test_classify_gpcr_ligand_from_prosite_text():
    out = dp._classify_target_class([{"description": "Glucagon / GIP / secretin / VIP family signature"}], [], "HGEGTFTSD")
    assert out["target_class"] == "gpcr_ligand" and out["seedless_nouns"] == ["receptor"]


def test_classify_ion_channel_toxin_from_homology_and_from_cysteine_density():
    by_text = dp._classify_target_class([], ["Omega-conotoxin GVIA"], "CKSPGSSCS")
    assert by_text["target_class"] == "ion_channel_toxin"
    # no keyword, but cysteine-rich short peptide -> disulfide toxin fallback
    by_cys = dp._classify_target_class([], ["Hypothetical protein"], "GCCSDPRCNMNNPDYCG")
    assert by_cys["target_class"] == "ion_channel_toxin"
    assert "cysteine-rich" in by_cys["evidence"][0]


def test_classify_integrin_by_rgd_and_protease_by_text_and_unknown_default():
    assert dp._classify_target_class([], [], "GRGDSPK")["target_class"] == "integrin_ligand"
    prot = dp._classify_target_class([{"description": "Kunitz/BPTI protease inhibitor domain"}], [], "RPDFCLE")
    assert prot["target_class"] == "protease_inhibitor_or_substrate"
    assert prot["seedless_nouns"] == ["protease", "peptidase"]
    unk = dp._classify_target_class([], ["Uncharacterized protein"], "MKTAYIAKQR")
    assert unk["target_class"] == "unknown" and "receptor" in unk["seedless_nouns"]


# ------------- generality: seedless beyond "receptor" (C) -------------------

def test_family_keywords_drawn_from_homology_not_only_signatures():
    # a peptide with NO PROSITE signature still seeds keywords from its BLAST hits
    kws = dp.Pipeline._family_keywords([], ["Voltage-gated potassium channel subfamily"])
    assert "potassium" in kws and "voltage" in kws
    assert "protein" not in kws  # generic stopwords are dropped


def test_seedless_seeds_finds_non_receptor_targets():
    """A channel-class peptide must seed channels, not be limited to receptors."""
    def _search(args):
        # only the 'potassium channel' query returns a channel gene
        if "channel" in args["query"]:
            return {"results": [{"protein_name": "Potassium voltage-gated channel KCNA1", "gene_names": ["KCNA1"]}]}
        return {"results": []}
    tu = _FakeTU({"UniProt_search": _search})
    out = dp.Pipeline(tu).seedless_seeds(
        [{"description": "potassium channel toxin"}], nouns=["channel", "receptor"], homology_defs=[]
    )
    assert "KCNA1" in out["seeds"] and out["nouns"] == ["channel", "receptor"]


# ------------- generality: InterPro universal family route (B) --------------

# InterPro live shape: proteins carry UniProt `accession` + `tax_id` (no gene
# field) and mix organisms; symbols come from a batch UniProt accession->gene map.
_IPR_ENTRIES = {"entries": [
    {"type": "family", "accession": "IPR000001"},
    {"type": "domain", "accession": "IPR999999"},  # domains/superfamilies ignored
]}


def test_interpro_family_members_filters_human_and_maps_accessions_to_symbols():
    tu = _FakeTU({
        "InterPro_get_entries_for_protein": _IPR_ENTRIES,
        "InterPro_get_proteins_by_domain": {"proteins": [
            {"accession": "P1", "tax_id": "9606"},
            {"accession": "P2", "tax_id": "9606"},
            {"accession": "P3", "tax_id": "7460"},  # honeybee -> filtered out
        ]},
        "UniProt_search": {"results": [
            {"accession": "P1", "gene_names": ["AAA"]},
            {"accession": "P2", "gene_names": ["BBB"]},
        ]},
    })
    members = dp.Pipeline(tu).interpro_family_members("P12345")
    assert members == ["AAA", "BBB"]
    # only the FAMILY entry is enumerated, not the domain entry
    iprs = [a["domain_id"] for n, a in tu.calls if n == "InterPro_get_proteins_by_domain"]
    assert iprs == ["IPR000001"]
    # the non-human accession is not sent to the batch symbol mapper
    uq = next(a["query"] for n, a in tu.calls if n == "UniProt_search")
    assert "P1" in uq and "P2" in uq and "P3" not in uq


def test_family_panel_interpro_supplies_panel_when_no_hgnc_group():
    """For a target with no curated HGNC group, InterPro provides the family."""
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": ["P2"]},  # no gene_group_id
        "GPCRdb_get_protein": {},                               # not a GPCR
        "InterPro_get_entries_for_protein": {"entries": [{"type": "family", "accession": "IPR0NPR"}]},
        "InterPro_get_proteins_by_domain": {"proteins": [
            {"accession": "Q1", "tax_id": "9606"}, {"accession": "Q2", "tax_id": "9606"}, {"accession": "Q3", "tax_id": "9606"},
        ]},
        "UniProt_search": {"results": [
            {"accession": "Q1", "gene_names": ["NPR1"]}, {"accession": "Q2", "gene_names": ["NPR2"]}, {"accession": "Q3", "gene_names": ["NPR3"]},
        ]},
    })
    panel = dp.Pipeline(tu).family_panel("NPR1")["panel"]
    assert set(panel) == {"NPR1", "NPR2", "NPR3"}
    assert panel["NPR2"]["sources"] == ["InterPro"]


def test_family_panel_hgnc_authoritative_interpro_only_annotates():
    """When HGNC grouped the family, InterPro annotates members but adds no outsiders."""
    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"hgnc_id": "HGNC:1", "uniprot_ids": ["P1"], "gene_group_id": ["100"]},
        "HGNC_fetch_gene_family_members": [{"symbol": "GLP1R"}, {"symbol": "GCGR"}],
        "GPCRdb_get_protein": {},
        "InterPro_get_entries_for_protein": {"entries": [{"type": "family", "accession": "IPR0G"}]},
        "InterPro_get_proteins_by_domain": {"proteins": [
            {"accession": "A1", "tax_id": "9606"}, {"accession": "A2", "tax_id": "9606"}, {"accession": "A3", "tax_id": "9606"},
        ]},
        "UniProt_search": {"results": [
            {"accession": "A1", "gene_names": ["GCGR"]}, {"accession": "A2", "gene_names": ["OUTSIDER1"]}, {"accession": "A3", "gene_names": ["OUTSIDER2"]},
        ]},
    })
    panel = dp.Pipeline(tu).family_panel("GLP1R")["panel"]
    assert set(panel) == {"GLP1R", "GCGR"}                 # no OUTSIDER leaked in
    assert "InterPro" in panel["GCGR"]["sources"]          # but GCGR cross-checked
    assert "HGNC" in panel["GCGR"]["sources"]


def test_family_panel_skips_oversized_hgnc_supergroup():
    """A domain supergroup (e.g. 'EF-hand', ~200 genes) must NOT flood the panel;
    only the bounded target-family group is enumerated."""
    big = [{"symbol": f"EF{i}"} for i in range(201)]  # over _HGNC_GROUP_CAP

    def _members(args):
        return big if args["gene_group_id"] == "863" else [{"symbol": "CACNA1B"}, {"symbol": "CACNA1A"}]

    tu = _FakeTU({
        "HGNC_fetch_gene_by_symbol": {"uniprot_ids": [None], "gene_group_id": ["863", "100"]},
        "HGNC_fetch_gene_family_members": _members,
        "GPCRdb_get_protein": {},
    })
    out = dp.Pipeline(tu).family_panel("CACNA1B")
    assert set(out["panel"]) == {"CACNA1B", "CACNA1A"}  # the EF-hand supergroup is skipped
    assert out["meta"]["skipped_broad_groups"][0]["gene_group_id"] == "863"
