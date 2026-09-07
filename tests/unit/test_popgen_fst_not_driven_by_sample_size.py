"""Regression guard: PopGen_fst's denominator omitted the Weir & Cockerham
(1984) (n_c - 1) sample-size-correction factor on MSG, so the reported Fst
was a monotone function of sample size rather than of allele-frequency
divergence -- identical p1/p2 gave "little" differentiation at n=50 but
"very great" at n=10000.

Formula restored (Weir & Cockerham 1984, Evolution 38(6):1358-1370):
    MSP = n1*(p1-p_bar)^2 + n2*(p2-p_bar)^2                (df = r-1 = 1)
    MSG = (n1*p1*(1-p1) + n2*p2*(1-p2)) / (n1+n2-2)
    n_c = (n1+n2) - (n1^2+n2^2)/(n1+n2)
    theta = (MSP - MSG) / (MSP + (n_c - 1) * MSG)
"""

import pytest

from tooluniverse.popgen_tool import PopGenTool

pytestmark = pytest.mark.unit


def _tool():
    return PopGenTool({"name": "popgen_test"})


def _fst(p1, p2, n1, n2):
    tool = _tool()
    result = tool.run(
        {"operation": "fst", "p1": p1, "p2": p2, "n1": n1, "n2": n2}
    )
    assert result["status"] == "success"
    return result["data"]


def test_identical_frequencies_not_driven_by_sample_size():
    small = _fst(0.4, 0.45, 50, 50)
    large = _fst(0.4, 0.45, 10000, 10000)

    # Both must land in the same "little differentiation" bucket, unlike
    # the old code where n=10000 spuriously jumped to ~0.96.
    assert small["Fst"] < 0.05
    assert large["Fst"] < 0.05
    assert abs(small["Fst"] - large["Fst"]) < 0.05

    assert "Little" in small["interpretation"]
    assert "Little" in large["interpretation"]

    # New estimator is self-describing.
    assert "Weir-Cockerham" in small["estimator"]
    assert "n_c" in small["estimator"] or "sample-size" in small["estimator"]


def test_large_divergence_large_n_is_moderate_not_saturated_at_one():
    data = _fst(0.2, 0.8, 1_000_000, 1_000_000)
    # Correct Weir-Cockerham theta here is ~0.529, not the old code's 1.0000.
    assert data["Fst"] == pytest.approx(0.5294, abs=0.001)
    assert data["Fst"] < 0.99


def test_identical_frequencies_unequal_sample_sizes_near_zero():
    data = _fst(0.5, 0.5, 100, 200)
    assert data["Fst"] == pytest.approx(0.0, abs=1e-9)


def test_fixed_allele_still_returns_zero():
    data = _fst(0.0, 0.0, 100, 100)
    assert data["Fst"] == 0.0
    assert "fixed or absent" in data["interpretation"]


def test_hand_computed_unequal_n_matches_weir_cockerham_formula():
    # p1=0.1, p2=0.9, n1=40, n2=60 hand-derivation:
    # p_bar = 0.58, MSP = 15.36, MSG = 9/98 = 0.091837,
    # n_c = 100 - 5200/100 = 48, theta = (15.36-0.091837)/(15.36+47*0.091837)
    #     = 15.268163/19.676351 = 0.77602...
    data = _fst(0.1, 0.9, 40, 60)
    assert data["Fst"] == pytest.approx(0.7760, abs=0.001)
