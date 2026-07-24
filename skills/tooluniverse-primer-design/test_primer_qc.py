"""Tests for the primer-design skill helper script (primer QC)."""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import primer_qc as pq  # noqa: E402

pytestmark = pytest.mark.unit


def test_gc_content():
    assert pq.gc("GGCC") == pytest.approx(100.0)
    assert pq.gc("ATGC") == pytest.approx(50.0)


def test_longest_run():
    assert pq.longest_run("ATGC") == 1
    assert pq.longest_run("AAAACGT") == 4


def test_tm_increases_with_gc():
    at_rich = pq.tm_saltadj("ATATATATATATATATAT")
    gc_rich = pq.tm_saltadj("GCGCGCGCGCGCGCGCGC")
    assert gc_rich > at_rich


def test_tm_reasonable_for_18mer():
    # 18-mer, 50% GC should be ~48 C by the 64.9+41*... formula (a rough screen)
    tm = pq.tm_saltadj("CTACCTGAAGAACCTGAG")
    assert 40 < tm < 60


def test_three_prime_complement_detects_dimer():
    # 3'-to-3' geometry: a's 3' end (AAAGG) pairs with b's 3' end (TTTCC)
    # -> fully complementary -> max dimer score.
    assert pq.three_prime_complement("GGGGGAAAGG", "CCCCCTTTCC", window=5) == 5
    # 3' ends that are NOT complementary score low.
    assert pq.three_prime_complement("GGGGGAAAGG", "GGGGGAAAGG", window=5) < 5
