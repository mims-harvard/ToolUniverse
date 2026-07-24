"""
Borzoi RNA-seq-coverage prediction — MCP Server.

Borzoi (Linder et al., Nature Genetics 2025) predicts multi-omic coverage —
~7,611 human tracks dominated by RNA-seq, plus CAGE/ATAC/DNase/ChIP — directly
from a 524,288 bp DNA sequence. It is the successor to Enformer and the
standard model for predicting RNA-seq coverage and splicing/expression variant
effects from sequence.

Served as a ToolUniverse *remote* tool because it carries a heavy dependency
stack (`borzoi-pytorch` -> PyTorch + ~0.8 GB of weights per replicate from
``johahi/borzoi-replicate-{0..3}``) and is GPU-recommended (the Flashzoi
variant is GPU-only).

Two operations:
  * run_borzoi_predict        -> predicted coverage for one sequence
  * run_borzoi_variant_effect -> ref-vs-alt central-bin delta per track

Reference
---------
Linder J, Srivastava D, Yuan H, Agarwal V, Kelley DR. "Predicting RNA-seq
coverage from DNA sequence as a unifying model of gene regulation." Nature
Genetics 57, 949-961 (2025).
"""

from typing import Any, Dict, List, Optional

import torch
from borzoi_pytorch import Borzoi

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

SEQ_LENGTH = 524_288
N_BINS = 6_144
_BASE_TO_CHANNEL = {"A": 0, "C": 1, "G": 2, "T": 3}
_MODEL = None


def _get_model(replicate: int = 0):
    """Lazy-load a pretrained Borzoi replicate (cached)."""
    global _MODEL
    if _MODEL is None:
        _MODEL = Borzoi.from_pretrained(f"johahi/borzoi-replicate-{replicate}")
        _MODEL.eval()
    return _MODEL


def _encode(sequence: str) -> torch.Tensor:
    """Center-crop / pad a DNA string to SEQ_LENGTH and one-hot encode (1,4,L)."""
    seq = (sequence or "").strip().upper()
    if len(seq) > SEQ_LENGTH:
        start = (len(seq) - SEQ_LENGTH) // 2
        seq = seq[start : start + SEQ_LENGTH]
    elif len(seq) < SEQ_LENGTH:
        pad = SEQ_LENGTH - len(seq)
        left = pad // 2
        seq = "N" * left + seq + "N" * (pad - left)
    onehot = torch.zeros(1, 4, SEQ_LENGTH)
    for i, base in enumerate(seq):
        ch = _BASE_TO_CHANNEL.get(base)
        if ch is not None:  # N stays all-zero
            onehot[0, ch, i] = 1.0
    return onehot


def _predict(sequence: str) -> torch.Tensor:
    """Return the (n_tracks, n_bins) human coverage prediction for one sequence.

    borzoi-pytorch outputs (batch, tracks, bins) = (1, 7611, 6144) — tracks on
    the first axis, sequence bins on the second (the opposite order from
    Enformer), so the central-bin value per track is taken along the bin axis.
    """
    model = _get_model()
    with torch.no_grad():
        out = model(_encode(sequence))
    return out[0]  # (7611, 6144) = (tracks, bins)


def _center_bin(pred: torch.Tensor) -> torch.Tensor:
    """Per-track value at the central sequence bin -> shape (n_tracks,)."""
    return pred[:, pred.shape[1] // 2]


def _top_center_tracks(
    pred: torch.Tensor, track_indices: Optional[List[int]], top_n: int
):
    center = _center_bin(pred)
    if track_indices:
        return [
            {"track": int(t), "center_value": float(center[int(t)])}
            for t in track_indices
            if 0 <= int(t) < center.shape[0]
        ]
    order = torch.argsort(center, descending=True)[:top_n]
    return [{"track": int(t), "center_value": float(center[int(t)])} for t in order]


@register_mcp_tool(
    tool_type_name="run_borzoi_predict",
    config={
        "description": (
            "Predict multi-omic coverage (~7,611 human tracks, RNA-seq-dominant) "
            "from a DNA sequence using Borzoi. The sequence is center-cropped / "
            "N-padded to 524,288 bp. Returns the central-bin value for requested "
            "tracks (or the top-signal tracks)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": "DNA sequence (A/C/G/T/N). Cropped/padded to 524,288 bp around its center.",
                },
                "track_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Track indices to report (optional). If omitted, the top-signal tracks are returned.",
                },
                "top_n": {
                    "type": "integer",
                    "description": "When track_indices is omitted, how many top tracks to return (default 20).",
                },
            },
            "required": ["sequence"],
        },
    },
    mcp_config={
        "server_name": "Borzoi MCP Server",
        "host": "127.0.0.1",
        "port": 8012,
        "transport": "http",
    },
)
class BorzoiPredictTool:
    """Predict Borzoi coverage for a DNA sequence."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence")
        if not sequence:
            return {"error": "Missing required parameter: sequence"}
        track_indices = arguments.get("track_indices")
        top_n = int(arguments.get("top_n") or 20)

        pred = _predict(sequence)
        return {
            "model": "Borzoi",
            "organism": "human",
            "n_tracks": int(pred.shape[0]),
            "n_bins": int(pred.shape[1]),
            "bin_size_bp": 32,
            "tracks": _top_center_tracks(pred, track_indices, top_n),
        }


@register_mcp_tool(
    tool_type_name="run_borzoi_variant_effect",
    config={
        "description": (
            "Score a variant with Borzoi: predicts coverage for the reference "
            "and alternate sequences (each 524,288 bp, variant at center) and "
            "returns the central-bin delta (alt - ref) per track — the canonical "
            "Borzoi expression/coverage variant-effect score."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "ref_sequence": {
                    "type": "string",
                    "description": "Reference DNA sequence centered on the variant (cropped/padded to 524,288 bp).",
                },
                "alt_sequence": {
                    "type": "string",
                    "description": "Alternate DNA sequence (same length/centering as ref).",
                },
                "track_indices": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Track indices to report (optional; default = top |delta| tracks).",
                },
                "top_n": {
                    "type": "integer",
                    "description": "When track_indices omitted, number of top |delta| tracks to return (default 20).",
                },
            },
            "required": ["ref_sequence", "alt_sequence"],
        },
    },
    mcp_config={
        "server_name": "Borzoi MCP Server",
        "host": "127.0.0.1",
        "port": 8012,
        "transport": "http",
    },
)
class BorzoiVariantEffectTool:
    """Score a variant as the Borzoi central-bin alt-ref coverage delta."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ref = arguments.get("ref_sequence")
        alt = arguments.get("alt_sequence")
        if not (ref and alt):
            return {
                "error": "Missing required parameter(s): ref_sequence, alt_sequence"
            }
        track_indices = arguments.get("track_indices")
        top_n = int(arguments.get("top_n") or 20)

        delta = _center_bin(_predict(alt)) - _center_bin(_predict(ref))
        if track_indices:
            tracks = [
                {"track": int(t), "delta": float(delta[int(t)])}
                for t in track_indices
                if 0 <= int(t) < delta.shape[0]
            ]
        else:
            order = torch.argsort(delta.abs(), descending=True)[:top_n]
            tracks = [{"track": int(t), "delta": float(delta[int(t)])} for t in order]
        return {
            "model": "Borzoi",
            "organism": "human",
            "n_tracks": int(delta.shape[0]),
            "tracks": tracks,
        }


if __name__ == "__main__":
    start_mcp_server()
