"""Unit tests for the roadmap remote-tool *server logic* (CellRank, ...).

These exercise the parts written in this repo — argument validation, the
error/return envelopes, and result shaping — NOT the upstream model forward pass
(`cellrank`/`scanpy` heavy compute), which runs on a deployed MCP server, not in
CI. The un-installable packages are stubbed in ``sys.modules`` so the server
modules import; the heavy calls are monkeypatched per-test.
"""

import importlib.util
import os
import sys
import types

import numpy as np
import pytest

pytestmark = pytest.mark.unit

_REMOTE = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "remote"
)


def _load(rel_path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_REMOTE, rel_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


class _FakeLineage:
    """Mimics a CellRank Lineage: np.asarray()-able and carries `.names`."""

    def __init__(self, arr, names):
        self._arr = np.asarray(arr, dtype=float)
        self.names = names

    def __array__(self, dtype=None):
        return self._arr if dtype is None else self._arr.astype(dtype)


# Stub the single-cell stack so cellrank_tool imports without the heavy deps.
_stub("scanpy")
sys.modules["scanpy"].read_h5ad = lambda *a, **k: None
sys.modules["scanpy"].pp = types.SimpleNamespace(
    pca=lambda *a, **k: None, neighbors=lambda *a, **k: None
)
_cr = types.ModuleType("cellrank")
_cr.estimators = types.SimpleNamespace(GPCCA=lambda *a, **k: None)
_cr.kernels = types.SimpleNamespace()
sys.modules.setdefault("cellrank", _cr)

crk = _load("cellrank/cellrank_tool.py", "cellrank_tool")


# ------------------------------------------------------------------ CellRank
def test_cellrank_missing_adata_path():
    assert crk.CellrankFateTool().run({})["error"]


def test_cellrank_rejects_unknown_kernel():
    out = crk.CellrankFateTool().run({"adata_path": "x.h5ad", "kernel": "magic"})
    assert "kernel must be one of" in out["error"]


def test_cellrank_pseudotime_requires_key(monkeypatch):
    class _Adata:
        obs = {}

    monkeypatch.setattr(crk.sc, "read_h5ad", lambda *a, **k: _Adata())
    out = crk.CellrankFateTool().run({"adata_path": "x.h5ad", "kernel": "pseudotime"})
    assert "pseudotime_key" in out["error"]


def test_cellrank_fate_envelope(monkeypatch):
    import pandas as pd

    class _Adata:
        n_obs = 4
        n_vars = 50
        obs = pd.DataFrame({"clusters": ["A", "A", "B", "B"]})
        obs_names = pd.Index(["c0", "c1", "c2", "c3"])

    class _Estimator:
        def __init__(self, *a, **k):
            pass

        def compute_schur(self, *a, **k):
            pass

        def compute_macrostates(self, *a, **k):
            pass

        def predict_terminal_states(self, *a, **k):
            pass

        def compute_fate_probabilities(self, *a, **k):
            pass

        @property
        def fate_probabilities(self):
            return _FakeLineage(
                [[0.9, 0.1], [0.8, 0.2], [0.2, 0.8], [0.1, 0.9]], ["Alpha", "Beta"]
            )

    monkeypatch.setattr(crk.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(crk, "_ensure_graph", lambda adata: None)
    monkeypatch.setattr(crk, "_build_kernel", lambda *a, **k: object())
    monkeypatch.setattr(crk.cr, "estimators", types.SimpleNamespace(GPCCA=_Estimator))

    out = crk.CellrankFateTool().run(
        {"adata_path": "x.h5ad", "kernel": "connectivity", "cluster_key": "clusters"}
    )
    assert out["model"] == "CellRank 2" and out["kernel"] == "connectivity"
    assert out["n_cells"] == 4
    assert out["terminal_states"] == ["Alpha", "Beta"]
    assert out["n_terminal_states"] == 2
    # per-cluster means: cluster A leans Alpha, cluster B leans Beta
    by = out["mean_fate_probabilities_by_cluster"]
    assert by["A"]["Alpha"] > by["A"]["Beta"]
    assert by["B"]["Beta"] > by["B"]["Alpha"]
    assert len(out["fate_probabilities"]) == 4 and out["cell_ids"] == ["c0", "c1", "c2", "c3"]
