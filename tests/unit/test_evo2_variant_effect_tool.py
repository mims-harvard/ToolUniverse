"""Unit tests for the Evo 2 variant-effect scorer.

The live NVIDIA NIM forward call is key-gated and not exercised here; these tests
pin the parts written in this repo — the autoregressive log-likelihood reduction
(against an independent reference), sequence-input resolution, the delta/envelope
assembly, and the no-key / error paths. The likelihood math is what a silent bug
would hide in, so it is checked directly.
"""

import math

import numpy as np
import pytest

from tooluniverse.evo2_variant_effect_tool import Evo2VariantEffectTool

pytestmark = pytest.mark.unit

VOCAB = 256


def _tool():
    return Evo2VariantEffectTool({"name": "evo2"})


def _reference_loglik(seq, logits):
    """Plain-loop reference for the autoregressive log-likelihood."""
    arr = logits[0] if logits.ndim == 3 else logits  # (batch, seq, vocab)
    n = min(len(seq), arr.shape[0])
    total = 0.0
    for i in range(n - 1):
        row = arr[i]
        mx = row.max()
        log_z = mx + math.log(np.exp(row - mx).sum())
        total += float(row[ord(seq[i + 1])] - log_z)
    return total


def test_loglik_uniform_logits_is_minus_log_vocab():
    """Uniform logits -> each next base has prob 1/VOCAB; LL = -(n-1)*log(VOCAB)."""
    seq = "ACGT"
    ll = Evo2VariantEffectTool._autoregressive_loglik(seq, np.zeros((4, VOCAB)))
    assert math.isclose(ll, -3 * math.log(VOCAB), rel_tol=1e-9)


def test_loglik_matches_reference_on_random_logits():
    rng = np.random.default_rng(0)
    seq = "ACGTACGTAC"
    logits = rng.normal(size=(len(seq), VOCAB))
    got = Evo2VariantEffectTool._autoregressive_loglik(seq, logits)
    assert math.isclose(got, _reference_loglik(seq, logits), rel_tol=1e-9)


def test_loglik_handles_3d_batch_shape():
    seq = "ACGT"
    logits2d = np.random.default_rng(1).normal(size=(4, VOCAB))
    logits3d = logits2d[None, :, :]  # [1, L, vocab] = (batch, seq, vocab)
    assert math.isclose(
        Evo2VariantEffectTool._autoregressive_loglik(seq, logits3d),
        Evo2VariantEffectTool._autoregressive_loglik(seq, logits2d),
        rel_tol=1e-9,
    )


def test_resolve_point_substitution_mode():
    ref, alt, err = _tool()._resolve_sequences(
        {"sequence": "ACGTACGT", "position": 5, "reference": "A", "alternate": "T"}
    )
    assert err is None
    assert ref == "ACGTACGT" and alt == "ACGTTCGT"  # base 5 (A) -> T


def test_resolve_ref_alt_length_mismatch_errors():
    _, _, err = _tool()._resolve_sequences(
        {"ref_sequence": "ACGT", "alt_sequence": "ACG"}
    )
    assert err and "same length" in err["error"]


def test_resolve_reference_mismatch_errors():
    _, _, err = _tool()._resolve_sequences(
        {"sequence": "ACGT", "position": 1, "reference": "G", "alternate": "T"}
    )
    assert err and "does not match" in err["error"]


def test_resolve_missing_inputs_errors():
    _, _, err = _tool()._resolve_sequences({"sequence": "ACGT"})
    assert err and "Provide either" in err["error"]


def test_run_requires_api_key(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    out = _tool().run({"ref_sequence": "ACGT", "alt_sequence": "ACTT"})
    assert out["status"] == "error" and "NVIDIA_API_KEY" in out["error"]


def test_run_delta_and_direction(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    tool = _tool()
    lls = iter([-5.0, -8.0])  # ref, then alt
    monkeypatch.setattr(tool, "_sequence_log_likelihood", lambda seq, key, model: next(lls))
    out = tool.run({"ref_sequence": "ACGT", "alt_sequence": "ACTT"})
    assert out["status"] == "success"
    d = out["data"]
    assert d["ref_loglik"] == -5.0 and d["alt_loglik"] == -8.0
    assert d["delta_loglik"] == -3.0  # alt - ref
    assert "disfavored" in d["direction"]


def test_run_propagates_forward_error(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    tool = _tool()
    err = {"status": "error", "error": "Evo 2 HTTP 500", "source": "Evo2VariantEffectTool"}
    monkeypatch.setattr(tool, "_sequence_log_likelihood", lambda seq, key, model: err)
    out = tool.run({"ref_sequence": "ACGT", "alt_sequence": "ACTT"})
    assert out["status"] == "error" and "HTTP 500" in out["error"]


def test_resolve_model_defaults_and_validates():
    assert Evo2VariantEffectTool._resolve_model(None) == "evo2-40b"
    assert Evo2VariantEffectTool._resolve_model("evo2-7b") == "evo2-7b"
    assert Evo2VariantEffectTool._resolve_model("evo2-40b") == "evo2-40b"
    # unknown / unsafe values fall back to the default (no arbitrary path segment)
    assert Evo2VariantEffectTool._resolve_model("evo2-999b") == "evo2-40b"
    assert Evo2VariantEffectTool._resolve_model("../etc") == "evo2-40b"


def test_run_selects_model_in_url_and_metadata(monkeypatch):
    """The chosen model must drive both the forward URL and the reported metadata."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    tool = _tool()
    seen = {}

    def fake_forward(seq, api_key, model):
        seen["model"] = model
        return np.zeros((4, VOCAB))  # uniform logits -> finite loglik

    monkeypatch.setattr(tool, "_forward", fake_forward)
    out = tool.run({"ref_sequence": "ACGT", "alt_sequence": "ACTT", "model": "evo2-7b"})
    assert out["status"] == "success"
    assert seen["model"] == "evo2-7b"
    assert "evo2-7b" in out["metadata"]["model"]


def test_forward_url_includes_model(monkeypatch):
    """_forward must target arc/<model>/forward, not a hard-coded size."""
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
    tool = _tool()
    captured = {}

    class _Resp:
        status_code = 500
        text = "boom"

    def fake_post(url, **kwargs):
        captured["url"] = url
        return _Resp()

    monkeypatch.setattr("tooluniverse.evo2_variant_effect_tool.requests.post", fake_post)
    tool._forward("ACGT", "nvapi-test", "evo2-7b")
    assert captured["url"].endswith("/arc/evo2-7b/forward")
