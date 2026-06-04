"""Tests for the pharmacokinetics skill helper script (NCA)."""

import math
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import nca_from_csv as nca  # noqa: E402

pytestmark = pytest.mark.unit


def test_auc_linear_segment():
    # ascending segment uses the linear trapezoid: 0.5*(c0+c1)*dt
    auc = nca._auc_linlog([0, 2], [0, 4])
    assert auc == pytest.approx(0.5 * (0 + 4) * 2, rel=1e-9)


def test_auc_log_down_segment():
    # declining segment uses the log trapezoid: dt*(c0-c1)/ln(c0/c1)
    auc = nca._auc_linlog([0, 1], [8, 2])
    assert auc == pytest.approx(1 * (8 - 2) / math.log(8 / 2), rel=1e-9)


def test_terminal_slope_recovered():
    # pure log-linear decline with lambda_z = 0.2
    t = [4, 8, 12, 16]
    c = [math.exp(-0.2 * x) for x in t]
    lz, r2, n = nca._terminal(t, c)
    assert lz == pytest.approx(0.2, rel=1e-6)
    assert r2 > 0.999
    assert n >= 3


def test_blq_cleaning_leading_zero_and_terminal_drop():
    # leading BLQ -> 0; terminal BLQ -> dropped
    t, c = nca._clean_blq([0, 1, 2, 3], [None, 5.0, 2.0, None])
    assert c[0] == 0.0  # leading BLQ became 0
    assert 3 not in t  # terminal BLQ time dropped
    assert c[1:] == [5.0, 2.0]
