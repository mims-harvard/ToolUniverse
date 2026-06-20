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


def _stub_tree(dotted, **attrs):
    """Register a (possibly dotted) module in sys.modules with attrs, linking parents."""
    parts = dotted.split(".")
    for i in range(len(parts)):
        name = ".".join(parts[: i + 1])
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
        if i > 0:
            setattr(sys.modules[".".join(parts[:i])], parts[i], sys.modules[name])
    for k, v in attrs.items():
        setattr(sys.modules[dotted], k, v)


# Stub the scipy bits singler_tool imports, so it loads without scipy in CI.
_stub_tree("scipy")
_stub_tree("scipy.io", mmwrite=lambda *a, **k: None)
_stub_tree("scipy.sparse", csr_matrix=lambda x: x)

sgr = _load("singler/singler_tool.py", "singler_tool")
sls = _load("slingshot/slingshot_tool.py", "slingshot_tool")


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


# ------------------------------------------------------------------- SingleR
def test_singler_missing_adata_path():
    assert sgr.SinglerAnnotateTool().run({})["error"]


def test_singler_rejects_unknown_celldex_ref():
    out = sgr.SinglerAnnotateTool().run({"adata_path": "q.h5ad", "celldex_ref": "MadeUpRef"})
    assert "celldex_ref must be one of" in out["error"]


def test_singler_requires_a_reference():
    out = sgr.SinglerAnnotateTool().run({"adata_path": "q.h5ad"})
    assert "Provide either celldex_ref" in out["error"]


def test_singler_summarize_shapes_envelope():
    out = sgr._summarize(
        ["T cell", "B cell", "T cell", "Monocyte"],
        ["c0", "c1", "c2", "c3"],
        "MonacoImmuneData",
    )
    assert out["model"] == "SingleR" and out["reference"] == "MonacoImmuneData"
    assert out["n_cells"] == 4
    assert out["label_counts"]["T cell"] == 2  # most_common puts T cell first
    assert list(out["label_counts"])[0] == "T cell"
    assert out["predicted_labels"][0] == "T cell" and out["cell_ids"][3] == "c3"


def test_singler_run_parses_r_output(monkeypatch):
    class _Adata:
        obs_names = __import__("numpy").array(["c0", "c1", "c2"])

        class _V:
            def astype(self, _):
                return ["g"]

        var_names = ["g1"]
        X = None

    monkeypatch.setattr(sgr.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(sgr, "_export_matrix", lambda *a, **k: None)
    monkeypatch.setattr(
        sgr,
        "_run_rscript",
        lambda work: {"predicted_labels": ["T", "T", "B"], "ref": "MonacoImmuneData"},
    )
    out = sgr.SinglerAnnotateTool().run(
        {"adata_path": "q.h5ad", "celldex_ref": "MonacoImmuneData"}
    )
    assert out["n_cells"] == 3 and out["label_counts"]["T"] == 2
    assert out["cell_ids"] == ["c0", "c1", "c2"]


def test_singler_propagates_r_error(monkeypatch):
    class _Adata:
        obs_names = __import__("numpy").array(["c0"])
        var_names = ["g1"]
        X = None

    monkeypatch.setattr(sgr.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(sgr, "_export_matrix", lambda *a, **k: None)
    monkeypatch.setattr(sgr, "_run_rscript", lambda work: {"error": "SingleR (R) failed: boom"})
    out = sgr.SinglerAnnotateTool().run({"adata_path": "q.h5ad", "celldex_ref": "ImmGenData"})
    assert out["error"] == "SingleR (R) failed: boom"


# ----------------------------------------------------------------- Slingshot
def test_slingshot_missing_required_args():
    assert sls.SlingshotTrajectoryTool().run({})["error"]
    assert sls.SlingshotTrajectoryTool().run({"adata_path": "x.h5ad"})["error"]


def test_slingshot_validates_embedding_and_cluster_keys(monkeypatch):
    class _Adata:
        obsm = {"X_pca": np.zeros((4, 5))}
        obs = {}

    monkeypatch.setattr(sls.sc, "read_h5ad", lambda *a, **k: _Adata())
    # missing embedding key
    out = sls.SlingshotTrajectoryTool().run(
        {"adata_path": "x.h5ad", "cluster_key": "clusters", "embedding_key": "X_umap"}
    )
    assert "embedding_key" in out["error"]
    # missing cluster key (X_pca exists, but obs has no 'clusters')
    out = sls.SlingshotTrajectoryTool().run(
        {"adata_path": "x.h5ad", "cluster_key": "clusters"}
    )
    assert "cluster_key" in out["error"]


def test_slingshot_envelope(monkeypatch):
    import pandas as pd

    class _Adata:
        obsm = {"X_pca": np.random.default_rng(0).normal(size=(6, 10))}
        obs = pd.DataFrame({"clusters": ["A", "A", "B", "B", "C", "C"]})
        obs_names = pd.Index([f"c{i}" for i in range(6)])

    monkeypatch.setattr(sls.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(
        sls,
        "_run_rscript",
        lambda work: {
            "lineages": [["A", "B"], ["A", "C"]],
            "lineage_names": ["Lineage1", "Lineage2"],
            "n_lineages": 2,
            "cluster_pseudotime": {"A": {"Lineage1": 0.0}},
            "pseudotime": [[0.0, 0.0]] * 6,
        },
    )
    out = sls.SlingshotTrajectoryTool().run(
        {"adata_path": "x.h5ad", "cluster_key": "clusters", "n_dims": 5}
    )
    assert out["model"] == "Slingshot" and out["n_lineages"] == 2
    assert out["embedding_key"] == "X_pca" and out["n_cells"] == 6
    assert out["lineages"] == [["A", "B"], ["A", "C"]]
    assert out["cell_ids"][0] == "c0"  # cell_ids attached because pseudotime present


def test_slingshot_propagates_r_error(monkeypatch):
    """An R-side failure surfaces as a clean error envelope, not a crash."""
    import pandas as pd

    class _Adata:
        obsm = {"X_pca": np.zeros((4, 5))}
        obs = pd.DataFrame({"clusters": ["A", "A", "B", "B"]})
        obs_names = pd.Index(["c0", "c1", "c2", "c3"])

    monkeypatch.setattr(sls.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(sls, "_run_rscript", lambda work: {"error": "Slingshot (R) failed: boom"})
    out = sls.SlingshotTrajectoryTool().run({"adata_path": "x.h5ad", "cluster_key": "clusters"})
    assert out["error"] == "Slingshot (R) failed: boom"
