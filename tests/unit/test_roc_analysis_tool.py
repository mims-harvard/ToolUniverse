"""Unit tests for the ROC/AUC diagnostic-accuracy tool (scikit-learn-backed).

The tool is deliberately generic: it takes scores + binary labels (inline or
from a CSV) and returns the standard sklearn ROC result. These tests pin the
canonical numbers on a tiny separable example, the fixed-cutoff metrics, label
coercion, CSV input, and the error paths.
"""

import csv

import pytest

from tooluniverse.roc_analysis_tool import ROCAnalysisTool

pytestmark = pytest.mark.unit

# Perfectly separable: every positive scores above every negative.
SEP_SCORES = [0.1, 0.2, 0.3, 0.6, 0.7, 0.8]
SEP_LABELS = [0, 0, 0, 1, 1, 1]


def _tool():
    return ROCAnalysisTool(
        {"name": "roc", "type": "ROCAnalysisTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_perfectly_separable_auc_is_one():
    """A separable score/label set has AUC 1.0 and a clean Youden cutoff."""
    out = _tool().run({"scores": SEP_SCORES, "labels": SEP_LABELS})
    assert out["status"] == "success"
    d = out["data"]
    assert d["auc"] == 1.0
    assert d["n"] == 6 and d["n_positive"] == 3 and d["n_negative"] == 3
    assert d["youden_optimal"]["sensitivity"] == 1.0
    assert d["youden_optimal"]["specificity"] == 1.0
    assert d["auc_ci95"] == [1.0, 1.0]


def test_fixed_cutoff_metrics():
    """At a fixed cutoff, sensitivity/specificity follow the 2x2 table."""
    # cutoff 0.65: positives 0.7,0.8 caught (TP=2), 0.6 missed (FN=1) -> sens 2/3.
    out = _tool().run({"scores": SEP_SCORES, "labels": SEP_LABELS, "cutoff": 0.65})
    at = out["data"]["at_cutoff"]
    assert at["cutoff"] == 0.65
    assert at["sensitivity"] == pytest.approx(2 / 3, abs=1e-6)
    assert at["specificity"] == 1.0


def test_two_class_string_labels_with_positive_label():
    """Non-0/1 labels are coerced via positive_label."""
    out = _tool().run({
        "scores": SEP_SCORES,
        "labels": ["healthy", "healthy", "healthy", "disease", "disease", "disease"],
        "positive_label": "disease",
    })
    assert out["status"] == "success"
    assert out["data"]["auc"] == 1.0
    assert out["data"]["n_positive"] == 3


def test_csv_input(tmp_path):
    """Reads scores/labels from a CSV with default column names."""
    p = tmp_path / "scores.csv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["label", "score"])
        for lab, sc in zip(SEP_LABELS, SEP_SCORES):
            w.writerow([lab, sc])
    out = _tool().run({"csv_path": str(p)})
    assert out["status"] == "success"
    assert out["data"]["auc"] == 1.0


def test_imperfect_auc_between_half_and_one():
    """A non-separable set yields 0.5 < AUC < 1.0."""
    out = _tool().run({
        "scores": [0.1, 0.4, 0.35, 0.8, 0.2, 0.9, 0.6, 0.45],
        "labels": [0, 0, 0, 1, 0, 1, 1, 1],
    })
    assert out["status"] == "success"
    assert 0.5 < out["data"]["auc"] <= 1.0


# --- error paths ----------------------------------------------------------- #
def test_single_class_is_error():
    """ROC is undefined without both classes present."""
    out = _tool().run({"scores": [1, 2, 3], "labels": [1, 1, 1]})
    assert out["status"] == "error" and "positive and a negative" in out["error"]


def test_length_mismatch_is_error():
    """Misaligned scores/labels are rejected, not crashed."""
    out = _tool().run({"scores": [1, 2], "labels": [1]})
    assert out["status"] == "error" and "length mismatch" in out["error"]


def test_missing_inputs_is_error():
    """No scores/labels and no csv_path is a clean error."""
    out = _tool().run({})
    assert out["status"] == "error"


def test_nonbinary_labels_without_positive_label_is_error():
    """Three classes with no positive_label is ambiguous -> error."""
    out = _tool().run({"scores": [1, 2, 3, 4], "labels": ["a", "b", "c", "a"]})
    assert out["status"] == "error" and "binary" in out["error"]
