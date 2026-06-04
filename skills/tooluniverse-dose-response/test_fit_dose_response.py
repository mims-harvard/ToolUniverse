"""Tests for the dose-response skill helper script (4PL Hill fit)."""

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import fit_dose_response as dr  # noqa: E402

pytestmark = pytest.mark.unit


def test_hill_4pl_endpoints():
    # f(x) = emin + (emax-emin)/(1+(ec50/x)^n); x->0 -> emin, x->inf -> emax
    assert dr.hill_4pl(1e-9, 0.0, 100.0, 1.0, 1.0) == pytest.approx(0.0, abs=1e-3)
    assert dr.hill_4pl(1e9, 0.0, 100.0, 1.0, 1.0) == pytest.approx(100.0, abs=1e-3)


def test_hill_4pl_at_ec50_is_midpoint():
    # at x = ec50, response is halfway between emin and emax
    assert dr.hill_4pl(5.0, 0.0, 100.0, 5.0, 1.5) == pytest.approx(50.0, rel=1e-6)


def test_fit_recovers_known_ic50(tmp_path):
    # generate a clean inhibition curve with EC50=1, then fit it back
    from scipy.optimize import curve_fit

    conc = np.array([0.01, 0.1, 1, 10, 100], dtype=float)
    true = (5.0, 95.0, 1.0, 1.0)  # emin, emax, ec50, n
    resp = dr.hill_4pl(conc, *true)
    popt, _ = curve_fit(dr.hill_4pl, conc, resp, p0=[0, 100, 0.5, 1], maxfev=20000)
    assert popt[2] == pytest.approx(1.0, rel=1e-3)  # EC50 recovered
