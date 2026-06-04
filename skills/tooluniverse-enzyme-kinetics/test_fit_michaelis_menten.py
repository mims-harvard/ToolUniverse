"""Tests for the enzyme-kinetics skill helper script (Michaelis-Menten fit)."""

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import fit_michaelis_menten as ek  # noqa: E402

pytestmark = pytest.mark.unit


def test_mm_at_km_is_half_vmax():
    # v = Vmax*[S]/(Km+[S]); at [S]=Km, v = Vmax/2
    assert ek.mm(5.0, 100.0, 5.0) == pytest.approx(50.0, rel=1e-9)


def test_mm_saturates_to_vmax():
    assert ek.mm(1e9, 100.0, 5.0) == pytest.approx(100.0, rel=1e-6)


def test_fit_recovers_km_vmax():
    from scipy.optimize import curve_fit

    s = np.array([0.1, 0.25, 0.5, 1, 2, 5, 10], dtype=float)
    v = ek.mm(s, 120.0, 1.5)  # true Vmax=120, Km=1.5
    popt, _ = curve_fit(ek.mm, s, v, p0=[100, 1], maxfev=20000, bounds=(0, np.inf))
    assert popt[0] == pytest.approx(120.0, rel=1e-3)  # Vmax
    assert popt[1] == pytest.approx(1.5, rel=1e-3)  # Km
