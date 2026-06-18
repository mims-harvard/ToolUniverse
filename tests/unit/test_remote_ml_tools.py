"""Unit tests for the remote ML tool *server logic* (Enformer/Borzoi/scVI/LDSC).

These tests exercise the parts written in this repo — DNA sequence encoding and
centering, central-bin track selection, LDSC log parsing, argument handling, and
the error/return envelopes — using REAL torch where the helpers need it.

They deliberately do NOT exercise the upstream model forward pass (loading
``enformer-pytorch`` / ``borzoi-pytorch`` / ``scvi-tools`` weights), which runs
on a deployed MCP server, not in CI. The three un-installable model packages are
stubbed in ``sys.modules`` so the server modules import; the model call itself is
monkeypatched per-test. This pins the glue logic that is most likely to carry a
bug, while being honest that end-to-end inference is verified at deploy time.
"""

import importlib.util
import os
import sys
import types

import numpy as np
import pytest

pytestmark = pytest.mark.unit

# --- stub the model packages that aren't installed, so the servers import ----
if "enformer_pytorch" not in sys.modules:
    m = types.ModuleType("enformer_pytorch")
    m.from_pretrained = lambda *a, **k: object()
    sys.modules["enformer_pytorch"] = m

if "borzoi_pytorch" not in sys.modules:
    m = types.ModuleType("borzoi_pytorch")

    class _Borzoi:
        @classmethod
        def from_pretrained(cls, *a, **k):
            return cls()

    m.Borzoi = _Borzoi
    sys.modules["borzoi_pytorch"] = m

if "scvi" not in sys.modules:
    scvi_mod = types.ModuleType("scvi")
    model_mod = types.ModuleType("scvi.model")
    model_mod.SCVI = object
    scvi_mod.model = model_mod
    sys.modules["scvi"] = scvi_mod
    sys.modules["scvi.model"] = model_mod

import torch  # noqa: E402  (available in this env)

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


ef = _load("enformer/enformer_tool.py", "ef_tool")
bz = _load("borzoi/borzoi_tool.py", "bz_tool")
ld = _load("ldsc/ldsc_tool.py", "ld_tool")
sv = _load("scvi/scvi_tool.py", "sv_tool")


# ----------------------------------------------------------------- Enformer
def test_enformer_encode_centers_and_maps_bases():
    out = ef._encode("ACGT")
    assert out.shape == (1, ef.SEQ_LENGTH) and out.dtype == torch.long
    pad = (ef.SEQ_LENGTH - 4) // 2
    assert out[0, pad : pad + 4].tolist() == [0, 1, 2, 3]  # A,C,G,T centered
    assert out[0, 0].item() == 4 and out[0, -1].item() == 4  # N-padded ends


def test_enformer_encode_crops_overlong_sequence():
    seq = "ACGT" * (ef.SEQ_LENGTH)  # far longer than the model input
    out = ef._encode(seq)
    assert out.shape == (1, ef.SEQ_LENGTH)


def test_enformer_encode_unknown_base_is_n():
    out = ef._encode("AXGT")  # X is not a base -> mapped to N(4)
    pad = (ef.SEQ_LENGTH - 4) // 2
    assert out[0, pad : pad + 4].tolist() == [0, 4, 2, 3]


def test_enformer_top_center_tracks_selection_and_ordering():
    pred = torch.zeros(ef.N_BINS, 5)
    pred[ef.N_BINS // 2] = torch.tensor([0.1, 0.5, 0.2, 0.9, 0.3])
    # explicit indices preserve request
    sel = ef._top_center_tracks(pred, [0, 4], 20)
    assert [d["track"] for d in sel] == [0, 4]
    assert sel[0]["center_value"] == pytest.approx(0.1)
    # top_n returns highest-signal tracks, descending
    top = ef._top_center_tracks(pred, None, 2)
    assert [d["track"] for d in top] == [3, 1]


def test_enformer_run_predict_envelope(monkeypatch):
    monkeypatch.setattr(ef, "_predict", lambda seq, org: torch.zeros(ef.N_BINS, 5))
    out = ef.EnformerPredictTool().run({"sequence": "ACGT", "top_n": 3})
    assert out["model"] == "Enformer" and out["n_tracks"] == 5
    assert out["n_bins"] == ef.N_BINS and out["bin_size_bp"] == 128
    assert len(out["tracks"]) == 3


def test_enformer_run_predict_errors():
    assert ef.EnformerPredictTool().run({})["error"]
    assert "organism" in ef.EnformerPredictTool().run(
        {"sequence": "ACGT", "organism": "frog"}
    )["error"]


def test_enformer_variant_effect_delta_sign(monkeypatch):
    def fake_predict(seq, org):
        v = 1.0 if seq == "ALT" else 0.0
        return torch.full((ef.N_BINS, 3), v)

    monkeypatch.setattr(ef, "_predict", fake_predict)
    out = ef.EnformerVariantEffectTool().run(
        {"ref_sequence": "REF", "alt_sequence": "ALT"}
    )
    assert out["tracks"][0]["delta"] == pytest.approx(1.0)  # alt - ref
    assert ef.EnformerVariantEffectTool().run({"ref_sequence": "REF"})["error"]


# ------------------------------------------------------------------- Borzoi
def test_borzoi_encode_onehot_shape_and_channels():
    out = bz._encode("ACGT")
    assert out.shape == (1, 4, bz.SEQ_LENGTH)
    pad = (bz.SEQ_LENGTH - 4) // 2
    block = out[0, :, pad : pad + 4]
    assert block.tolist() == [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    assert out[0, :, 0].sum().item() == 0.0  # N column is all-zero


def test_borzoi_run_predict_envelope(monkeypatch):
    monkeypatch.setattr(bz, "_predict", lambda seq: torch.zeros(bz.N_BINS, 7))
    out = bz.BorzoiPredictTool().run({"sequence": "ACGT", "top_n": 4})
    assert out["model"] == "Borzoi" and out["n_tracks"] == 7
    assert out["bin_size_bp"] == 32 and len(out["tracks"]) == 4
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


def test_scvi_missing_args():
    assert sv.ScviIntegrationTool().run({})["error"]
    assert sv.ScviDifferentialExpressionTool().run({"adata_path": "x.h5ad"})["error"]
