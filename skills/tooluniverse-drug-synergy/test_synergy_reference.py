"""Tests for the drug-synergy skill helper script."""

import pathlib
import subprocess
import sys

import pytest

SCRIPT = pathlib.Path(__file__).parent / "scripts" / "synergy_reference.py"
sys.path.insert(0, str(SCRIPT.parent))
import synergy_reference as sr  # noqa: E402

pytestmark = pytest.mark.unit


def test_call_thresholds():
    assert sr._call(0.2) == "synergy"
    assert sr._call(0.0) == "additive"
    assert sr._call(-0.2) == "antagonism"
    # boundary: just inside +/-0.10 is additive
    assert sr._call(0.10) == "additive"
    assert sr._call(0.11) == "synergy"


def test_bliss_expected_matches_tool():
    # Bliss: E_exp = ea + eb - ea*eb; for 0.4,0.3 -> 0.58, score (0.7-0.58)=0.12
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--ea", "0.4", "--eb", "0.3", "--ecombo", "0.7"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "0.580" in out  # Bliss expected
    assert "0.120" in out  # Bliss synergy score (matches DrugSynergy_calculate_bliss)
    assert "synergy" in out


def test_rejects_out_of_range_fraction():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--ea", "40", "--eb", "0.3", "--ecombo", "0.7"],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "fraction" in (r.stderr + r.stdout).lower()
