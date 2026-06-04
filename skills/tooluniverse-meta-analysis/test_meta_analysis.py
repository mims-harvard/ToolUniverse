"""Tests for the meta-analysis skill helper script.

Validates the error-prone effect-size conversions and the pooling math
(fixed + DerSimonian-Laird random effects), independent of the
MetaAnalysis_run tool. Run: pytest skills/tooluniverse-meta-analysis/
"""

import math
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import meta_analysis as ma  # noqa: E402

pytestmark = pytest.mark.unit


def test_ratio_ci_to_log_and_se():
    eff, se, is_ratio = ma._row_to_effect(
        {"name": "S", "or": "1.51", "ci_low": "1.20", "ci_high": "1.90"}
    )
    assert is_ratio
    assert eff == pytest.approx(math.log(1.51), rel=1e-6)
    assert se == pytest.approx((math.log(1.90) - math.log(1.20)) / (2 * 1.96), rel=1e-6)


def test_beta_se_passthrough():
    eff, se, is_ratio = ma._row_to_effect({"name": "S", "beta": "0.4", "se": "0.1"})
    assert not is_ratio
    assert (eff, se) == (0.4, 0.1)


def test_hedges_g_sign_and_correction():
    eff, se, _ = ma._row_to_effect(
        {"name": "S", "mean1": "10", "sd1": "2", "n1": "20", "mean2": "8", "sd2": "2", "n2": "20"}
    )
    assert eff > 0  # group 1 higher
    assert eff < 1.0  # Hedges' g < raw Cohen's d (small-sample correction)
    assert se > 0


def test_fisher_z():
    eff, se, _ = ma._row_to_effect({"name": "S", "r": "0.5", "n": "28"})
    assert eff == pytest.approx(math.atanh(0.5), rel=1e-6)
    assert se == pytest.approx(1 / math.sqrt(28 - 3), rel=1e-6)


def test_pool_matches_inverse_variance_fixed():
    effects = [0.5, 0.7, 0.3]
    ses = [0.1, 0.15, 0.12]
    pooled, pse, w, Q, df, I2, tau2 = ma.pool(effects, ses, "fixed")
    # inverse-variance weighted mean
    wi = [1 / s**2 for s in ses]
    expect = sum(e * x for e, x in zip(effects, wi)) / sum(wi)
    assert pooled == pytest.approx(expect, rel=1e-9)
    assert abs(sum(w) - 100) < 1e-6  # weights are percentages


def test_random_effects_widens_or_equals_fixed_se():
    effects = [0.5, 0.9, 0.2]
    ses = [0.1, 0.1, 0.1]
    _, pse_fixed, *_ = ma.pool(effects, ses, "fixed")
    _, pse_rand, *_ = ma.pool(effects, ses, "random")
    assert pse_rand >= pse_fixed - 1e-9  # random adds between-study variance


def test_unrecognized_row_raises():
    with pytest.raises(ValueError):
        ma._row_to_effect({"name": "S", "foo": "1"})
