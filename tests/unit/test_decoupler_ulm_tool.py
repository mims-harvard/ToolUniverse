"""Unit tests for decoupleR ULM activity inference.

A TF whose targets are all up-regulated must get a positive activity; a TF whose
targets are down-regulated must get a negative activity; a TF with too few
targets in the gene universe must be dropped. The math is a deterministic linear
regression, so results are exact.
"""

import pytest

from tooluniverse.decoupler_ulm_tool import DecouplerULMTool

pytestmark = pytest.mark.unit

# 20 genes: G1..G8 strongly up, G13..G20 strongly down, middle ~0
STATS = {f"G{i}": float(9 - i) for i in range(1, 21)}  # G1=8 .. G20=-11 (monotone)


def _tool():
    return DecouplerULMTool({"name": "ulm"})


def _edges(source, targets):
    return [{"source": source, "target": t, "weight": 1} for t in targets]


def _act(out, source):
    return next(a for a in out["data"]["activities"] if a["source"] == source)


def test_tf_targeting_up_genes_is_active():
    net = _edges("UP_TF", [f"G{i}" for i in range(1, 7)]) + _edges(
        "DOWN_TF", [f"G{i}" for i in range(15, 21)]
    )
    out = _tool().run({"gene_stats": STATS, "network": net})
    assert out["status"] == "success"
    assert _act(out, "UP_TF")["activity"] > 0
    assert _act(out, "DOWN_TF")["activity"] < 0
    assert _act(out, "UP_TF")["n_targets"] == 6


def test_significant_activity_has_small_p():
    net = _edges("UP_TF", [f"G{i}" for i in range(1, 9)])
    out = _tool().run({"gene_stats": STATS, "network": net})
    a = _act(out, "UP_TF")
    assert a["activity"] > 0 and a["p_value"] < 0.05


def test_min_targets_filter_drops_small_sources():
    net = _edges("BIG", [f"G{i}" for i in range(1, 8)]) + _edges("SMALL", ["G1", "G2"])
    out = _tool().run({"gene_stats": STATS, "network": net, "min_targets": 5})
    sources = {a["source"] for a in out["data"]["activities"]}
    assert "BIG" in sources and "SMALL" not in sources


def test_weight_sign_flips_activity():
    up = _edges("T", [f"G{i}" for i in range(1, 7)])
    repressive = [{"source": "T", "target": f"G{i}", "weight": -1} for i in range(1, 7)]
    a_up = _act(_tool().run({"gene_stats": STATS, "network": up}), "T")["activity"]
    a_rep = _act(_tool().run({"gene_stats": STATS, "network": repressive}), "T")["activity"]
    assert a_up > 0 and a_rep < 0  # negative mode-of-regulation flips the sign


def test_genes_stats_lists_accepted():
    out = _tool().run(
        {
            "genes": list(STATS.keys()),
            "stats": list(STATS.values()),
            "network": _edges("T", [f"G{i}" for i in range(1, 7)]),
        }
    )
    assert out["status"] == "success"


def test_errors():
    assert _tool().run({"gene_stats": STATS})["status"] == "error"  # no network
    assert _tool().run({"network": _edges("T", ["G1"])})["status"] == "error"  # no stats
    # network targets that don't match any gene -> no usable source
    out = _tool().run({"gene_stats": STATS, "network": _edges("T", ["X1", "X2", "X3", "X4", "X5"])})
    assert out["status"] == "error" and "targets" in out["error"]
