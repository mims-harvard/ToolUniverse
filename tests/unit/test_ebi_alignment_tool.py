"""Unit tests for EBI alignment + phylogeny tools (network mocked, CI-safe).

Covers the logic the live EBI Job Dispatcher cannot exercise deterministically:
  - FASTA record counting / >=2 validation
  - per-method param mapping (clustalo outfmt+stype vs muscle format/no-stype)
  - dynamic result-type selection (only fetch types the job produced)
  - clustering-name normalization and boolean flag passing
  - error envelopes
"""

from unittest.mock import patch

from tooluniverse.ebi_alignment_tool import EBIMSATool, EBIPhylogenyTool


def _msa_cfg():
    return {"name": "EBI_msa_align", "type": "EBIMSATool",
            "parameter": {"type": "object", "properties": {}}}


def _phylo_cfg():
    return {"name": "EBI_build_phylogenetic_tree", "type": "EBIPhylogenyTool",
            "parameter": {"type": "object", "properties": {}}}


THREE = ">a\nMVLS\n>b\nMVHL\n>c\nMVLA"


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def test_msa_requires_two_records():
    out = EBIMSATool(_msa_cfg()).run({"sequences": ">only\nMVLS"})
    assert out["status"] == "error"
    assert ">=2" in out["error"]


def test_msa_rejects_unknown_method():
    out = EBIMSATool(_msa_cfg()).run({"sequences": THREE, "method": "bogus"})
    assert out["status"] == "error"
    assert "Unknown method" in out["error"]


def test_msa_rejects_bad_sequence_type():
    out = EBIMSATool(_msa_cfg()).run({"sequences": THREE, "sequence_type": "peptide"})
    assert out["status"] == "error"
    assert "sequence_type" in out["error"]


def test_phylo_requires_two_records():
    out = EBIPhylogenyTool(_phylo_cfg()).run({"aligned_sequences": ">only\n-MVLS"})
    assert out["status"] == "error"
    assert ">=2" in out["error"]


def test_phylo_rejects_bad_clustering():
    out = EBIPhylogenyTool(_phylo_cfg()).run({"aligned_sequences": THREE, "clustering": "ward"})
    assert out["status"] == "error"
    assert "clustering" in out["error"]


# --------------------------------------------------------------------------- #
# Per-method param mapping
# --------------------------------------------------------------------------- #
def test_clustalo_sends_outfmt_and_stype():
    captured = {}

    def fake_submit(service, params, timeout):
        captured["service"] = service
        captured["params"] = params
        return "job123", None

    with patch("tooluniverse.ebi_alignment_tool._submit", side_effect=fake_submit), \
         patch("tooluniverse.ebi_alignment_tool._poll", return_value=("FINISHED", None)), \
         patch("tooluniverse.ebi_alignment_tool._result_types", return_value=["fa"]), \
         patch("tooluniverse.ebi_alignment_tool._result", return_value=">a\nMV\n>b\nML"):
        out = EBIMSATool(_msa_cfg()).run({"sequences": THREE, "method": "clustalo", "sequence_type": "protein"})

    assert out["status"] == "success"
    assert captured["service"] == "clustalo"
    assert captured["params"]["outfmt"] == "fa"      # clustalo uses outfmt
    assert captured["params"]["stype"] == "protein"


def test_muscle_omits_stype_uses_format():
    captured = {}

    def fake_submit(service, params, timeout):
        captured["params"] = params
        return "j", None

    with patch("tooluniverse.ebi_alignment_tool._submit", side_effect=fake_submit), \
         patch("tooluniverse.ebi_alignment_tool._poll", return_value=("FINISHED", None)), \
         patch("tooluniverse.ebi_alignment_tool._result_types", return_value=["aln-fasta"]), \
         patch("tooluniverse.ebi_alignment_tool._result", return_value=">a\nMV"):
        out = EBIMSATool(_msa_cfg()).run({"sequences": THREE, "method": "muscle", "sequence_type": "dna"})

    assert out["status"] == "success"
    assert captured["params"]["format"] == "fasta"   # muscle uses format
    assert "stype" not in captured["params"]          # muscle has no stype


def test_dna_seqtype_maps_to_dna_for_stype_services():
    captured = {}
    with patch("tooluniverse.ebi_alignment_tool._submit",
               side_effect=lambda s, p, t: (captured.update(p) or "j", None)), \
         patch("tooluniverse.ebi_alignment_tool._poll", return_value=("FINISHED", None)), \
         patch("tooluniverse.ebi_alignment_tool._result_types", return_value=["fa"]), \
         patch("tooluniverse.ebi_alignment_tool._result", return_value=">a\nAC"):
        EBIMSATool(_msa_cfg()).run({"sequences": THREE, "method": "mafft", "sequence_type": "rna"})
    assert captured["stype"] == "dna"  # rna treated as dna for alignment


# --------------------------------------------------------------------------- #
# Dynamic result-type selection
# --------------------------------------------------------------------------- #
def test_msa_only_fetches_available_result_types():
    fetched = []

    def fake_result(service, job_id, rtype, timeout):
        fetched.append(rtype)
        return f"content-of-{rtype}"

    # Job produced only 'fa' (no clustal, no phylotree)
    with patch("tooluniverse.ebi_alignment_tool._submit", return_value=("j", None)), \
         patch("tooluniverse.ebi_alignment_tool._poll", return_value=("FINISHED", None)), \
         patch("tooluniverse.ebi_alignment_tool._result_types", return_value=["fa"]), \
         patch("tooluniverse.ebi_alignment_tool._result", side_effect=fake_result):
        out = EBIMSATool(_msa_cfg()).run({"sequences": THREE})

    assert out["data"]["aligned_fasta"] == "content-of-fa"
    assert out["data"]["alignment_clustal"] is None   # not produced -> None
    assert out["data"]["guide_tree_newick"] is None
    assert fetched == ["fa"]  # never tried to fetch unavailable types


def test_submit_error_is_propagated():
    with patch("tooluniverse.ebi_alignment_tool._submit", return_value=(None, "boom")):
        out = EBIMSATool(_msa_cfg()).run({"sequences": THREE})
    assert out["status"] == "error"
    assert out["error"] == "boom"


# --------------------------------------------------------------------------- #
# Phylogeny param construction
# --------------------------------------------------------------------------- #
def test_phylo_normalizes_clustering_and_flags():
    captured = {}
    with patch("tooluniverse.ebi_alignment_tool._submit",
               side_effect=lambda s, p, t: (captured.update(p) or "j", None)), \
         patch("tooluniverse.ebi_alignment_tool._poll", return_value=("FINISHED", None)), \
         patch("tooluniverse.ebi_alignment_tool._result", return_value="(a:0.1,b:0.2);"):
        out = EBIPhylogenyTool(_phylo_cfg()).run(
            {"aligned_sequences": THREE, "clustering": "nj", "distance_correction": True, "exclude_gaps": True}
        )
    assert out["status"] == "success"
    assert out["data"]["newick"] == "(a:0.1,b:0.2);"
    assert captured["clustering"] == "Neighbour-joining"  # 'nj' normalized
    assert captured["kimura"] == "true"
    assert captured["tossgaps"] == "true"
