"""Unit tests for the remote ML tool *server logic* (Enformer/Borzoi/scVI/LDSC).

These tests exercise the parts written in this repo — DNA sequence encoding and
centering, central-bin track selection, LDSC log parsing, argument handling, and
the error/return envelopes — using REAL torch where the helpers need it.

They deliberately do NOT exercise the upstream model forward pass (loading
``enformer-pytorch`` / ``borzoi-pytorch`` / ``scvi-tools`` weights), which runs
on a deployed MCP server, not in CI. The three un-installable model packages are
stubbed in ``sys.modules`` so the server modules import; the model call itself is
monkeypatched per-test.

CI does not install the heavy DL stack, so the torch/scanpy-dependent cases skip
cleanly there; the stdlib-only LDSC cases run everywhere. All cases run locally
where the deps are present.
"""

import importlib.util
import os
import sys
import types

import numpy as np
import pytest

pytestmark = pytest.mark.unit

HAS_TORCH = importlib.util.find_spec("torch") is not None
HAS_SCANPY = importlib.util.find_spec("scanpy") is not None
requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
requires_scanpy = pytest.mark.skipif(not HAS_SCANPY, reason="scanpy not installed")

_REMOTE = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "tooluniverse", "remote"
)


def _load(rel_path, name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_REMOTE, rel_path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _stub(name, **attrs):
    if name not in sys.modules:
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m


# LDSC server is stdlib-only — always loadable, even in a minimal CI image.
ld = _load("ldsc/ldsc_tool.py", "ld_tool")

# torch-backed servers: stub the model packages, then load (only when torch present)
ef = bz = sv = None
if HAS_TORCH:
    import torch

    _stub("enformer_pytorch", from_pretrained=lambda *a, **k: object())

    class _Borzoi:
        @classmethod
        def from_pretrained(cls, *a, **k):
            return cls()

    _stub("borzoi_pytorch", Borzoi=_Borzoi)
    ef = _load("enformer/enformer_tool.py", "ef_tool")
    bz = _load("borzoi/borzoi_tool.py", "bz_tool")

if HAS_SCANPY:
    scvi_mod = types.ModuleType("scvi")
    model_mod = types.ModuleType("scvi.model")
    model_mod.SCVI = object
    scvi_mod.model = model_mod
    sys.modules.setdefault("scvi", scvi_mod)
    sys.modules.setdefault("scvi.model", model_mod)
    sv = _load("scvi/scvi_tool.py", "sv_tool")


# ----------------------------------------------------------------- Enformer
@requires_torch
def test_enformer_encode_centers_and_maps_bases():
    out = ef._encode("ACGT")
    assert out.shape == (1, ef.SEQ_LENGTH) and out.dtype == torch.long
    pad = (ef.SEQ_LENGTH - 4) // 2
    assert out[0, pad : pad + 4].tolist() == [0, 1, 2, 3]  # A,C,G,T centered
    assert out[0, 0].item() == 4 and out[0, -1].item() == 4  # N-padded ends


@requires_torch
def test_enformer_encode_crops_overlong_sequence():
    out = ef._encode("ACGT" * ef.SEQ_LENGTH)  # far longer than the model input
    assert out.shape == (1, ef.SEQ_LENGTH)


@requires_torch
def test_enformer_encode_unknown_base_is_n():
    out = ef._encode("AXGT")  # X is not a base -> mapped to N(4)
    pad = (ef.SEQ_LENGTH - 4) // 2
    assert out[0, pad : pad + 4].tolist() == [0, 4, 2, 3]


@requires_torch
def test_enformer_top_center_tracks_selection_and_ordering():
    pred = torch.zeros(ef.N_BINS, 5)
    pred[ef.N_BINS // 2] = torch.tensor([0.1, 0.5, 0.2, 0.9, 0.3])
    sel = ef._top_center_tracks(pred, [0, 4], 20)  # explicit indices preserved
    assert [d["track"] for d in sel] == [0, 4]
    assert sel[0]["center_value"] == pytest.approx(0.1)
    top = ef._top_center_tracks(pred, None, 2)  # top_n, descending
    assert [d["track"] for d in top] == [3, 1]


@requires_torch
def test_enformer_run_predict_envelope(monkeypatch):
    monkeypatch.setattr(ef, "_predict", lambda seq, org: torch.zeros(ef.N_BINS, 5))
    out = ef.EnformerPredictTool().run({"sequence": "ACGT", "top_n": 3})
    assert out["model"] == "Enformer" and out["n_tracks"] == 5
    assert out["n_bins"] == ef.N_BINS and out["bin_size_bp"] == 128
    assert len(out["tracks"]) == 3


@requires_torch
def test_enformer_run_predict_errors():
    assert ef.EnformerPredictTool().run({})["error"]
    assert "organism" in ef.EnformerPredictTool().run(
        {"sequence": "ACGT", "organism": "frog"}
    )["error"]


@requires_torch
def test_enformer_variant_effect_delta_sign(monkeypatch):
    def fake_predict(seq, org):
        return torch.full((ef.N_BINS, 3), 1.0 if seq == "ALT" else 0.0)

    monkeypatch.setattr(ef, "_predict", fake_predict)
    out = ef.EnformerVariantEffectTool().run(
        {"ref_sequence": "REF", "alt_sequence": "ALT"}
    )
    assert out["tracks"][0]["delta"] == pytest.approx(1.0)  # alt - ref
    assert ef.EnformerVariantEffectTool().run({"ref_sequence": "REF"})["error"]


# ------------------------------------------------------------------- Borzoi
@requires_torch
def test_borzoi_encode_onehot_shape_and_channels():
    out = bz._encode("ACGT")
    assert out.shape == (1, 4, bz.SEQ_LENGTH)
    pad = (bz.SEQ_LENGTH - 4) // 2
    block = out[0, :, pad : pad + 4]
    assert block.tolist() == [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    assert out[0, :, 0].sum().item() == 0.0  # N column is all-zero


@requires_torch
def test_borzoi_run_predict_envelope(monkeypatch):
    # Borzoi output is (tracks, bins); mock 7 tracks x N_BINS bins.
    monkeypatch.setattr(bz, "_predict", lambda seq: torch.zeros(7, bz.N_BINS))
    out = bz.BorzoiPredictTool().run({"sequence": "ACGT", "top_n": 4})
    assert out["model"] == "Borzoi" and out["n_tracks"] == 7
    assert out["n_bins"] == bz.N_BINS and out["bin_size_bp"] == 32
    assert len(out["tracks"]) == 4
    assert bz.BorzoiPredictTool().run({})["error"]


# --------------------------------------------------------------------- LDSC
H2_LOG = """\
Total Observed scale h2: 0.2106 (0.0203)
Lambda GC: 1.0792
Mean Chi^2: 1.1832
Intercept: 1.0186 (0.0093)
Ratio: 0.1016 (0.0506)
"""

RG_LOG = """\
Genetic Correlation
-------------------
Genetic Correlation: 0.2783 (0.0817)
Z-score: 3.4061
P: 0.000657
"""


def test_ldsc_ref_resolution():
    assert ld._ref("/abs/panel", "x").startswith("/abs/panel")  # absolute kept
    rel = ld._ref(None, "eur_w_ld_chr/")
    assert rel.endswith("eur_w_ld_chr/") and ld.LDSC_REF_DIR in rel


def test_ldsc_heritability_parsing(monkeypatch):
    monkeypatch.setattr(ld, "_run_ldsc", lambda args: {"log": H2_LOG})
    out = ld.LdscHeritabilityTool().run({"sumstats_path": "trait.sumstats.gz"})
    assert out["h2"] == pytest.approx(0.2106)
    assert out["h2_se"] == pytest.approx(0.0203)
    assert out["intercept"] == pytest.approx(1.0186)
    assert out["ratio"] == pytest.approx(0.1016)


def test_ldsc_genetic_correlation_parsing(monkeypatch):
    monkeypatch.setattr(ld, "_run_ldsc", lambda args: {"log": RG_LOG})
    out = ld.LdscGeneticCorrelationTool().run(
        {"sumstats_path_1": "a.sumstats.gz", "sumstats_path_2": "b.sumstats.gz"}
    )
    assert out["rg"] == pytest.approx(0.2783)
    assert out["rg_se"] == pytest.approx(0.0817)
    assert out["p_value"] == pytest.approx(0.000657)


def test_ldsc_propagates_engine_error(monkeypatch):
    monkeypatch.setattr(ld, "_run_ldsc", lambda args: {"error": "ldsc.py not found"})
    out = ld.LdscHeritabilityTool().run({"sumstats_path": "x.sumstats.gz"})
    assert out["error"] == "ldsc.py not found"


def test_ldsc_missing_args():
    assert ld.LdscHeritabilityTool().run({})["error"]
    assert ld.LdscGeneticCorrelationTool().run({"sumstats_path_1": "a"})["error"]


# --------------------------------------------------------------------- scVI
@requires_scanpy
def test_scvi_integration_envelope(monkeypatch):
    class _FakeModel:
        def get_latent_representation(self):
            return np.zeros((3, 10), dtype=np.float32)

    class _FakeAdata:
        obs_names = np.array(["c1", "c2", "c3"])

    monkeypatch.setattr(sv, "_prepare_adata", lambda *a, **k: _FakeAdata())
    monkeypatch.setattr(sv, "_train_scvi", lambda *a, **k: _FakeModel())
    out = sv.ScviIntegrationTool().run({"adata_path": "x.h5ad", "batch_key": "sample"})
    assert out["model"] == "scVI" and out["n_cells"] == 3 and out["n_latent"] == 10
    assert len(out["latent_representation"]) == 3
    assert out["cell_ids"] == ["c1", "c2", "c3"]


@requires_scanpy
def test_scvi_missing_args():
    assert sv.ScviIntegrationTool().run({})["error"]
    assert sv.ScviDifferentialExpressionTool().run({"adata_path": "x.h5ad"})["error"]
