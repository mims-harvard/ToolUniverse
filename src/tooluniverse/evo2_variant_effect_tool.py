"""NVIDIA Evo 2 zero-shot variant-effect scoring (hosted NIM forward endpoint).

Evo 2 (Arc Institute; Brixi et al., 2025) is a genome foundation model with a
1 Mb context. NVIDIA hosts it as a NIM; the ``generate`` endpoint (autoregressive
sequence generation) is already wrapped as ``NvidiaNIM_evo2``. This tool adds the
genomics-relevant operation that endpoint does not cover: **zero-shot
variant-effect scoring** via the model's ``forward`` endpoint.

Method (NVIDIA's documented zero-shot recipe, e.g. the BRCA1 example): build a
DNA window for the reference and the alternate allele, run a forward pass on
each to obtain the model's logits, reduce them to an autoregressive sequence
log-likelihood, and report the delta::

    delta_loglik = loglik(alt) - loglik(ref)

A **negative** delta means the variant makes the sequence less likely under the
genome model — a candidate deleterious/disruptive change; near-zero means
tolerated.

The hosted ``/forward`` endpoint (a StripedHyena model, served in two sizes —
``arc/evo2-40b`` default and ``arc/evo2-7b``, selectable via the ``model`` arg)
returns the requested layer tensors as a base64-encoded NumPy ``.npz``. The final
logits are the ``unembed`` layer (npz key ``unembed.output``, shape
``[batch, seq_len, 512]`` over Evo 2's byte-level vocabulary). This tool decodes
that, computes the likelihood (byte-level tokens, token = ``ord(base)``), and
takes the delta. ``run()`` is key-gated (``NVIDIA_API_KEY``) and never raises.

Note: the forward/scoring path requires a live key to validate end-to-end; the
likelihood reduction is unit-tested independently against synthetic logits.

API: https://docs.nvidia.com/nim/bionemo/evo2/latest/endpoints.html
"""

import base64
import io
import json
import os
import zipfile
from typing import Any, Dict, Optional, Tuple

import numpy as np
import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_ARC_BASE = "https://health.api.nvidia.com/v1/biology/arc"
_DEFAULT_MODEL = "evo2-40b"
_VALID_MODELS = {"evo2-40b", "evo2-7b"}
_VALID_BASES = set("ACGTN")


@register_tool("Evo2VariantEffectTool")
class Evo2VariantEffectTool(BaseTool):
    """Score a variant with Evo 2's forward-pass delta log-likelihood (hosted NIM)."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}
        fields = self.tool_config.get("fields", {}) or {}
        # Base path up to (but not including) the model slug; the model is chosen
        # per call so one tool can score with either hosted Evo 2 size.
        self.arc_base = fields.get("base_url", _ARC_BASE).rstrip("/")
        self.timeout = int(fields.get("timeout", 120))

    @staticmethod
    def _resolve_model(model: Any) -> str:
        """Pick a valid hosted Evo 2 model, defaulting to evo2-40b."""
        candidate = str(model or _DEFAULT_MODEL).strip()
        return candidate if candidate in _VALID_MODELS else _DEFAULT_MODEL

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        api_key = os.environ.get("NVIDIA_API_KEY")
        if not api_key:
            return self._err(
                "NVIDIA_API_KEY not set (free key at https://build.nvidia.com)."
            )

        ref_seq, alt_seq, info = self._resolve_sequences(args)
        if info is not None:  # error dict
            return info

        model = self._resolve_model(args.get("model"))
        ll_ref = self._sequence_log_likelihood(ref_seq, api_key, model)
        if isinstance(ll_ref, dict):
            return ll_ref
        ll_alt = self._sequence_log_likelihood(alt_seq, api_key, model)
        if isinstance(ll_alt, dict):
            return ll_alt

        delta = ll_alt - ll_ref
        return {
            "status": "success",
            "data": {
                "delta_loglik": delta,
                "ref_loglik": ll_ref,
                "alt_loglik": ll_alt,
                "direction": (
                    "variant disfavored vs reference (candidate deleterious)"
                    if delta < 0
                    else "variant tolerated or favored (likely neutral)"
                ),
            },
            "metadata": {
                "model": f"Evo 2 (arc/{model})",
                "method": "forward-pass delta log-likelihood (zero-shot)",
                "source": "NVIDIA NIM (hosted; requires NVIDIA_API_KEY)",
                "note": (
                    "Negative delta = variant less likely under the genome model. "
                    "Not a calibrated pathogenicity probability; rank or calibrate "
                    "against a reference set."
                ),
            },
        }

    # -------------------------------------------------------------- inputs
    def _resolve_sequences(
        self, args: Dict[str, Any]
    ) -> Tuple[str, str, Optional[Dict[str, Any]]]:
        """Return (ref_seq, alt_seq, error_or_None).

        Two input styles:
          * ref_sequence + alt_sequence  (explicit windows), or
          * sequence + position + alternate  (point substitution at 1-based pos).
        """
        ref = self._clean(args.get("ref_sequence"))
        alt = self._clean(args.get("alt_sequence"))
        if ref and alt:
            if len(ref) != len(alt):
                return (
                    "",
                    "",
                    self._err(
                        "ref_sequence and alt_sequence must have the same length."
                    ),
                )
            return ref, alt, None

        seq = self._clean(args.get("sequence"))
        if seq and args.get("position") is not None and args.get("alternate"):
            try:
                pos = int(args["position"])
            except (TypeError, ValueError):
                return "", "", self._err("position must be a 1-based integer.")
            if not 1 <= pos <= len(seq):
                return (
                    "",
                    "",
                    self._err(
                        f"position {pos} out of range for sequence length {len(seq)}."
                    ),
                )
            allele = self._clean(args.get("alternate"))
            if len(allele) != 1:
                return (
                    "",
                    "",
                    self._err("alternate must be a single base for this mode."),
                )
            declared = args.get("reference")
            if declared and self._clean(declared) != seq[pos - 1]:
                return (
                    "",
                    "",
                    self._err(
                        f"reference {declared!r} does not match base {seq[pos - 1]!r} "
                        f"at position {pos}."
                    ),
                )
            alt_seq = seq[: pos - 1] + allele + seq[pos:]
            return seq, alt_seq, None

        return (
            "",
            "",
            self._err(
                "Provide either ref_sequence + alt_sequence, or sequence + position + "
                "alternate."
            ),
        )

    @staticmethod
    def _clean(value: Any) -> str:
        """Strip whitespace + uppercase; return '' if it is not a DNA string."""
        s = "".join(str(value or "").split()).upper()
        return s if s and set(s) <= _VALID_BASES else ""

    # ------------------------------------------------------------- scoring
    def _sequence_log_likelihood(self, seq: str, api_key: str, model: str):
        """Forward pass -> autoregressive log-likelihood (or an error dict)."""
        logits = self._forward(seq, api_key, model)
        if isinstance(logits, dict):
            return logits
        try:
            return self._autoregressive_loglik(seq, logits)
        except Exception as exc:  # defensive: malformed logits shape
            return self._err(f"Could not compute likelihood from Evo 2 logits: {exc}")

    @staticmethod
    def _autoregressive_loglik(seq: str, logits: np.ndarray) -> float:
        """Sum of log P(next base) under the model. logits[i] predicts base i+1.

        Evo 2 is byte-level: the vocabulary index of a base is ``ord(base)``.
        """
        # NIM returns (batch, seq_len, vocab); take batch 0 -> [L, vocab].
        arr = logits[0] if logits.ndim == 3 else logits
        n = min(len(seq), arr.shape[0])
        if n < 2:
            return 0.0
        arr = arr[: n - 1]  # positions 0..n-2 predict bases 1..n-1
        m = arr.max(axis=1, keepdims=True)
        log_z = m[:, 0] + np.log(np.exp(arr - m).sum(axis=1))
        next_tokens = np.frombuffer(seq[1:n].encode("ascii"), dtype=np.uint8)
        chosen = arr[np.arange(n - 1), next_tokens]
        return float(np.sum(chosen - log_z))

    def _forward(self, seq: str, api_key: str, model: str):
        """POST to the Evo 2 forward endpoint and return the logits array (or error)."""
        url = f"{self.arc_base}/{model}/forward"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # The hosted Evo 2 NIMs (both evo2-40b and evo2-7b) are StripedHyena
        # models: the final logits layer is 'unembed' (returns 'unembed.output',
        # shape (batch, L, 512)). ('output_layer' is the BioNeMo/Megatron name and
        # 422s on this endpoint.)
        payload = {"sequence": seq, "output_layers": ["unembed"]}
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            return self._err(f"Evo 2 request timed out after {self.timeout}s.")
        except requests.exceptions.RequestException as exc:
            return self._err(f"Evo 2 request failed: {exc}")
        if resp.status_code != 200:
            return self._err(f"Evo 2 HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            decoded = self._decode_response(resp)
            blob = base64.b64decode(decoded["data"])
            arrays = np.load(io.BytesIO(blob))
            return arrays["unembed.output"]
        except Exception as exc:
            return self._err(f"Could not parse Evo 2 response: {exc}")

    @staticmethod
    def _decode_response(resp) -> Dict[str, Any]:
        """The NVCF gateway returns inline JSON, or a zip for large payloads."""
        if "zip" in resp.headers.get("content-type", "").lower():
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                return json.loads(zf.read(zf.namelist()[0]))
        return resp.json()

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "Evo2VariantEffectTool"}
