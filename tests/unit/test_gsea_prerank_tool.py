"""Unit tests for pre-ranked GSEA.

A gene set concentrated at the top of the ranking must give a strongly positive
ES with a small p; a set at the bottom must give a negative ES; a dispersed set
must be non-significant. The leading edge must contain the driving genes. The
seeded permutation p must be reproducible.
"""

import pytest

from tooluniverse.gsea_prerank_tool import GSEAPrerankTool

pytestmark = pytest.mark.unit

# 20 genes, scores strictly descending (G1 highest .. G20 lowest)
RANKED = {f"G{i}": float(21 - i) for i in range(1, 21)}


def _tool():
    return GSEAPrerankTool({"name": "gsea"})


def _result(out, name):
    return next(r for r in out["data"]["results"] if r["gene_set"] == name)


def test_set_at_top_is_positively_enriched():
    out = _tool().run({"ranked_genes": RANKED, "gene_sets": {"TOP": ["G1", "G2", "G3", "G4"]}})
    assert out["status"] == "success"
    r = _result(out, "TOP")
    assert r["es"] > 0 and r["nes"] > 0
    assert r["p_value"] < 0.05
    assert "up" in r["direction"]
    assert set(r["leading_edge"]) >= {"G1", "G2", "G3", "G4"}


def test_set_at_bottom_is_negatively_enriched():
    out = _tool().run({"ranked_genes": RANKED, "gene_sets": {"BOT": ["G17", "G18", "G19", "G20"]}})
    r = _result(out, "BOT")
    assert r["es"] < 0 and "down" in r["direction"]
    assert r["p_value"] < 0.05


def test_dispersed_set_is_not_significant():
    out = _tool().run({"ranked_genes": RANKED, "gene_sets": {"MID": ["G1", "G10", "G11", "G20"]}})
    r = _result(out, "MID")
    assert abs(r["es"]) < 0.6 and r["p_value"] > 0.1


def test_permutation_p_is_reproducible():
    a = _result(_tool().run({"ranked_genes": RANKED, "gene_set": ["G1", "G2", "G3", "G4"]}), "gene_set")
    b = _result(_tool().run({"ranked_genes": RANKED, "gene_set": ["G1", "G2", "G3", "G4"]}), "gene_set")
    assert a["p_value"] == b["p_value"] and a["es"] == b["es"]


def test_genes_scores_lists_accepted():
    out = _tool().run(
        {
            "genes": list(RANKED.keys()),
            "scores": list(RANKED.values()),
            "gene_set": ["G1", "G2", "G3"],
        }
    )
    assert out["status"] == "success"


def test_small_overlap_set_is_skipped_not_crashed():
    out = _tool().run({"ranked_genes": RANKED, "gene_sets": {"TINY": ["G1", "NOTHERE"]}})
    r = _result(out, "TINY")
    assert r.get("skipped") is True and r["n_overlap"] == 1


def test_duplicate_members_are_deduped():
    """A gene listed twice must not be double-counted (same ES + n_overlap)."""
    clean = _result(_tool().run({"ranked_genes": RANKED, "gene_set": ["G1", "G2", "G3", "G4"]}), "gene_set")
    dup = _result(_tool().run({"ranked_genes": RANKED, "gene_set": ["G1", "G1", "G2", "G2", "G3", "G4"]}), "gene_set")
    assert dup["n_overlap"] == 4 and dup["es"] == clean["es"]


def test_errors():
    assert _tool().run({"ranked_genes": {"a": 1}})["status"] == "error"  # too few genes
    assert _tool().run({"ranked_genes": RANKED})["status"] == "error"  # no gene set
    out = _tool().run({"genes": ["a", "b"], "scores": [1.0], "gene_set": ["a"]})
    assert out["status"] == "error"  # mismatched lengths (and too few)
