"""Unit tests for co-expression module detection.

Two groups of genes with distinct, mutually-uncorrelated expression patterns must
be split into (at least) two modules; the module eigengene must have one value
per sample. Random/constant genes must not crash it.
"""

import numpy as np
import pytest

from tooluniverse.coexpression_module_tool import CoexpressionModuleTool

pytestmark = pytest.mark.unit


def _tool():
    return CoexpressionModuleTool({"name": "coexp"})


def _two_module_expression():
    rng = np.random.default_rng(0)
    n_samples = 20
    p1 = rng.normal(size=n_samples)
    p2 = rng.normal(size=n_samples)  # independent of p1
    expr = {}
    for i in range(6):  # module A: 6 genes ~ p1
        expr[f"A{i}"] = (p1 + 0.05 * rng.normal(size=n_samples)).tolist()
    for i in range(6):  # module B: 6 genes ~ p2
        expr[f"B{i}"] = (p2 + 0.05 * rng.normal(size=n_samples)).tolist()
    return expr


def test_two_uncorrelated_groups_form_separate_modules():
    out = _tool().run({"expression": _two_module_expression(), "min_module_size": 3})
    assert out["status"] == "success"
    d = out["data"]
    assert d["n_modules"] >= 2
    # each module's genes should be from a single group (A* or B*)
    for m in d["modules"]:
        prefixes = {g[0] for g in m["genes"]}
        assert len(prefixes) == 1  # homogeneous module
        assert len(m["eigengene"]) == d["n_samples"]


def test_eigengene_tracks_module_expression():
    out = _tool().run({"expression": _two_module_expression(), "min_module_size": 3})
    m = out["data"]["modules"][0]
    block = np.array([_two_module_expression()[g] for g in m["genes"]])
    # eigengene is sign-aligned to positively track the module mean
    assert np.corrcoef(m["eigengene"], block.mean(axis=0))[0, 1] > 0.5


def test_handles_constant_gene_without_crashing():
    expr = _two_module_expression()
    expr["FLAT"] = [1.0] * 20  # zero-variance gene -> NaN correlation, must be handled
    out = _tool().run({"expression": expr, "min_module_size": 3})
    assert out["status"] == "success"


def test_errors():
    assert _tool().run({})["status"] == "error"  # no expression
    assert _tool().run({"expression": {"G1": [1, 2, 3]}})["status"] == "error"  # too few genes
    # too few samples
    out = _tool().run({"expression": {f"G{i}": [1, 2] for i in range(5)}})
    assert out["status"] == "error" and "samples" in out["error"]
