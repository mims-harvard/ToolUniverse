"""Keyless ESM-2 masked-marginal missense variant-effect scoring.

This tool scores a single-amino-acid (missense) protein variant with the
**masked-marginal** log-likelihood ratio of Meier et al. (2021,
"Language models enable zero-shot prediction of the effects of mutations on
protein function", NeurIPS):

    score = log P(mutant | masked context) - log P(wild-type | masked context)

The variant position is replaced with the model's ``<mask>`` token, ESM-2
predicts the residue distribution at that position, and the score is the
log-ratio of the mutant vs. wild-type amino-acid probabilities. A **negative**
score means the model favors the wild-type residue over the mutant — the
variant is disfavored and is a candidate loss-of-function / destabilizing
change; a score near zero or positive means the substitution is tolerated by
the model.

Why this exists alongside the ``ESM_*`` tools
---------------------------------------------
ToolUniverse already exposes richer ESM scoring via EvolutionaryScale's ESMC
API (``ESM_score_sequence``, ``ESM_score_variant_sae_disruption``, …) — prefer
those when you have an ``ESM_API_KEY``. This tool fills a different niche: it
runs **without any API key** over HuggingFace's free ``hf-inference`` provider,
so it works as a zero-setup fallback for a quick single-variant screen.

It composes the generic :class:`HuggingFaceInferenceTool` for the HTTP/fill-mask
plumbing and adds only the masked-marginal method on top, so there is no
duplicated network code. ``run()`` never raises — every path returns a dict
with a ``status`` key.
"""

import math
from typing import Any, Dict, Optional

from .base_tool import BaseTool
from .huggingface_inference_tool import HuggingFaceInferenceTool
from .tool_registry import register_tool

# ESM-2 family default. The small vocab (~33 tokens) is shared across sizes, so
# requesting this many fill-mask candidates returns every amino-acid token.
_DEFAULT_MODEL = "facebook/esm2_t33_650M_UR50D"
_VOCAB_TOP_K = 33
# hf-inference truncates very long inputs; keep a budget that leaves room for
# the <cls>/<eos> tokens. Longer sequences are windowed around the variant.
_MAX_CONTEXT = 1022
# The 20 standard amino acids — the only residues a missense call substitutes.
_STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")


@register_tool("ESM2VariantEffectTool")
class ESM2VariantEffectTool(BaseTool):
    """Score a missense protein variant with ESM-2 masked-marginal LLR (no key)."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}
        # Compose the generic HF inference tool for the actual fill-mask call.
        self._hf = HuggingFaceInferenceTool({"name": "esm2-variant-hf"})

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}

        sequence = "".join(str(args.get("sequence", "")).split()).upper()
        if not sequence or not sequence.isalpha():
            return _err(
                "sequence is required (a wild-type protein sequence in "
                "1-letter amino-acid code)."
            )

        position = args.get("position")
        try:
            position = int(position)
        except (TypeError, ValueError):
            return _err("position is required and must be a 1-based integer.")
        if not 1 <= position <= len(sequence):
            return _err(
                f"position {position} is out of range for a sequence of "
                f"length {len(sequence)} (use 1-based coordinates)."
            )

        mutant = str(args.get("mutant", "")).strip().upper()
        if mutant not in _STANDARD_AA:
            return _err(
                f"mutant must be one standard amino acid (one of {sorted(_STANDARD_AA)}), "
                f"got {args.get('mutant')!r}."
            )

        wild_type = sequence[position - 1]
        declared_wt = args.get("wild_type")
        if declared_wt:
            declared_wt = str(declared_wt).strip().upper()
            if declared_wt != wild_type:
                return _err(
                    f"wild_type {declared_wt!r} does not match residue "
                    f"{wild_type!r} at position {position} of the supplied "
                    "sequence — check the coordinates / sequence."
                )
        if mutant == wild_type:
            return _err(
                f"mutant equals the wild-type residue ({wild_type} at position "
                f"{position}); a missense variant must change the amino acid."
            )

        # Window long sequences around the variant so the input fits the model.
        window, local_idx, win_start, windowed = self._window(sequence, position)

        masked = " ".join(
            "<mask>" if i == local_idx else aa for i, aa in enumerate(window)
        )
        model_id = args.get("model_id") or _DEFAULT_MODEL

        fill = self._hf.run(
            {
                "operation": "fill_mask",
                "model_id": model_id,
                "text": masked,
                "top_k": _VOCAB_TOP_K,
                "wait_for_model": bool(args.get("wait_for_model", False)),
            }
        )
        if fill.get("status") != "success":
            return fill  # propagate the loading/error dict unchanged

        probs = {
            p["token_str"]: p["score"]
            for p in fill["data"].get("predictions", [])
            if len(p.get("token_str", "")) == 1 and p["score"] is not None
        }
        p_wt, p_mut = probs.get(wild_type), probs.get(mutant)
        if not p_wt or not p_mut:
            missing = wild_type if not p_wt else mutant
            return _err(
                f"Model {model_id} did not return a probability for residue "
                f"{missing!r}; cannot compute the log-likelihood ratio."
            )

        llr = math.log(p_mut) - math.log(p_wt)
        if llr < 0:
            direction = "mutant disfavored vs wild-type (candidate deleterious)"
        else:
            direction = "mutant tolerated or favored (likely neutral)"

        window_span = [win_start + 1, win_start + len(window)] if windowed else None

        return {
            "status": "success",
            "data": {
                "model_id": model_id,
                "variant": f"{wild_type}{position}{mutant}",
                "position": position,
                "wild_type": wild_type,
                "mutant": mutant,
                "p_wild_type": p_wt,
                "p_mutant": p_mut,
                "log_likelihood_ratio": llr,
                "direction": direction,
            },
            "metadata": {
                "method": "ESM-2 masked-marginal LLR (Meier et al. 2021)",
                "source": "HuggingFace hf-inference (no API key required)",
                "windowed": windowed,
                "window": window_span,
                "note": (
                    "Negative = mutant less likely than wild-type. Magnitude is "
                    "not a calibrated pathogenicity probability; rank variants or "
                    "calibrate against a reference set. For key-based ESMC scoring "
                    "use ESM_score_sequence / ESM_score_variant_sae_disruption."
                ),
            },
        }

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _window(sequence: str, position: int):
        """Return (window, local_index, window_start, windowed?) for the model.

        Sequences within the context budget are returned whole. Longer ones are
        clipped to a ``_MAX_CONTEXT`` window centered on the variant so the
        masked position keeps its real sequence neighborhood.
        """
        if len(sequence) <= _MAX_CONTEXT:
            return sequence, position - 1, 0, False
        half = _MAX_CONTEXT // 2
        start = max(0, (position - 1) - half)
        start = min(start, len(sequence) - _MAX_CONTEXT)
        window = sequence[start : start + _MAX_CONTEXT]
        return window, (position - 1) - start, start, True


def _err(message: str) -> Dict[str, Any]:
    return {"status": "error", "error": message, "source": "ESM2VariantEffectTool"}
