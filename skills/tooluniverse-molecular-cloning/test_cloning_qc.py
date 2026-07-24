"""Tests for the molecular-cloning skill helper script (assembly QC)."""

import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).parent / "scripts" / "cloning_qc.py"
sys.path.insert(0, str(SCRIPT.parent))
import cloning_qc as cq  # noqa: E402

pytestmark = pytest.mark.unit


def test_revcomp():
    assert cq.revcomp("ATGC") == "GCAT"
    assert cq.revcomp("GGTCTC") == "GAGACC"  # BsaI site / its reverse complement


def test_gc():
    assert cq.gc("GGCC") == pytest.approx(100.0)
    assert cq.gc("ATGC") == pytest.approx(50.0)


def test_internal_bsai_site_flagged():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--enzyme", "BsaI", "--parts", "ATGGCGGGTCTCAAAGCCC,CTGAGCGAGGAC"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "WARN" in out  # Part_1 has an internal GGTCTC
    assert "DOMESTICATE" in out
    assert "PASS" in out  # Part_2 is clean


def test_palindromic_overhang_flagged():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--overhangs", "AAAC,AATT"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "palindromic" in out  # AATT is self-complementary


def test_clean_overlaps_pass():
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--overlaps", "ATGGCGCCCAAGACGGGCTA,GAGGACGAGCTGCTGAAGCT"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "WARN" not in out  # both 20 bp, good GC
