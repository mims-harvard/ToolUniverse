"""Unit tests for the coloc.abf colocalization tool.

Two signals peaking at the SAME SNP must yield a high PP4 (shared causal
variant); peaking at DIFFERENT SNPs must yield a high PP3 (distinct variants);
a signal in only one trait must yield a high PP1/PP2. The posteriors must sum to
1. These pin the approximate-Bayes-factor combination.
"""

import math

import pytest

from tooluniverse.colocalization_tool import ColocalizationTool, _logdiff

pytestmark = pytest.mark.unit

SE = [0.02] * 6
WEAK = [0.01, 0.02, 0.03, 0.02, 0.04, 0.01]  # no strong signal


def _tool():
    return ColocalizationTool({"name": "coloc"})


def _run(beta1, beta2, **extra):
    return _tool().run(
        {"beta1": beta1, "se1": SE, "beta2": beta2, "se2": SE, **extra}
    )


def test_shared_peak_gives_high_pp4():
    # both traits peak strongly at SNP index 3
    b1 = [0.01, 0.02, 0.03, 0.20, 0.04, 0.01]
    b2 = [0.02, 0.01, 0.04, 0.18, 0.03, 0.02]
    out = _run(b1, b2, snp=["rs1", "rs2", "rs3", "rs4", "rs5", "rs6"])
    assert out["status"] == "success"
    d = out["data"]
    assert d["pp4_colocalization"] > 0.8
    assert d["best_causal_snp"] == "rs4"  # the shared peak
    assert "colocalization" in d["interpretation"]
    assert math.isclose(sum(d["posteriors"].values()), 1.0, abs_tol=1e-9)


def test_distinct_peaks_give_high_pp3():
    b1 = [0.01, 0.20, 0.03, 0.02, 0.04, 0.01]  # trait 1 peaks at idx 1
    b2 = [0.02, 0.01, 0.04, 0.02, 0.20, 0.02]  # trait 2 peaks at idx 4
    out = _run(b1, b2)
    d = out["data"]
    assert d["posteriors"]["PP3"] > 0.8  # both causal, different SNPs
    assert d["pp4_colocalization"] < 0.1


def test_signal_in_one_trait_only_gives_high_pp1():
    b1 = [0.01, 0.02, 0.03, 0.22, 0.04, 0.01]  # trait 1 has a strong signal
    out = _run(b1, WEAK)  # trait 2 is null
    d = out["data"]
    assert d["posteriors"]["PP1"] > 0.8
    assert d["pp4_colocalization"] < 0.1


def test_posteriors_sum_to_one_and_priors_echoed():
    out = _run([0.05] * 6, [0.05] * 6, p12=2e-5)
    assert math.isclose(sum(out["data"]["posteriors"].values()), 1.0, abs_tol=1e-9)
    assert out["metadata"]["priors"]["p12"] == 2e-5


def test_logdiff_matches_definition():
    a, b = 2.0, 1.0
    assert math.isclose(_logdiff(a, b), math.log(math.exp(a) - math.exp(b)), abs_tol=1e-12)


def test_errors_on_length_mismatch():
    out = _tool().run({"beta1": [0.1, 0.2], "se1": [0.02, 0.02], "beta2": [0.1], "se2": [0.02]})
    assert out["status"] == "error" and "same length" in out["error"]


def test_errors_on_nonpositive_se():
    out = _tool().run(
        {"beta1": [0.1, 0.2], "se1": [0.02, 0.0], "beta2": [0.1, 0.2], "se2": [0.02, 0.02]}
    )
    assert out["status"] == "error" and "positive" in out["error"]


def test_errors_on_missing_array():
    assert _tool().run({"beta1": [0.1, 0.2]})["status"] == "error"
