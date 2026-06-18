"""Unit tests for the keyless ESM-2 masked-marginal variant scorer.

The HuggingFace fill-mask call is mocked so these tests are deterministic and
network-free; they pin the masked-marginal math, the direction interpretation,
input validation, long-sequence windowing, and status propagation.
"""

import math

import pytest

from tooluniverse.esm2_variant_effect_tool import ESM2VariantEffectTool

pytestmark = pytest.mark.unit

# A short wild-type "sequence". Residue at 1-based position 4 is 'E'.
SEQ = "MAKEDLST"


def _tool(fill_response):
    """Build the tool with its HF fill-mask call stubbed to `fill_response`."""
    tool = ESM2VariantEffectTool({"name": "esm2"})
    tool._hf = type("FakeHF", (), {"run": staticmethod(lambda *a, **k: fill_response)})()
    return tool


def _fill_ok(prob_map):
    return {
        "status": "success",
        "data": {
            "predictions": [
                {"token_str": aa, "score": p} for aa, p in prob_map.items()
            ]
        },
    }


def test_masked_marginal_llr_and_direction():
    """LLR = log P(mut) - log P(wt); a disfavored mutant scores negative."""
    out = _tool(_fill_ok({"E": 0.5, "V": 0.01, "A": 0.2})).run(
        {"sequence": SEQ, "position": 4, "mutant": "V"}
    )
    assert out["status"] == "success"
    d = out["data"]
    assert d["wild_type"] == "E" and d["mutant"] == "V"
    assert d["variant"] == "E4V"
    assert math.isclose(d["log_likelihood_ratio"], math.log(0.01) - math.log(0.5))
    assert d["log_likelihood_ratio"] < 0
    assert "disfavored" in d["direction"]


def test_favored_mutant_is_positive():
    """A mutant the model prefers over wild-type scores positive (tolerated)."""
    out = _tool(_fill_ok({"E": 0.05, "V": 0.4})).run(
        {"sequence": SEQ, "position": 4, "mutant": "V"}
    )
    assert out["data"]["log_likelihood_ratio"] > 0
    assert "tolerated" in out["data"]["direction"]


def test_wild_type_mismatch_is_error():
    """A declared wild_type that contradicts the sequence is rejected early."""
    out = _tool(_fill_ok({"E": 0.5, "V": 0.01})).run(
        {"sequence": SEQ, "position": 4, "wild_type": "Q", "mutant": "V"}
    )
    assert out["status"] == "error" and "does not match" in out["error"]


def test_position_out_of_range_is_error():
    out = _tool(_fill_ok({})).run({"sequence": SEQ, "position": 99, "mutant": "V"})
    assert out["status"] == "error" and "out of range" in out["error"]


def test_mutant_equals_wild_type_is_error():
    out = _tool(_fill_ok({})).run({"sequence": SEQ, "position": 4, "mutant": "E"})
    assert out["status"] == "error" and "missense" in out["error"]


def test_invalid_mutant_letter_is_error():
    out = _tool(_fill_ok({})).run({"sequence": SEQ, "position": 4, "mutant": "Z"})
    assert out["status"] == "error" and "standard amino acid" in out["error"]


def test_missing_probability_is_error():
    """If the model omits the wt or mut residue, the LLR can't be computed."""
    out = _tool(_fill_ok({"A": 0.9})).run(
        {"sequence": SEQ, "position": 4, "mutant": "V"}
    )
    assert out["status"] == "error" and "did not return a probability" in out["error"]


def test_loading_status_propagates():
    """A 'loading' response from HF is surfaced unchanged, not swallowed."""
    loading = {"status": "loading", "error": "Model warming up", "estimated_time": 20}
    out = _tool(loading).run({"sequence": SEQ, "position": 4, "mutant": "V"})
    assert out["status"] == "loading"


def test_long_sequence_is_windowed():
    """Sequences over the context budget are windowed around the variant."""
    # Variant at position 1500 of a 3000-residue protein; wt there is 'E'.
    long_seq = ("A" * 1499) + "E" + ("A" * 1500)
    out = _tool(_fill_ok({"E": 0.3, "V": 0.02})).run(
        {"sequence": long_seq, "position": 1500, "mutant": "V"}
    )
    assert out["status"] == "success"
    assert out["data"]["wild_type"] == "E"
    assert out["metadata"]["windowed"] is True
    lo, hi = out["metadata"]["window"]
    assert lo <= 1500 <= hi and (hi - lo + 1) <= 1022
