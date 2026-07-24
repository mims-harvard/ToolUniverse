"""Unit tests for single-causal ABF fine-mapping.

A single dominant SNP must take nearly all the posterior (PIP~1, credible set of
one); two equally strong SNPs must split the posterior (~0.5 each, credible set
of two). PIPs must sum to 1 and the credible set must reach the requested
coverage. These pin the Wakefield-ABF PIP computation.
"""

import math

import pytest

from tooluniverse.finemap_abf_tool import FinemapABFTool

pytestmark = pytest.mark.unit

SE6 = [0.02] * 6


def _tool():
    return FinemapABFTool({"name": "fm"})


def test_single_dominant_snp_gets_high_pip():
    beta = [0.02, 0.03, 0.25, 0.04, 0.02, 0.05]  # SNP index 2 dominates
    out = _tool().run({"beta": beta, "se": SE6, "snp": ["a", "b", "c", "d", "e", "f"]})
    assert out["status"] == "success"
    d = out["data"]
    assert d["top_snp"] == "c" and d["top_pip"] > 0.95
    assert d["credible_set_size"] == 1
    assert math.isclose(sum(d["pip"].values()), 1.0, abs_tol=1e-9)


def test_two_equal_snps_split_posterior():
    beta = [0.01, 0.25, 0.02, 0.25, 0.01, 0.02]  # SNPs 1 and 3 equally strong
    out = _tool().run({"beta": beta, "se": SE6})
    d = out["data"]
    pips = sorted(d["pip"].values(), reverse=True)
    assert math.isclose(pips[0], pips[1], rel_tol=1e-6)  # tied
    assert math.isclose(pips[0], 0.5, abs_tol=0.05)
    assert d["credible_set_size"] == 2


def test_credible_set_reaches_coverage():
    beta = [0.10, 0.11, 0.09, 0.10, 0.10, 0.11]  # diffuse signal
    out = _tool().run({"beta": beta, "se": SE6, "coverage": 0.95})
    d = out["data"]
    assert d["credible_set_coverage"] >= 0.95
    assert d["credible_set_size"] >= 2


def test_errors_on_length_mismatch():
    out = _tool().run({"beta": [0.1, 0.2, 0.3], "se": [0.02, 0.02]})
    assert out["status"] == "error" and "same length" in out["error"]


def test_errors_on_nonpositive_se():
    out = _tool().run({"beta": [0.1, 0.2], "se": [0.02, 0.0]})
    assert out["status"] == "error" and "positive" in out["error"]


def test_errors_on_bad_coverage():
    out = _tool().run({"beta": [0.1, 0.2], "se": [0.02, 0.02], "coverage": 1.5})
    assert out["status"] == "error" and "coverage" in out["error"]
