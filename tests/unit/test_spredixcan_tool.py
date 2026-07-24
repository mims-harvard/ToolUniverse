"""Unit tests for S-PrediXcan summary-based TWAS.

For independent SNPs the gene z-score is sum(w*sigma*z)/sqrt(sum((w*sigma)^2)),
which is exact and hand-checkable. A supplied covariance changes the denominator.
Concordant weights and z-scores give a large positive z; opposing signs cancel.
"""

import math

import pytest

from tooluniverse.spredixcan_tool import SPrediXcanTool, _norm_p

pytestmark = pytest.mark.unit


def _tool():
    return SPrediXcanTool({"name": "spx"})


def test_independent_snps_matches_closed_form():
    w = [0.5, 0.3, 0.2, 0.4, 0.25]
    z = [3.0, 2.0, 1.0, 2.5, 1.5]
    out = _tool().run({"weight": w, "gwas_z": z})
    assert out["status"] == "success"
    num = sum(wi * zi for wi, zi in zip(w, z))
    den = math.sqrt(sum(wi**2 for wi in w))
    assert math.isclose(out["data"]["twas_zscore"], num / den, rel_tol=1e-9)
    assert out["data"]["twas_zscore"] > 0 and out["data"]["p_value"] < 0.05
    assert out["data"]["n_snps"] == 5


def test_opposing_signs_cancel():
    out = _tool().run({"weight": [1.0, 1.0, 1.0, 1.0], "gwas_z": [2.0, -2.0, 2.0, -2.0]})
    assert abs(out["data"]["twas_zscore"]) < 1e-9


def test_snp_sd_scales_contributions():
    base = _tool().run({"weight": [1.0, 1.0, 1.0], "gwas_z": [2.0, 2.0, 2.0]})["data"]["twas_zscore"]
    # equal sds -> same z (sd cancels in num/den when uniform)
    scaled = _tool().run(
        {"weight": [1.0, 1.0, 1.0], "gwas_z": [2.0, 2.0, 2.0], "snp_sd": [2.0, 2.0, 2.0]}
    )["data"]["twas_zscore"]
    assert math.isclose(base, scaled, rel_tol=1e-9)


def test_covariance_changes_denominator():
    w = [1.0, 1.0]
    z = [2.0, 2.0]
    indep = _tool().run({"weight": w, "gwas_z": z})["data"]["twas_zscore"]
    # positively-correlated SNPs inflate w^T Gamma w -> smaller z than independent
    corr = _tool().run({"weight": w, "gwas_z": z, "covariance": [[1.0, 0.8], [0.8, 1.0]]})["data"]["twas_zscore"]
    assert corr < indep


def test_covariance_diagonal_supplies_sigma_when_snp_sd_omitted():
    """sigma must come from sqrt(diag(cov)) so numerator and denominator agree."""
    out = _tool().run({"weight": [1.0, 1.0], "gwas_z": [2.0, 2.0], "covariance": [[4.0, 0.0], [0.0, 4.0]]})
    # num = sum(w*2*z) = 8; den = sqrt(w^T cov w) = sqrt(8) -> z = 8/sqrt(8) = sqrt(8)
    assert math.isclose(out["data"]["twas_zscore"], math.sqrt(8.0), rel_tol=1e-9)


def test_normal_p_helper():
    assert math.isclose(_norm_p(1.959964), 0.05, abs_tol=1e-4)


def test_errors():
    assert _tool().run({"weight": [0.5]})["status"] == "error"  # no gwas_z / too few
    assert _tool().run({"weight": [0.5, 0.3], "gwas_z": [1.0]})["status"] == "error"  # mismatch
    out = _tool().run({"weight": [0.5, 0.3], "gwas_z": [1.0, 2.0], "covariance": [[1.0]]})
    assert out["status"] == "error" and "matrix" in out["error"]
