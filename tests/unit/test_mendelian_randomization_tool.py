"""Unit tests for the two-sample MR estimators.

On noise-free instruments (outcome = theta * exposure) every estimator must
return theta exactly, the MR-Egger intercept must be 0, and Cochran's Q must be
0. Adding a constant pleiotropic offset must surface in the Egger intercept
while the Egger slope stays at theta. These pin the estimator math; the bootstrap
SE is checked for determinism (it is seeded).
"""

import math

import pytest

from tooluniverse.mendelian_randomization_tool import (
    MendelianRandomizationTool,
    _norm_p,
)

pytestmark = pytest.mark.unit

BX = [0.10, 0.20, 0.15, 0.30, 0.25, 0.18]
BXSE = [0.02, 0.03, 0.02, 0.03, 0.02, 0.03]
BYSE = [0.02, 0.02, 0.02, 0.03, 0.02, 0.02]
THETA = 0.5


def _tool():
    return MendelianRandomizationTool({"name": "mr"})


def _run(by):
    return _tool().run(
        {
            "beta_exposure": BX,
            "se_exposure": BXSE,
            "beta_outcome": by,
            "se_outcome": BYSE,
        }
    )


def test_recovers_known_causal_effect_no_pleiotropy():
    by = [THETA * b for b in BX]  # outcome = theta * exposure, exactly
    out = _run(by)
    assert out["status"] == "success"
    est = out["data"]["estimates"]
    assert math.isclose(est["ivw"]["estimate"], THETA, abs_tol=1e-9)
    assert math.isclose(est["mr_egger"]["estimate"], THETA, abs_tol=1e-9)
    assert math.isclose(est["weighted_median"]["estimate"], THETA, abs_tol=1e-9)
    # no directional pleiotropy -> intercept ~ 0
    assert abs(out["data"]["egger_intercept"]["estimate"]) < 1e-9
    # perfect fit -> no heterogeneity
    assert out["data"]["heterogeneity"]["cochran_q"] < 1e-9
    assert out["data"]["heterogeneity"]["i_squared"] == 0.0
    assert out["data"]["n_instruments"] == 6


def test_egger_intercept_detects_directional_pleiotropy():
    alpha = 0.03
    by = [alpha + THETA * b for b in BX]  # constant pleiotropic offset
    out = _run(by)
    data = out["data"]
    # Egger slope still recovers theta; intercept recovers the offset
    assert math.isclose(data["estimates"]["mr_egger"]["estimate"], THETA, abs_tol=1e-9)
    assert math.isclose(data["egger_intercept"]["estimate"], alpha, abs_tol=1e-9)
    # IVW (through-origin) is biased by the pleiotropy, away from theta
    assert data["estimates"]["ivw"]["estimate"] > THETA


def test_weighted_median_se_is_deterministic():
    by = [THETA * b for b in BX]
    se1 = _run(by)["data"]["estimates"]["weighted_median"]["se"]
    se2 = _run(by)["data"]["estimates"]["weighted_median"]["se"]
    assert se1 == se2 and se1 > 0  # seeded bootstrap -> reproducible


def test_normal_pvalue_helper():
    assert math.isclose(_norm_p(1.959964), 0.05, abs_tol=1e-4)
    assert math.isclose(_norm_p(0.0), 1.0, abs_tol=1e-9)


def test_errors_on_length_mismatch():
    out = _tool().run(
        {
            "beta_exposure": [0.1, 0.2, 0.3],
            "se_exposure": [0.02, 0.02, 0.02],
            "beta_outcome": [0.05, 0.1],
            "se_outcome": [0.02, 0.02],
        }
    )
    assert out["status"] == "error" and "same length" in out["error"]


def test_errors_on_too_few_instruments():
    out = _tool().run(
        {
            "beta_exposure": [0.1, 0.2],
            "se_exposure": [0.02, 0.02],
            "beta_outcome": [0.05, 0.1],
            "se_outcome": [0.02, 0.02],
        }
    )
    assert out["status"] == "error" and "3 instruments" in out["error"]


def test_errors_on_nonpositive_se():
    out = _tool().run(
        {
            "beta_exposure": BX,
            "se_exposure": BXSE,
            "beta_outcome": [THETA * b for b in BX],
            "se_outcome": [0.02, 0.0, 0.02, 0.03, 0.02, 0.02],
        }
    )
    assert out["status"] == "error" and "positive" in out["error"]


def test_errors_on_missing_array():
    out = _tool().run({"beta_exposure": BX})
    assert out["status"] == "error"
