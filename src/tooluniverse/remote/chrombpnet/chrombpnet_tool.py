"""
ChromBPNet regulatory-variant effect — MCP Server.

ChromBPNet (Pampari et al., Nature Methods 2025) is a base-resolution deep
neural network that predicts chromatin accessibility (ATAC-seq / DNase-seq) from
DNA sequence, with the Tn5/DNase enzyme-bias regressed out. It is the modern,
bias-corrected successor to DeepSEA/Basset for non-coding regulatory variant
interpretation and TF-motif discovery, and underlies the ENCODE accessibility
model zoo.

Served as a ToolUniverse *remote* tool because it carries a heavy dependency
stack (`tensorflow` + Keras) and requires a trained, cell-type-specific model
(a ``.h5`` from the ChromBPNet model zoo / your own training), referenced by
``model_path`` on the server.

The model takes a 2,114 bp one-hot sequence and outputs two heads: a 1,000 bp
accessibility *profile* (base-resolution shape) and a scalar *log total count*
(coverage magnitude).

Two operations:
  * run_chrombpnet_predict        -> predicted accessibility for one sequence
  * run_chrombpnet_variant_effect -> ref-vs-alt count log2FC + profile JS-divergence

Reference
---------
Pampari A, Shcherbina A, Kvon EZ, et al. "ChromBPNet: bias-factorized,
base-resolution deep learning models of chromatin accessibility reveal cis-
regulatory sequence syntax." Nature Methods (2025).
"""

import math
from typing import Any, Dict

import numpy as np
import tensorflow as tf

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

INPUT_LEN = 2114
OUTPUT_LEN = 1000
_BASE_TO_CHANNEL = {"A": 0, "C": 1, "G": 2, "T": 3}
_MODELS: Dict[str, Any] = {}


def _get_model(model_path: str):
    """Lazy-load and cache a trained ChromBPNet Keras model (custom losses ignored)."""
    if model_path not in _MODELS:
        _MODELS[model_path] = tf.keras.models.load_model(model_path, compile=False)
    return _MODELS[model_path]


def _encode(sequence: str) -> np.ndarray:
    """Center-crop / N-pad a DNA string to INPUT_LEN and one-hot encode (1, L, 4)."""
    seq = (sequence or "").strip().upper()
    if len(seq) > INPUT_LEN:
        start = (len(seq) - INPUT_LEN) // 2
        seq = seq[start : start + INPUT_LEN]
    elif len(seq) < INPUT_LEN:
        pad = INPUT_LEN - len(seq)
        left = pad // 2
        seq = "N" * left + seq + "N" * (pad - left)
    onehot = np.zeros((1, INPUT_LEN, 4), dtype=np.float32)
    for i, base in enumerate(seq):
        ch = _BASE_TO_CHANNEL.get(base)
        if ch is not None:  # N stays all-zero
            onehot[0, i, ch] = 1.0
    return onehot


def _predict(model, sequence: str):
    """Return (profile_probabilities[OUTPUT_LEN], log_total_counts) for one sequence."""
    out = model.predict(_encode(sequence), verbose=0)
    profile_logits = np.asarray(out[0]).reshape(-1)  # (OUTPUT_LEN,)
    log_counts = float(np.asarray(out[1]).reshape(-1)[0])
    # softmax over the profile logits -> a probability distribution over positions
    z = profile_logits - profile_logits.max()
    profile = np.exp(z)
    profile /= profile.sum()
    return profile, log_counts


def _jsd(p: np.ndarray, q: np.ndarray) -> float:
    """Jensen-Shannon divergence (base-2) between two probability profiles."""
    m = 0.5 * (p + q)

    def _kl(a, b):
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


@register_mcp_tool(
    tool_type_name="run_chrombpnet_predict",
    config={
        "description": (
            "Predict chromatin accessibility from a DNA sequence with a trained "
            "ChromBPNet model. The sequence is center-cropped / N-padded to 2,114 "
            "bp; returns the predicted log total counts (coverage magnitude), the "
            "total counts, and the base-resolution accessibility profile (1,000 bp "
            "probability distribution). Requires a server-side model_path (.h5)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "model_path": {
                    "type": "string",
                    "description": "Server-accessible path to a trained ChromBPNet Keras model (.h5), cell-type-specific.",
                },
                "sequence": {
                    "type": "string",
                    "description": "DNA sequence (A/C/G/T/N); cropped/padded to 2,114 bp around its center.",
                },
                "return_profile": {
                    "type": "boolean",
                    "description": "Include the full 1,000-bp profile array in the response (default false; summary stats are always returned).",
                },
            },
            "required": ["model_path", "sequence"],
        },
    },
    mcp_config={
        "server_name": "ChromBPNet MCP Server",
        "host": "127.0.0.1",
        "port": 8032,
        "transport": "http",
    },
)
class ChrombpnetPredictTool:
    """Predict accessibility (counts + profile) for a DNA sequence with ChromBPNet."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        model_path = arguments.get("model_path")
        sequence = arguments.get("sequence")
        if not model_path:
            return {"error": "Missing required parameter: model_path"}
        if not sequence:
            return {"error": "Missing required parameter: sequence"}

        try:
            model = _get_model(model_path)
        except Exception as exc:  # model file missing / unreadable
            return {"error": f"Could not load ChromBPNet model: {exc}"}
        profile, log_counts = _predict(model, sequence)
        peak = int(np.argmax(profile))
        result = {
            "model": "ChromBPNet",
            "log_total_counts": log_counts,
            "total_counts": float(math.exp(log_counts)),
            "profile_length": OUTPUT_LEN,
            "peak_offset": peak - OUTPUT_LEN // 2,  # bp from profile center
        }
        if arguments.get("return_profile"):
            result["profile"] = [float(x) for x in profile]
        return result


@register_mcp_tool(
    tool_type_name="run_chrombpnet_variant_effect",
    config={
        "description": (
            "Score a non-coding regulatory variant with ChromBPNet: predict "
            "accessibility for the reference and alternate sequences (each 2,114 "
            "bp, variant at center) and return the count log2 fold-change "
            "(alt vs ref accessibility magnitude) and the profile Jensen-Shannon "
            "divergence (change in base-resolution accessibility shape) — the "
            "canonical ChromBPNet variant-effect scores. Requires a server-side "
            "model_path (.h5)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "model_path": {
                    "type": "string",
                    "description": "Server-accessible path to a trained ChromBPNet Keras model (.h5), cell-type-specific.",
                },
                "ref_sequence": {
                    "type": "string",
                    "description": "Reference DNA sequence centered on the variant (cropped/padded to 2,114 bp).",
                },
                "alt_sequence": {
                    "type": "string",
                    "description": "Alternate DNA sequence (same length/centering as ref).",
                },
            },
            "required": ["model_path", "ref_sequence", "alt_sequence"],
        },
    },
    mcp_config={
        "server_name": "ChromBPNet MCP Server",
        "host": "127.0.0.1",
        "port": 8032,
        "transport": "http",
    },
)
class ChrombpnetVariantEffectTool:
    """Score a variant as ChromBPNet count log2FC + profile JS-divergence."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        model_path = arguments.get("model_path")
        ref = arguments.get("ref_sequence")
        alt = arguments.get("alt_sequence")
        if not model_path:
            return {"error": "Missing required parameter: model_path"}
        if not (ref and alt):
            return {
                "error": "Missing required parameter(s): ref_sequence, alt_sequence"
            }

        try:
            model = _get_model(model_path)
        except Exception as exc:
            return {"error": f"Could not load ChromBPNet model: {exc}"}
        ref_profile, ref_log = _predict(model, ref)
        alt_profile, alt_log = _predict(model, alt)
        return {
            "model": "ChromBPNet",
            "ref_log_total_counts": ref_log,
            "alt_log_total_counts": alt_log,
            "count_log2fc": (alt_log - ref_log) / math.log(2.0),
            "profile_jsd": _jsd(ref_profile, alt_profile),
        }


if __name__ == "__main__":
    start_mcp_server()
