"""
ChromBPNet regulatory-variant effect — MCP Server.

ChromBPNet (Pampari et al., Nature Methods 2025) is a base-resolution deep
neural network that predicts chromatin accessibility (ATAC-seq / DNase-seq) from
DNA sequence, with the Tn5/DNase enzyme-bias regressed out. It is the modern,
bias-corrected successor to DeepSEA/Basset for non-coding regulatory variant
interpretation and TF-motif discovery, and underlies the ENCODE accessibility
model zoo.

Served as a ToolUniverse *remote* tool because it carries a heavy dependency
stack (`tensorflow` + Keras) and requires a trained, cell-type-specific model.
The provider—not the caller—selects one reviewed Keras v3 ``.keras`` artifact
through ``CHROMBPNET_MODEL_PATH``. Legacy ``.h5`` deserialization and
caller-selected model paths are intentionally rejected.

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
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict

import numpy as np
import tensorflow as tf

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
from tooluniverse.remote_argument_validation import require_argument_object
from tooluniverse.remote_sequence_input import (
    validate_sequence,
    validate_variant_sequences,
)

INPUT_LEN = 2114
OUTPUT_LEN = 1000
MAX_SEQUENCE_LENGTH = 10_000
_BASE_TO_CHANNEL = {"A": 0, "C": 1, "G": 2, "T": 3}
_MODELS: Dict[str, Any] = {}
_MODEL_INIT_LOCK = threading.Lock()
_INFERENCE_LOCK = threading.Lock()


def _configured_model_path() -> str:
    """Resolve the administrator-selected, safe Keras v3 model artifact."""
    configured = os.environ.get("CHROMBPNET_MODEL_PATH", "").strip()
    if not configured:
        raise RuntimeError("CHROMBPNET_MODEL_PATH is not configured")
    try:
        model_path = Path(configured).expanduser().resolve(strict=True)
    except (OSError, RuntimeError):
        raise RuntimeError("the configured ChromBPNet model is unavailable") from None
    if not model_path.is_file() or model_path.suffix.lower() != ".keras":
        raise RuntimeError("the configured ChromBPNet model must be a .keras file")
    return str(model_path)


def _get_model():
    """Lazy-load the reviewed Keras v3 model with safe deserialization enabled."""
    model_path = _configured_model_path()
    if model_path not in _MODELS:
        with _MODEL_INIT_LOCK:
            if model_path not in _MODELS:
                _MODELS[model_path] = tf.keras.models.load_model(
                    model_path, compile=False, safe_mode=True
                )
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
    with _INFERENCE_LOCK:
        out = model.predict(_encode(sequence), verbose=0)
    if not isinstance(out, (list, tuple)) or len(out) != 2:
        raise RuntimeError("ChromBPNet returned an invalid output structure")
    profile_logits = np.asarray(out[0], dtype=float).reshape(-1)
    count_values = np.asarray(out[1], dtype=float).reshape(-1)
    if (
        profile_logits.size != OUTPUT_LEN
        or count_values.size != 1
        or not np.isfinite(profile_logits).all()
        or not np.isfinite(count_values).all()
    ):
        raise RuntimeError("ChromBPNet returned invalid prediction values")
    log_counts = float(count_values[0])
    # softmax over the profile logits -> a probability distribution over positions
    z = profile_logits - profile_logits.max()
    profile = np.exp(z)
    profile_sum = profile.sum()
    if not math.isfinite(float(profile_sum)) or profile_sum <= 0:
        raise RuntimeError("ChromBPNet returned an invalid accessibility profile")
    profile /= profile_sum
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
            "probability distribution). The provider must configure a reviewed "
            "Keras v3 model with CHROMBPNET_MODEL_PATH."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 10000,
                    "pattern": "^[ACGTNacgtn]+$",
                    "description": "DNA sequence (A/C/G/T/N); cropped/padded to 2,114 bp around its center.",
                },
                "return_profile": {
                    "type": "boolean",
                    "description": "Include the full 1,000-bp profile array in the response (default false; summary stats are always returned).",
                },
            },
            "required": ["sequence"],
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        sequence = arguments.get("sequence")
        if not sequence:
            return {"error": "Missing required parameter: sequence"}
        try:
            sequence = validate_sequence(
                sequence,
                name="sequence",
                alphabet="ACGTN",
                max_length=MAX_SEQUENCE_LENGTH,
            )
        except ValueError as exc:
            return {"error": str(exc)}
        return_profile = arguments.get("return_profile")
        return_profile = False if return_profile is None else return_profile
        if not isinstance(return_profile, bool):
            return {"error": "return_profile must be a boolean."}

        try:
            model = _get_model()
            profile, log_counts = _predict(model, sequence)
        except Exception:
            return {"error": "Could not load the configured ChromBPNet model."}
        if log_counts > math.log(sys.float_info.max):
            return {"error": "ChromBPNet returned an invalid total-count prediction."}
        peak = int(np.argmax(profile))
        result = {
            "model": "ChromBPNet",
            "log_total_counts": log_counts,
            "total_counts": float(math.exp(log_counts)),
            "profile_length": OUTPUT_LEN,
            "peak_offset": peak - OUTPUT_LEN // 2,  # bp from profile center
        }
        if return_profile:
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
            "provider-configured reviewed Keras v3 model."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "ref_sequence": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 10000,
                    "pattern": "^[ACGTNacgtn]+$",
                    "description": "Reference DNA sequence centered on the variant (cropped/padded to 2,114 bp).",
                },
                "alt_sequence": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 10000,
                    "pattern": "^[ACGTNacgtn]+$",
                    "description": "Alternate DNA sequence (same length/centering as ref).",
                },
            },
            "required": ["ref_sequence", "alt_sequence"],
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
        try:
            arguments = require_argument_object(arguments)
        except ValueError as exc:
            return {"error": str(exc)}
        ref = arguments.get("ref_sequence")
        alt = arguments.get("alt_sequence")
        if not (ref and alt):
            return {
                "error": "Missing required parameter(s): ref_sequence, alt_sequence"
            }
        try:
            ref, alt = validate_variant_sequences(
                ref,
                alt,
                alphabet="ACGTN",
                max_length=MAX_SEQUENCE_LENGTH,
            )
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            model = _get_model()
            ref_profile, ref_log = _predict(model, ref)
            alt_profile, alt_log = _predict(model, alt)
        except Exception:
            return {"error": "Could not load the configured ChromBPNet model."}
        scores = ((alt_log - ref_log) / math.log(2.0), _jsd(ref_profile, alt_profile))
        if not all(math.isfinite(score) for score in scores):
            return {"error": "ChromBPNet returned invalid variant-effect scores."}
        return {
            "model": "ChromBPNet",
            "ref_log_total_counts": ref_log,
            "alt_log_total_counts": alt_log,
            "count_log2fc": scores[0],
            "profile_jsd": scores[1],
        }


if __name__ == "__main__":
    start_mcp_server()
