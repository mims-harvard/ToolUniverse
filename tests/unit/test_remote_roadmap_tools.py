"""Unit tests for the roadmap remote-tool *server logic* (CellRank, ...).

These exercise the parts written in this repo — argument validation, the
error/return envelopes, and result shaping — NOT the upstream model forward pass
(`cellrank`/`scanpy` heavy compute), which runs on a deployed MCP server, not in
CI. The un-installable packages are stubbed in ``sys.modules`` so the server
modules import; the heavy calls are monkeypatched per-test.
"""

import importlib.util
import math
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


def _have(name):
    """True if the REAL module is importable (so we must not shadow it with a stub)."""
    if name in sys.modules:
        # already imported: real module has a __spec__; our stubs do not.
        return getattr(sys.modules[name], "__spec__", None) is not None
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _ensure_stub(dotted, **attrs):
    """Install a fake module tree ONLY when the real top-level package is absent.

    Never mutates an installed module — overwriting e.g. ``requests.exceptions``
    would corrupt unrelated tests sharing the same interpreter session (the cause
    of an earlier CI break). Returns True if a stub was installed, False if the
    real module is present and should be used as-is.
    """
    if _have(dotted.split(".")[0]):
        return False
    parts = dotted.split(".")
    for i in range(len(parts)):
        name = ".".join(parts[: i + 1])
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)
        if i > 0:
            setattr(sys.modules[".".join(parts[:i])], parts[i], sys.modules[name])
    for k, v in attrs.items():
        setattr(sys.modules[dotted], k, v)
    return True


class _FakeLineage:
    """Mimics a CellRank Lineage: np.asarray()-able and carries `.names`."""

    def __init__(self, arr, names):
        self._arr = np.asarray(arr, dtype=float)
        self.names = names

    def __array__(self, dtype=None):
        return self._arr if dtype is None else self._arr.astype(dtype)


# Heavy deps are absent in CI (stubbed here) and present locally (used for real).
# Each stub is installed ONLY when the real package is missing, so an installed
# module is never corrupted for other tests. `requests` is a real dependency in
# every environment, so it is deliberately NOT stubbed.
if _ensure_stub("scanpy"):
    sys.modules["scanpy"].read_h5ad = lambda *a, **k: None
    sys.modules["scanpy"].pp = types.SimpleNamespace(
        pca=lambda *a, **k: None, neighbors=lambda *a, **k: None
    )
if _ensure_stub("cellrank"):
    sys.modules["cellrank"].estimators = types.SimpleNamespace(GPCCA=lambda *a, **k: None)
    sys.modules["cellrank"].kernels = types.SimpleNamespace()
_ensure_stub("scipy")
_ensure_stub("scipy.io", mmwrite=lambda *a, **k: None)
_ensure_stub("scipy.sparse", csr_matrix=lambda x: x)
_ensure_stub(
    "tensorflow",
    keras=types.SimpleNamespace(
        models=types.SimpleNamespace(load_model=lambda *a, **k: None)
    ),
)

crk = _load("cellrank/cellrank_tool.py", "cellrank_tool")
sgr = _load("singler/singler_tool.py", "singler_tool")
sls = _load("slingshot/slingshot_tool.py", "slingshot_tool")
mc3 = _load("monocle3/monocle3_tool.py", "monocle3_tool")
cbp = _load("chrombpnet/chrombpnet_tool.py", "chrombpnet_tool")


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


# ------------------------------------------------------------------ Monocle3
def test_monocle3_missing_adata_path():
    assert mc3.Monocle3PseudotimeTool().run({})["error"]


def test_monocle3_requires_a_root():
    out = mc3.Monocle3PseudotimeTool().run({"adata_path": "x.h5ad"})
    assert "root_cluster" in out["error"] or "root_cells" in out["error"]


def test_monocle3_root_cluster_needs_cluster_key():
    out = mc3.Monocle3PseudotimeTool().run(
        {"adata_path": "x.h5ad", "root_cluster": "progenitor"}
    )
    assert "cluster_key" in out["error"]


def test_monocle3_envelope(monkeypatch):
    import pandas as pd

    class _Adata:
        var_names = ["g1", "g2"]
        obs_names = pd.Index(["c0", "c1", "c2"])
        obs = pd.DataFrame({"clusters": ["root", "mid", "tip"]})
        layers = {}
        X = None

    monkeypatch.setattr(mc3.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(mc3, "mmwrite", lambda *a, **k: None)
    monkeypatch.setattr(mc3, "csr_matrix", lambda x: __import__("types").SimpleNamespace(T=None))
    monkeypatch.setattr(
        mc3,
        "_run_rscript",
        lambda work: {
            "pseudotime": [0.0, 1.5, 3.0],
            "cell_ids": ["c0", "c1", "c2"],
            "n_cells": 3,
            "n_unreachable": 0,
            "cluster_pseudotime": {"root": 0.0, "mid": 1.5, "tip": 3.0},
        },
    )
    out = mc3.Monocle3PseudotimeTool().run(
        {"adata_path": "x.h5ad", "cluster_key": "clusters", "root_cluster": "root"}
    )
    assert out["model"] == "Monocle3" and out["n_cells"] == 3
    assert out["cluster_pseudotime"]["root"] == 0.0
    assert out["pseudotime"] == [0.0, 1.5, 3.0]


def test_monocle3_propagates_r_error(monkeypatch):
    """A Monocle3 R-side failure surfaces as a clean error envelope."""
    import pandas as pd

    class _Adata:
        var_names = ["g1"]
        obs_names = pd.Index(["c0"])
        obs = pd.DataFrame({"clusters": ["root"]})
        layers = {}
        X = None

    monkeypatch.setattr(mc3.sc, "read_h5ad", lambda *a, **k: _Adata())
    monkeypatch.setattr(mc3, "mmwrite", lambda *a, **k: None)
    monkeypatch.setattr(mc3, "csr_matrix", lambda x: __import__("types").SimpleNamespace(T=None))
    monkeypatch.setattr(mc3, "_run_rscript", lambda work: {"error": "Monocle3 (R) failed: boom"})
    out = mc3.Monocle3PseudotimeTool().run(
        {"adata_path": "x.h5ad", "cluster_key": "clusters", "root_cluster": "root"}
    )
    assert out["error"] == "Monocle3 (R) failed: boom"


# ---------------------------------------------------------------- ChromBPNet
def test_chrombpnet_encode_shape_and_centering():
    out = cbp._encode("ACGT")
    assert out.shape == (1, cbp.INPUT_LEN, 4)
    pad = (cbp.INPUT_LEN - 4) // 2
    block = out[0, pad : pad + 4]
    assert block.tolist() == [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    assert out[0, 0].sum() == 0.0  # N-padded ends are all-zero


def test_chrombpnet_encode_crops_overlong():
    assert cbp._encode("ACGT" * cbp.INPUT_LEN).shape == (1, cbp.INPUT_LEN, 4)


def test_chrombpnet_jsd_identical_is_zero_disjoint_is_one():
    p = np.array([0.5, 0.5, 0.0, 0.0])
    q = np.array([0.0, 0.0, 0.5, 0.5])
    assert cbp._jsd(p, p) == pytest.approx(0.0, abs=1e-9)
    assert cbp._jsd(p, q) == pytest.approx(1.0, abs=1e-9)  # base-2 JSD of disjoint = 1


def test_chrombpnet_predict_missing_args():
    assert cbp.ChrombpnetPredictTool().run({})["error"]
    assert cbp.ChrombpnetPredictTool().run({"model_path": "m.h5"})["error"]


def test_chrombpnet_variant_missing_args():
    assert cbp.ChrombpnetVariantEffectTool().run({})["error"]
    assert cbp.ChrombpnetVariantEffectTool().run(
        {"model_path": "m.h5", "ref_sequence": "ACGT"}
    )["error"]


def test_chrombpnet_predict_envelope(monkeypatch):
    monkeypatch.setattr(cbp, "_get_model", lambda p: object())
    # profile peaks at center; log_total_counts = ln(100)
    prof = np.zeros(cbp.OUTPUT_LEN)
    prof[cbp.OUTPUT_LEN // 2] = 1.0
    monkeypatch.setattr(cbp, "_predict", lambda model, seq: (prof, math.log(100.0)))
    out = cbp.ChrombpnetPredictTool().run({"model_path": "m.h5", "sequence": "ACGT"})
    assert out["model"] == "ChromBPNet"
    assert out["total_counts"] == pytest.approx(100.0)
    assert out["peak_offset"] == 0  # peak at profile center
    assert "profile" not in out
    out2 = cbp.ChrombpnetPredictTool().run(
        {"model_path": "m.h5", "sequence": "ACGT", "return_profile": True}
    )
    assert len(out2["profile"]) == cbp.OUTPUT_LEN


def test_chrombpnet_variant_effect_scores(monkeypatch):
    monkeypatch.setattr(cbp, "_get_model", lambda p: object())
    flat = np.full(cbp.OUTPUT_LEN, 1.0 / cbp.OUTPUT_LEN)

    def fake_predict(model, seq):
        # alt has 4x the counts of ref -> log2fc = 2; identical flat profile -> jsd 0
        return (flat, math.log(400.0) if seq == "ALT" else math.log(100.0))

    monkeypatch.setattr(cbp, "_predict", fake_predict)
    out = cbp.ChrombpnetVariantEffectTool().run(
        {"model_path": "m.h5", "ref_sequence": "REF", "alt_sequence": "ALT"}
    )
    assert out["count_log2fc"] == pytest.approx(2.0)
    assert out["profile_jsd"] == pytest.approx(0.0, abs=1e-9)


def test_chrombpnet_handles_unloadable_model(monkeypatch):
    def boom(_):
        raise OSError("no such file")

    monkeypatch.setattr(cbp, "_get_model", boom)
    out = cbp.ChrombpnetPredictTool().run({"model_path": "missing.h5", "sequence": "ACGT"})
    assert "Could not load ChromBPNet model" in out["error"]

