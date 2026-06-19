"""Bayesian colocalization of two GWAS signals (coloc.abf, pure NumPy).

Given two sets of association summary statistics over the SAME set of SNPs in a
genomic region — e.g. a GWAS signal and an eQTL signal — this tool asks whether
the two traits share a single causal variant. It implements the approximate
Bayes factor colocalization of Giambartolomei et al. (PLoS Genetics 2014), the
``coloc.abf`` method, and returns the five posterior probabilities:

  * **PP0** — neither trait has a causal variant in the region
  * **PP1** — only trait 1 has a causal variant
  * **PP2** — only trait 2 has a causal variant
  * **PP3** — both traits are causal, but at *different* variants
  * **PP4** — both traits are causal and *share the same* variant (colocalization)

A high **PP4** (conventionally > 0.8) is evidence that the two signals are driven
by the same variant — the standard way to link, say, a GWAS locus to a gene via
an eQTL. Per-SNP Wakefield approximate Bayes factors are combined with the
standard priors (p1, p2, p12). This is deterministic math (no R, no LD matrix
needed), so it runs and is testable directly.

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Giambartolomei C, Vukcevic D, Schadt EE, et al. "Bayesian test for
colocalisation between pairs of genetic association studies using summary
statistics." PLoS Genetics 10, e1004383 (2014).
"""

import math
from typing import Any, Dict, List, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool

_HYPS = ["PP0", "PP1", "PP2", "PP3", "PP4"]


def _logsumexp(a: np.ndarray) -> float:
    m = float(np.max(a))
    return m + math.log(float(np.sum(np.exp(a - m))))


def _logdiff(a: float, b: float) -> float:
    """log(exp(a) - exp(b)) for a >= b (numerically stable).

    When a <= b (the off-diagonal cross-term has underflowed relative to the
    diagonal — i.e. a single shared peak dominates), the difference is zero, so
    return -inf (which makes the corresponding hypothesis posterior 0).
    """
    if a <= b:
        return float("-inf")
    return a + math.log1p(-math.exp(b - a))


@register_tool("ColocalizationTool")
class ColocalizationTool(BaseTool):
    """Bayesian colocalization (coloc.abf) of two summary-statistics signals."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        arrays = self._validate(args)
        if isinstance(arrays, dict):
            return arrays
        beta1, se1, beta2, se2 = arrays

        sd_prior = float(args.get("sd_prior") or 0.15)
        p1 = float(args.get("p1") or 1e-4)
        p2 = float(args.get("p2") or 1e-4)
        p12 = float(args.get("p12") or 1e-5)

        labf1 = self._log_abf(beta1, se1, sd_prior)
        labf2 = self._log_abf(beta2, se2, sd_prior)

        l1 = _logsumexp(labf1)
        l2 = _logsumexp(labf2)
        l4 = _logsumexp(labf1 + labf2)
        l3 = _logdiff(l1 + l2, l4)  # both causal, different SNPs (i != j)

        log_h = np.array(
            [
                0.0,
                math.log(p1) + l1,
                math.log(p2) + l2,
                math.log(p1) + math.log(p2) + l3,
                math.log(p12) + l4,
            ]
        )
        post = np.exp(log_h - _logsumexp(log_h))

        best = int(np.argmax(labf1 + labf2))  # SNP most likely shared under H4
        snps = args.get("snp")
        return {
            "status": "success",
            "data": {
                "n_snps": int(len(beta1)),
                "posteriors": {h: float(post[i]) for i, h in enumerate(_HYPS)},
                "pp4_colocalization": float(post[4]),
                "best_causal_snp": (
                    str(snps[best])
                    if isinstance(snps, (list, tuple)) and best < len(snps)
                    else best
                ),
                "interpretation": self._interpret(float(post[4]), float(post[3])),
            },
            "metadata": {
                "method": "coloc.abf (Giambartolomei 2014)",
                "priors": {"p1": p1, "p2": p2, "p12": p12, "sd_prior": sd_prior},
                "note": (
                    "PP4 = posterior prob the two traits share one causal variant "
                    "(>0.8 = strong colocalization). Assumes a single causal variant "
                    "per trait and both signals over the same SNP set."
                ),
            },
        }

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _log_abf(beta: np.ndarray, se: np.ndarray, sd_prior: float) -> np.ndarray:
        """Per-SNP Wakefield log approximate Bayes factor (H1 vs H0)."""
        v = se**2
        w = sd_prior**2
        r = w / (w + v)
        z2 = (beta / se) ** 2
        return 0.5 * np.log(1.0 - r) + 0.5 * r * z2

    @staticmethod
    def _interpret(pp4: float, pp3: float) -> str:
        if pp4 >= 0.8:
            return "strong colocalization (shared causal variant)"
        if pp3 >= 0.8:
            return "distinct causal variants (both associated, not shared)"
        if pp4 >= 0.5:
            return "suggestive colocalization"
        return "inconclusive (insufficient evidence to distinguish hypotheses)"

    def _validate(self, args: Dict[str, Any]):
        keys = ["beta1", "se1", "beta2", "se2"]
        cols = []
        for k in keys:
            v = args.get(k)
            if not isinstance(v, (list, tuple)) or not v:
                return self._err(f"{k} must be a non-empty list of numbers.")
            try:
                cols.append(np.asarray(v, dtype=float))
            except (TypeError, ValueError):
                return self._err(f"{k} must contain only numbers.")
        n = len(cols[0])
        if any(len(c) != n for c in cols):
            return self._err("beta1, se1, beta2, se2 must all have the same length.")
        if n < 2:
            return self._err("At least 2 SNPs are required.")
        if np.any(cols[1] <= 0) or np.any(cols[3] <= 0):
            return self._err("Standard errors (se1, se2) must be positive.")
        return cols[0], cols[1], cols[2], cols[3]

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "ColocalizationTool"}
