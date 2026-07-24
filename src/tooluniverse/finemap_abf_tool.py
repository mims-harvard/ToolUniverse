"""Single-causal-variant fine-mapping by approximate Bayes factors (pure NumPy).

Given per-SNP association summary statistics (effect size + standard error) for
the SNPs in a genomic region, this tool computes each SNP's **posterior
inclusion probability (PIP)** and the **credible set** of SNPs under the
single-causal-variant assumption, using Wakefield approximate Bayes factors
(Wakefield 2009; the per-SNP model that underlies ``coloc`` and ``FINEMAP``'s
1-causal case).

  * **PIP_i** = ABF_i / sum_j ABF_j — the posterior probability SNP i is the
    causal variant (assuming exactly one causal variant in the region).
  * **credible set** — the smallest set of SNPs whose PIPs sum to >= the
    requested coverage (default 0.95); the causal variant is in this set with
    that probability.

This is the fast, LD-free fine-mapping baseline (no LD matrix needed because it
assumes a single causal signal). For regions with multiple independent signals,
a full method (SuSiE / FINEMAP with LD) is needed — noted in the output. Pure
deterministic math, so it runs and is testable directly.

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Wakefield J. "Bayes factors for genome-wide association studies: comparison with
p-values." Genet Epidemiol 33, 79-86 (2009).
"""

import math
from typing import Any, Dict, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("FinemapABFTool")
class FinemapABFTool(BaseTool):
    """Single-causal-variant fine-mapping (PIPs + credible set) from summary stats."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        parsed = self._validate(args)
        if isinstance(parsed, dict):
            return parsed
        beta, se = parsed

        sd_prior = float(args.get("sd_prior") or 0.15)
        coverage = float(args.get("coverage") or 0.95)
        if not 0 < coverage <= 1:
            return self._err("coverage must be in (0, 1].")

        labf = self._log_abf(beta, se, sd_prior)
        pip = np.exp(labf - self._logsumexp(labf))  # normalize -> posterior incl. prob.

        n = len(beta)
        snps = args.get("snp")
        labels = (
            [str(s) for s in snps]
            if isinstance(snps, (list, tuple)) and len(snps) == n
            else [str(i) for i in range(n)]
        )

        order = np.argsort(pip)[::-1]  # highest PIP first
        cset, cum = [], 0.0
        for idx in order:
            cset.append({"snp": labels[idx], "pip": float(pip[idx])})
            cum += float(pip[idx])
            if cum >= coverage:
                break

        top = int(order[0])
        return {
            "status": "success",
            "data": {
                "n_snps": n,
                "top_snp": labels[top],
                "top_pip": float(pip[top]),
                "credible_set": cset,
                "credible_set_size": len(cset),
                "credible_set_coverage": cum,
                "pip": {labels[i]: float(pip[i]) for i in range(n)},
            },
            "metadata": {
                "method": "Wakefield ABF fine-mapping (single causal variant)",
                "coverage_requested": coverage,
                "sd_prior": sd_prior,
                "note": (
                    "PIP assumes exactly one causal variant in the region (no LD "
                    "matrix used). For loci with multiple independent signals use "
                    "SuSiE/FINEMAP with an LD reference."
                ),
            },
        }

    # -------------------------------------------------------------- helpers
    @staticmethod
    def _log_abf(beta: np.ndarray, se: np.ndarray, sd_prior: float) -> np.ndarray:
        """Per-SNP Wakefield log approximate Bayes factor (association vs null)."""
        v = se**2
        w = sd_prior**2
        r = w / (w + v)
        z2 = (beta / se) ** 2
        return 0.5 * np.log(1.0 - r) + 0.5 * r * z2

    @staticmethod
    def _logsumexp(a: np.ndarray) -> float:
        m = float(np.max(a))
        return m + math.log(float(np.sum(np.exp(a - m))))

    def _validate(self, args: Dict[str, Any]):
        beta_in, se_in = args.get("beta"), args.get("se")
        cols = []
        for k, v in (("beta", beta_in), ("se", se_in)):
            if not isinstance(v, (list, tuple)) or not v:
                return self._err(f"{k} must be a non-empty list of numbers.")
            try:
                cols.append(np.asarray(v, dtype=float))
            except (TypeError, ValueError):
                return self._err(f"{k} must contain only numbers.")
        beta, se = cols
        if len(beta) != len(se):
            return self._err("beta and se must have the same length.")
        if len(beta) < 2:
            return self._err("At least 2 SNPs are required to fine-map.")
        if np.any(se <= 0):
            return self._err("Standard errors (se) must be positive.")
        return beta, se

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "FinemapABFTool"}
