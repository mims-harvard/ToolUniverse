"""
Evo 2 zero-shot variant-effect scoring — MCP Server.

Evo 2 (Arc Institute; Brixi et al., 2025) is a genome foundation model with a
1 Mb context, hosted by NVIDIA as a NIM. This tool adds the genomics operation
the public `generate` endpoint does not cover: **zero-shot variant-effect
scoring** via the model's `forward` endpoint.

Method (NVIDIA's documented zero-shot recipe, e.g. the BRCA1 example): build a
DNA window for the reference and the alternate allele, run a forward pass on
each to obtain logits, reduce them to an autoregressive sequence
log-likelihood, and report the delta::

    delta_loglik = loglik(alt) - loglik(ref)

A **negative** delta means the variant makes the sequence less likely under the
genome model — a candidate deleterious/disruptive change; near-zero = tolerated.

Served as a ToolUniverse *remote* tool: the hosted-model call (the `NVIDIA_API_KEY`
and the NIM `/forward` request) lives on the server, keeping the core install and
its credentials out of the client. The server decodes the base64 ``.npz`` logits
(``output_layer`` = final logits, shape ``[seq_len, batch, 512]`` over Evo 2's
byte-level vocabulary), computes the likelihood (token = ``ord(base)``), and
returns the delta. ``run()`` never raises.

API: https://docs.nvidia.com/nim/bionemo/evo2/latest/endpoints.html

Reference
---------
Brixi G, Durrant MG, Ku J, et al. "Genome modeling and design across all domains
of life with Evo 2." (Arc Institute, 2025).
"""

import base64
import io
import json
import os
import zipfile
from typing import Any, Dict, Optional, Tuple

import numpy as np
import requests

from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server

_BASE_URL = os.environ.get(
    "EVO2_BASE_URL", "https://health.api.nvidia.com/v1/biology/arc/evo2-40b"
).rstrip("/")
_TIMEOUT = int(os.environ.get("EVO2_TIMEOUT", "120"))
_VALID_BASES = set("ACGTN")


def _clean(value: Any) -> str:
    """Strip whitespace + uppercase; return '' if it is not a DNA string."""
    s = "".join(str(value or "").split()).upper()
    return s if s and set(s) <= _VALID_BASES else ""


def _resolve_sequences(
    args: Dict[str, Any],
) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """Return (ref_seq, alt_seq, error_or_None).

    Two input styles:
      * ref_sequence + alt_sequence  (explicit windows), or
      * sequence + position + alternate  (point substitution at 1-based pos).
    """
    ref = _clean(args.get("ref_sequence"))
    alt = _clean(args.get("alt_sequence"))
    if ref and alt:
        if len(ref) != len(alt):
            return (
                "",
                "",
                {"error": "ref_sequence and alt_sequence must have the same length."},
            )
        return ref, alt, None

    seq = _clean(args.get("sequence"))
    if seq and args.get("position") is not None and args.get("alternate"):
        try:
            pos = int(args["position"])
        except (TypeError, ValueError):
            return "", "", {"error": "position must be a 1-based integer."}
        if not 1 <= pos <= len(seq):
            return (
                "",
                "",
                {
                    "error": f"position {pos} out of range for sequence length {len(seq)}."
                },
            )
        allele = _clean(args.get("alternate"))
        if len(allele) != 1:
            return "", "", {"error": "alternate must be a single base for this mode."}
        declared = args.get("reference")
        if declared and _clean(declared) != seq[pos - 1]:
            return (
                "",
                "",
                {
                    "error": f"reference {declared!r} does not match base {seq[pos - 1]!r} at position {pos}."
                },
            )
        return seq, seq[: pos - 1] + allele + seq[pos:], None

    return (
        "",
        "",
        {
            "error": "Provide either ref_sequence + alt_sequence, or sequence + position + alternate."
        },
    )


def _autoregressive_loglik(seq: str, logits: np.ndarray) -> float:
    """Sum of log P(next base) under the model. logits[i] predicts base i+1.

    Evo 2 is byte-level: the vocabulary index of a base is ``ord(base)``.
    """
    arr = logits[:, 0, :] if logits.ndim == 3 else logits  # [L, vocab]
    n = min(len(seq), arr.shape[0])
    if n < 2:
        return 0.0
    arr = arr[: n - 1]  # positions 0..n-2 predict bases 1..n-1
    m = arr.max(axis=1, keepdims=True)
    log_z = m[:, 0] + np.log(np.exp(arr - m).sum(axis=1))
    next_tokens = np.frombuffer(seq[1:n].encode("ascii"), dtype=np.uint8)
    chosen = arr[np.arange(n - 1), next_tokens]
    return float(np.sum(chosen - log_z))


def _decode_response(resp) -> Dict[str, Any]:
    """The NVCF gateway returns inline JSON, or a zip for large payloads."""
    if "zip" in resp.headers.get("content-type", "").lower():
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            return json.loads(zf.read(zf.namelist()[0]))
    return resp.json()


def _forward(seq: str, api_key: str):
    """POST to the Evo 2 forward endpoint and return the logits array (or error dict)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"sequence": seq, "output_layers": ["output_layer"]}
    try:
        resp = requests.post(
            f"{_BASE_URL}/forward", headers=headers, json=payload, timeout=_TIMEOUT
        )
    except requests.exceptions.Timeout:
        return {"error": f"Evo 2 request timed out after {_TIMEOUT}s."}
    except requests.exceptions.RequestException as exc:
        return {"error": f"Evo 2 request failed: {exc}"}
    if resp.status_code != 200:
        return {"error": f"Evo 2 HTTP {resp.status_code}: {resp.text[:200]}"}
    try:
        blob = base64.b64decode(_decode_response(resp)["data"])
        return np.load(io.BytesIO(blob))["output_layer"]
    except Exception as exc:
        return {"error": f"Could not parse Evo 2 response: {exc}"}


def _sequence_log_likelihood(seq: str, api_key: str):
    """Forward pass -> autoregressive log-likelihood (or an error dict)."""
    logits = _forward(seq, api_key)
    if isinstance(logits, dict):
        return logits
    try:
        return _autoregressive_loglik(seq, logits)
    except Exception as exc:  # defensive: malformed logits shape
        return {"error": f"Could not compute likelihood from Evo 2 logits: {exc}"}


@register_mcp_tool(
    tool_type_name="run_evo2_variant_effect",
    config={
        "description": (
            "Zero-shot variant-effect scoring with NVIDIA-hosted Evo 2 (Arc "
            "Institute genome foundation model). Runs the model's forward pass on "
            "the reference and alternate DNA windows and returns the delta "
            "log-likelihood (alt - ref). Negative = variant disfavored by the "
            "genome model (candidate deleterious). The hosted NIM call and "
            "NVIDIA_API_KEY live on the server. Complements NvidiaNIM_evo2 (which "
            "only generates sequences)."
        ),
        "parameter_schema": {
            "type": "object",
            "properties": {
                "ref_sequence": {
                    "type": "string",
                    "description": "Reference DNA window (A/C/G/T/N). Use with alt_sequence (same length).",
                },
                "alt_sequence": {
                    "type": "string",
                    "description": "Alternate DNA window, same length/centering as ref_sequence.",
                },
                "sequence": {
                    "type": "string",
                    "description": "Reference DNA window for point-substitution mode (use with position + alternate).",
                },
                "position": {
                    "type": "integer",
                    "description": "1-based position of the substituted base within `sequence`.",
                },
                "reference": {
                    "type": "string",
                    "description": "Optional reference base (single letter) at `position`, validated against `sequence`.",
                },
                "alternate": {
                    "type": "string",
                    "description": "Alternate base (single letter) substituted at `position`.",
                },
            },
            "required": [],
        },
    },
    mcp_config={
        "server_name": "Evo 2 Variant-Effect MCP Server",
        "host": "127.0.0.1",
        "port": 8034,
        "transport": "http",
    },
)
class Evo2VariantEffectTool:
    """Score a variant with Evo 2's forward-pass delta log-likelihood (hosted NIM)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        args = arguments or {}
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            return {
                "error": "NVIDIA_API_KEY not set on the server (free key at https://build.nvidia.com)."
            }

        ref_seq, alt_seq, err = _resolve_sequences(args)
        if err is not None:
            return err

        ll_ref = _sequence_log_likelihood(ref_seq, api_key)
        if isinstance(ll_ref, dict):
            return ll_ref
        ll_alt = _sequence_log_likelihood(alt_seq, api_key)
        if isinstance(ll_alt, dict):
            return ll_alt

        delta = ll_alt - ll_ref
        return {
            "model": "Evo 2 (arc/evo2-40b)",
            "method": "forward-pass delta log-likelihood (zero-shot)",
            "delta_loglik": delta,
            "ref_loglik": ll_ref,
            "alt_loglik": ll_alt,
            "direction": (
                "variant disfavored vs reference (candidate deleterious)"
                if delta < 0
                else "variant tolerated or favored (likely neutral)"
            ),
            "note": (
                "Negative delta = variant less likely under the genome model. Not a "
                "calibrated pathogenicity probability; rank or calibrate against a "
                "reference set."
            ),
        }


if __name__ == "__main__":
    start_mcp_server()
