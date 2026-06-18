"""
Enformer sequence-to-expression prediction — MCP Server.

Enformer (Avsec et al., Nature Methods 2021) predicts thousands of genomic
tracks (CAGE, DNase, ATAC, ChIP) directly from a 196,608 bp DNA sequence,
integrating long-range regulatory interactions. It is the standard sequence
model for variant-effect-on-expression and regulatory-activity prediction.

Served as a ToolUniverse *remote* tool because it carries a heavy dependency
stack (`enformer-pytorch` -> PyTorch + ~1 GB of weights from
``EleutherAI/enformer-official-rough``) and benefits from a GPU. Single-sequence
CPU inference is feasible but slow.

Two operations:
  * run_enformer_predict        -> predicted track values for one sequence
  * run_enformer_variant_effect -> ref-vs-alt delta at the central bin
                                   (the canonical regulatory variant score)

Reference
---------
Avsec Z, Agarwal V, Visentin D, et al. "Effective gene expression prediction
from sequence by integrating long-range interactions." Nature Methods 18,
1196-1203 (2021).
"""

from typing import Any, Dict, List, Optional

import torch
from enformer_pytorch import from_pretrained

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

SEQ_LENGTH = 196_608
N_BINS = 896
_BASE_TO_IDX = {"A": 0, "C": 1, "G": 2, "T": 3, "N": 4}
_MODEL = None


def _get_model():
    """Lazy-load the pretrained Enformer model (cached)."""
    global _MODEL
    if _MODEL is None:
        _MODEL = from_pretrained("EleutherAI/enformer-official-rough")
        _MODEL.eval()
    return _MODEL


def _encode(sequence: str) -> torch.Tensor:
    """Center-crop / N-pad a DNA string to SEQ_LENGTH and integer-encode it."""
    seq = (sequence or "").strip().upper()
    if len(seq) > SEQ_LENGTH:
        start = (len(seq) - SEQ_LENGTH) // 2
        seq = seq[start : start + SEQ_LENGTH]
    elif len(seq) < SEQ_LENGTH:
        pad = SEQ_LENGTH - len(seq)
        left = pad // 2
        seq = "N" * left + seq + "N" * (pad - left)
    idx = [_BASE_TO_IDX.get(b, 4) for b in seq]
    return torch.tensor([idx], dtype=torch.long)


def _predict(sequence: str, organism: str) -> torch.Tensor:
    """Return the (N_BINS, n_tracks) prediction tensor for one sequence."""
    model = _get_model()
    with torch.no_grad():
        out = model(_encode(sequence))
    return out[organism][0]  # (896, n_tracks)


def _top_center_tracks(
    pred: torch.Tensor, track_indices: Optional[List[int]], top_n: int
):
    """Center-bin value per requested track, or the top_n highest-signal tracks."""
    center = pred[N_BINS // 2]  # (n_tracks,)
    if track_indices:
        return [
            {"track": int(t), "center_value": float(center[int(t)])}
            for t in track_indices
            if 0 <= int(t) < center.shape[0]
        ]
    order = torch.argsort(center, descending=True)[:top_n]
    return [{"track": int(t), "center_value": float(center[int(t)])} for t in order]


@register_mcp_tool(
    tool_type_name="run_enformer_predict",
    config={
        "description": (
            "Predict genomic track activity (CAGE/DNase/ATAC/ChIP; 5,313 human "
            "or 1,643 mouse tracks) from a DNA sequence using Enformer. The "
            "sequence is center-cropped / N-padded to 196,608 bp. Returns the "
            "central-bin value for requested tracks (or the top-signal tracks)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": "DNA sequence (A/C/G/T/N). Cropped/padded to 196,608 bp around its center.",
                },
                "organism": {
                    "type": "string",
                    "description": "'human' (5,313 tracks, default) or 'mouse' (1,643 tracks).",
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
        "server_name": "Enformer MCP Server",
        "host": "127.0.0.1",
        "port": 8011,
        "transport": "http",
    },
)
class EnformerPredictTool:
    """Predict Enformer track activity for a DNA sequence."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence")
        if not sequence:
            return {"error": "Missing required parameter: sequence"}
        organism = (arguments.get("organism") or "human").lower()
        if organism not in ("human", "mouse"):
            return {"error": "organism must be 'human' or 'mouse'"}
        track_indices = arguments.get("track_indices")
        top_n = int(arguments.get("top_n") or 20)

        pred = _predict(sequence, organism)
        return {
            "model": "Enformer",
            "organism": organism,
            "n_tracks": int(pred.shape[1]),
            "n_bins": int(pred.shape[0]),
            "bin_size_bp": 128,
            "tracks": _top_center_tracks(pred, track_indices, top_n),
        }


@register_mcp_tool(
    tool_type_name="run_enformer_variant_effect",
    config={
        "description": (
            "Score a regulatory variant with Enformer: predicts tracks for the "
            "reference and alternate sequences (each 196,608 bp, variant at "
            "center) and returns the central-bin delta (alt - ref) per track — "
            "the canonical sequence-model variant-effect-on-expression score."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "ref_sequence": {
                    "type": "string",
                    "description": "Reference DNA sequence centered on the variant (cropped/padded to 196,608 bp).",
                },
                "alt_sequence": {
                    "type": "string",
                    "description": "Alternate DNA sequence (same length/centering as ref).",
                },
                "organism": {
                    "type": "string",
                    "description": "'human' (default) or 'mouse'.",
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
        "server_name": "Enformer MCP Server",
        "host": "127.0.0.1",
        "port": 8011,
        "transport": "http",
    },
)
class EnformerVariantEffectTool:
    """Score a regulatory variant as the Enformer central-bin alt-ref delta."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        ref = arguments.get("ref_sequence")
        alt = arguments.get("alt_sequence")
        if not (ref and alt):
            return {
                "error": "Missing required parameter(s): ref_sequence, alt_sequence"
            }
        organism = (arguments.get("organism") or "human").lower()
        track_indices = arguments.get("track_indices")
        top_n = int(arguments.get("top_n") or 20)

        ref_center = _predict(ref, organism)[N_BINS // 2]
        alt_center = _predict(alt, organism)[N_BINS // 2]
        delta = alt_center - ref_center
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
            "model": "Enformer",
            "organism": organism,
            "n_tracks": int(delta.shape[0]),
            "tracks": tracks,
        }


if __name__ == "__main__":
    start_mcp_server()
