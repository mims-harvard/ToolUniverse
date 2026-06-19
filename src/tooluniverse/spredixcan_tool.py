"""Summary-based transcriptome-wide association (S-PrediXcan, pure NumPy).

S-PrediXcan (Barbeira et al., Nature Communications 2018; the summary-statistics
form of PrediXcan) tests a gene for association with a trait by combining a
gene-expression prediction model (per-SNP eQTL weights) with GWAS summary
statistics (per-SNP z-scores), giving one z-score per gene without individual-
level data. It is the standard TWAS done from summary stats.

The gene-level z-score (Barbeira eq. for the analytic approximation) is::

    Z_gene = sum_i  w_i * sigma_i * Z_i  /  sqrt( w^T Gamma w )

where ``w_i`` is the eQTL weight, ``Z_i`` the GWAS z-score and ``sigma_i`` the SNP
standard deviation for SNP i, and ``Gamma`` is the SNP covariance matrix. When a
covariance matrix is supplied it is used directly; otherwise the SNPs are treated
as independent (``Gamma = diag(sigma^2)``), the standard approximation for
LD-pruned models. This is deterministic linear algebra, so it runs and is
testable directly (no LD reference panel needed when SNPs are independent).

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

Reference
---------
Barbeira AN, Dickinson SP, Bonazzola R, et al. "Exploring the phenotypic
consequences of tissue specific gene expression variation inferred from GWAS
summary statistics." Nature Communications 9, 1825 (2018).
"""

import math
from typing import Any, Dict, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool


def _norm_p(z: float) -> float:
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))


@register_tool("SPrediXcanTool")
class SPrediXcanTool(BaseTool):
    """Summary-based TWAS gene z-score from eQTL weights + GWAS z-scores."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        parsed = self._validate(args)
        if isinstance(parsed, dict):
            return parsed
        w, z, sigma, cov = parsed

        numerator = float(np.sum(w * sigma * z))
        if cov is not None:
            var_gene = float(w @ cov @ w)
        else:
            var_gene = float(np.sum((w * sigma) ** 2))  # independent SNPs
        if var_gene <= 0:
            return self._err(
                "Degenerate gene model (w^T Gamma w <= 0); check weights/covariance."
            )
        z_gene = numerator / math.sqrt(var_gene)
        if z_gene >= 0:
            direction = "increased expression associated with higher trait"
        else:
            direction = "increased expression associated with lower trait"
        return {
            "status": "success",
            "data": {
                "n_snps": int(len(w)),
                "twas_zscore": z_gene,
                "p_value": _norm_p(z_gene),
                "direction": direction,
            },
            "metadata": {
                "method": "S-PrediXcan (Barbeira et al. 2018)",
                "ld_model": "supplied covariance"
                if cov is not None
                else "independent SNPs",
                "note": (
                    "Z_gene = sum_i w_i*sigma_i*Z_i / sqrt(w^T Gamma w). With no "
                    "covariance, SNPs are assumed independent (valid for LD-pruned "
                    "models). Two-sided p uses a normal approximation."
                ),
            },
        }

    # -------------------------------------------------------------- inputs
    def _validate(self, args: Dict[str, Any]):
        weight = self._num_list(args.get("weight"), "weight")
        if isinstance(weight, dict):
            return weight
        gwas_z = self._num_list(args.get("gwas_z"), "gwas_z")
        if isinstance(gwas_z, dict):
            return gwas_z
        n = len(weight)
        if len(gwas_z) != n:
            return self._err("weight and gwas_z must have the same length.")
        if n < 2:
            return self._err("At least 2 SNPs are required.")

        sd = args.get("snp_sd")
        if sd is None:
            sigma = np.ones(n)
        else:
            sigma = self._num_list(sd, "snp_sd")
            if isinstance(sigma, dict):
                return sigma
            if len(sigma) != n:
                return self._err("snp_sd must have the same length as weight.")
            sigma = np.asarray(sigma)
            if np.any(sigma <= 0):
                return self._err("snp_sd values must be positive.")

        cov = None
        cov_in = args.get("covariance")
        if cov_in is not None:
            try:
                cov = np.asarray(cov_in, dtype=float)
            except (TypeError, ValueError):
                return self._err("covariance must be a numeric 2-D matrix.")
            if cov.shape != (n, n):
                return self._err(
                    f"covariance must be a {n}x{n} matrix (one row/col per SNP)."
                )
            # Keep sigma consistent with the covariance: when snp_sd was not given,
            # take sigma_i = sqrt(Gamma_ii) so the numerator (w_i*sigma_i*Z_i) and
            # the denominator (w^T Gamma w) use the same SNP scale.
            if sd is None:
                sigma = np.sqrt(np.clip(np.diag(cov), 0.0, None))
        return np.asarray(weight), np.asarray(gwas_z), sigma, cov

    def _num_list(self, v: Any, name: str):
        if not isinstance(v, (list, tuple)) or not v:
            return self._err(f"{name} must be a non-empty list of numbers.")
        try:
            return [float(x) for x in v]
        except (TypeError, ValueError):
            return self._err(f"{name} must contain only numbers.")

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"status": "error", "error": message, "source": "SPrediXcanTool"}
