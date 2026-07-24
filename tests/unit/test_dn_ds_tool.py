"""Unit tests for the dN/dS (Ka/Ks) tool (Nei-Gojobori, pure Python).

Tests pin the selection-direction interpretation on hand-constructed sequence
pairs (purifying, identical, all-synonymous), the codon math, FASTA input, and
the error paths. No external dependency, so no skip guard.
"""

import pytest

from tooluniverse.dn_ds_tool import DnDsTool

pytestmark = pytest.mark.unit

# 12 codons (M A K F E D L S T V R G). seq2: 3 synonymous (3rd-pos) + 1
# nonsynonymous (GAT->AAT, Asp->Asn) change -> dN/dS << 1 (purifying).
S1 = "ATGGCCAAATTTGAAGATCTGAGCACCGTGCGTGGC"
S2 = "ATGGCCAAGTTCGAAAATCTGAGCACCGTACGTGGC"


def _tool():
    return DnDsTool(
        {"name": "dnds", "type": "DnDsTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_purifying_selection_ratio():
    """Mostly-synonymous divergence yields a small, finite dN/dS (purifying)."""
    out = _tool().run({"seq1": S1, "seq2": S2})
    assert out["status"] == "success"
    d = out["data"]
    assert d["codons_compared"] == 12
    assert d["Nd"] == 1.0 and d["Sd"] == 3.0
    assert 0 < d["dN_dS"] < 1
    assert "purifying" in d["interpretation"]


def test_identical_sequences_undetermined():
    """No substitutions -> dN/dS is undetermined (not a crash)."""
    out = _tool().run({"seq1": S1, "seq2": S1})
    assert out["status"] == "success"
    assert out["data"]["dN_dS"] is None
    assert out["data"]["Nd"] == 0.0 and out["data"]["Sd"] == 0.0


def test_only_synonymous_gives_zero_dn():
    """Purely synonymous changes -> dN = 0."""
    # AAA->AAG (Lys, syn) and TTT->TTC (Phe, syn) only.
    out = _tool().run({"seq1": "ATGAAATTT", "seq2": "ATGAAGTTC"})
    assert out["status"] == "success"
    assert out["data"]["dN"] == 0.0


def test_rna_and_lowercase_accepted():
    """U is mapped to T and lowercase is upper-cased."""
    out = _tool().run({"seq1": "augaaauuu", "seq2": "augaaguuc"})
    assert out["status"] == "success"
    assert out["data"]["codons_compared"] == 3


def test_ragged_lengths_truncated_to_codon():
    """Unequal lengths are truncated to the shorter codon-aligned length."""
    out = _tool().run({"seq1": S1 + "AT", "seq2": S2})  # 2 extra bases on seq1
    assert out["status"] == "success"
    assert out["data"]["codons_compared"] == 12


def test_fasta_input(tmp_path):
    """Sequences can be read from single-record FASTA files."""
    f1, f2 = tmp_path / "a.fa", tmp_path / "b.fa"
    f1.write_text(">a\n" + S1 + "\n")
    f2.write_text(">b\n" + S2 + "\n")
    out = _tool().run({"fasta1_path": str(f1), "fasta2_path": str(f2)})
    assert out["status"] == "success"
    assert 0 < out["data"]["dN_dS"] < 1


# --- error paths ----------------------------------------------------------- #
def test_missing_sequences_is_error():
    """No sequences provided -> clean error."""
    out = _tool().run({"seq1": S1})
    assert out["status"] == "error"


def test_non_nucleotide_is_error():
    """Non-ACGTU characters are rejected."""
    out = _tool().run({"seq1": "ATGXYZ", "seq2": "ATGAAA"})
    assert out["status"] == "error" and "nucleotide" in out["error"]


def test_too_short_is_error():
    """Fewer than one codon -> error."""
    out = _tool().run({"seq1": "AT", "seq2": "AT"})
    assert out["status"] == "error"


def test_missing_one_fasta_is_error():
    """Only one FASTA path provided -> error."""
    out = _tool().run({"fasta1_path": "/tmp/x.fa"})
    assert out["status"] == "error"
