"""Unit tests for single-sample GSEA (ssGSEA).

A gene set whose genes are highly expressed in one sample but lowly expressed in
another must get a positive score in the first and a negative score in the
second. Scores are per-sample; the sign/ordering is what matters and is exact.
"""

import pytest

from tooluniverse.ssgsea_tool import SSGSEATool

pytestmark = pytest.mark.unit

# 12 genes, 2 samples: in 'tumor' G1..G6 are top-expressed; in 'normal' reversed.
EXPR = {f"G{i}": [13 - i, i] for i in range(1, 13)}  # G1=[12,1] .. G12=[1,12]


def _tool():
    return SSGSEATool({"name": "ssgsea"})


def test_set_scores_flip_between_samples():
    out = _tool().run(
        {"expression": EXPR, "samples": ["tumor", "normal"], "gene_sets": {"TOP": ["G1", "G2", "G3", "G4"]}}
    )
    assert out["status"] == "success"
    scores = out["data"]["enrichment_scores"]["TOP"]
    assert scores["tumor"] > 0  # set genes are top-expressed in tumor
    assert scores["normal"] < 0  # and bottom-expressed in normal
    assert out["data"]["n_samples"] == 2 and out["data"]["samples"] == ["tumor", "normal"]


def test_default_sample_names_when_unlabeled():
    out = _tool().run({"expression": EXPR, "gene_set": ["G1", "G2", "G3"]})
    assert out["data"]["samples"] == ["sample_1", "sample_2"]
    assert "gene_set" in out["data"]["enrichment_scores"]


def test_tiny_set_is_skipped():
    out = _tool().run({"expression": EXPR, "gene_sets": {"BIG": ["G1", "G2", "G3"], "TINY": ["G1", "NOPE"]}})
    assert "TINY" in out["data"]["skipped_sets"]
    assert "BIG" in out["data"]["enrichment_scores"]


def test_errors():
    assert _tool().run({})["status"] == "error"  # no expression
    assert _tool().run({"expression": EXPR})["status"] == "error"  # no gene set
    # ragged matrix
    bad = {f"G{i}": [1, 2] for i in range(1, 12)}
    bad["G12"] = [1]
    out = _tool().run({"expression": bad, "gene_set": ["G1", "G2"]})
    assert out["status"] == "error" and "same number" in out["error"]
