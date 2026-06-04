"""Tests for the diagnostic-test-evaluation skill helper script (ROC)."""

import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent / "scripts"))
import roc_analysis as roc  # noqa: E402

pytestmark = pytest.mark.unit


def test_perfect_separation_auc_one():
    y = np.array([0, 0, 0, 1, 1, 1])
    s = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])  # positives strictly higher
    lo, hi = roc.bootstrap_auc_ci(y, s, n=200, seed=0)
    assert lo == pytest.approx(1.0)
    assert hi == pytest.approx(1.0)


def test_bootstrap_ci_brackets_point_auc():
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(0)
    y = np.array([0] * 100 + [1] * 100)
    s = np.concatenate([rng.normal(0, 1, 100), rng.normal(1.5, 1, 100)])
    point = roc_auc_score(y, s)
    lo, hi = roc.bootstrap_auc_ci(y, s, n=500, seed=1)
    assert lo <= point <= hi
    assert 0.5 < lo < hi <= 1.0


def test_ci_handles_degenerate_resample():
    # tiny imbalanced set: some bootstrap resamples have one class -> skipped, no crash
    y = np.array([0, 0, 1])
    s = np.array([0.1, 0.2, 0.9])
    lo, hi = roc.bootstrap_auc_ci(y, s, n=100, seed=2)
    assert not (lo != lo)  # not NaN (at least some valid resamples)
