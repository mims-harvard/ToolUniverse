"""Unit tests for GSVA (gene set variation analysis).

GSVA scores are signed and centered near zero (mx_diff default). A set whose
genes are the most up-regulated in a sample (relative to the cohort) must score
positive there and negative in a sample where they are down-regulated; the two
must have opposite sign for the same set across two anti-correlated samples. The
math is deterministic, so results are reproducible. Numerical agreement with the
reference implementation (R/Bioconductor GSVA, via decoupler) is checked
separately in the validation script, not here (no heavy deps in CI).
"""

import numpy as np
import pytest

from tooluniverse.gsva_tool import GSVATool, _phi, _rankdata_avg

pytestmark = pytest.mark.unit


def _tool():
    return GSVATool({"name": "gsva"})


# A 12-gene, 2-sample matrix: in "tumor" G1..G4 are highest, in "normal" lowest.
RAMP = {f"G{i}": [13 - i, i] for i in range(1, 13)}


def test_top_set_positive_in_tumor_negative_in_normal():
    out = _tool().run(
        {"expression": RAMP, "samples": ["tumor", "normal"], "gene_set": ["G1", "G2", "G3", "G4"]}
    )
    assert out["status"] == "success"
    scores = out["data"]["enrichment_scores"]["gene_set"]
    assert scores["tumor"] > 0 and scores["normal"] < 0


def test_scores_are_reproducible():
    a = _tool().run({"expression": RAMP, "gene_set": ["G1", "G2", "G3"]})
    b = _tool().run({"expression": RAMP, "gene_set": ["G1", "G2", "G3"]})
    assert a["data"]["enrichment_scores"] == b["data"]["enrichment_scores"]


def test_mx_diff_false_uses_single_max_deviation():
    out = _tool().run(
        {"expression": RAMP, "gene_set": ["G1", "G2", "G3", "G4"], "mx_diff": False}
    )
    # classic KS statistic is a single deviation -> magnitude >= |mx_diff score|
    diff = _tool().run({"expression": RAMP, "gene_set": ["G1", "G2", "G3", "G4"]})
    s_ks = out["data"]["enrichment_scores"]["gene_set"]["sample_1"]
    s_diff = diff["data"]["enrichment_scores"]["gene_set"]["sample_1"]
    assert abs(s_ks) >= abs(s_diff) - 1e-9


def test_multiple_sets_and_skipped():
    out = _tool().run(
        {
            "expression": RAMP,
            "gene_sets": {"UP": ["G1", "G2", "G3"], "TINY": ["G1", "NOPE"]},
        }
    )
    assert "UP" in out["data"]["enrichment_scores"]
    assert "TINY" in out["data"]["skipped_sets"]


def test_duplicate_members_are_deduped():
    clean = _tool().run({"expression": RAMP, "gene_set": ["G1", "G2", "G3", "G4"]})
    dup = _tool().run({"expression": RAMP, "gene_set": ["G1", "G1", "G2", "G2", "G3", "G4"]})
    assert (
        clean["data"]["enrichment_scores"]["gene_set"]
        == dup["data"]["enrichment_scores"]["gene_set"]
    )


def test_constant_gene_does_not_crash():
    expr = {f"G{i}": [float(i), float(i)] for i in range(1, 13)}
    expr["G1"] = [5.0, 5.0]  # zero variance across samples -> bandwidth 0 branch
    out = _tool().run({"expression": expr, "gene_set": ["G1", "G2", "G3"]})
    assert out["status"] == "success"


def test_phi_matches_known_values():
    assert _phi(np.array([0.0]))[0] == pytest.approx(0.5, abs=1e-6)
    assert _phi(np.array([1.959964]))[0] == pytest.approx(0.975, abs=1e-5)
    assert _phi(np.array([-1.959964]))[0] == pytest.approx(0.025, abs=1e-5)


def test_rankdata_avg_handles_ties():
    # values 10,10,20 -> ranks 1.5,1.5,3
    np.testing.assert_allclose(_rankdata_avg(np.array([10.0, 10.0, 20.0])), [1.5, 1.5, 3.0])


def test_errors():
    assert _tool().run({})["status"] == "error"  # no expression
    assert _tool().run({"expression": {"G1": [1.0]}})["status"] == "error"  # one sample
    short = {f"G{i}": [1.0, 2.0] for i in range(1, 5)}  # < 10 genes
    assert _tool().run({"expression": short, "gene_set": ["G1"]})["status"] == "error"
    assert _tool().run({"expression": RAMP})["status"] == "error"  # no gene set
