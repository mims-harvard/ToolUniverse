"""Two-sample Mendelian randomization estimators (pure NumPy, no R).

Given harmonized instrument-level summary statistics — the SNP-exposure and
SNP-outcome effect sizes and standard errors for a set of genetic instruments
(e.g. from ``OpenGWAS_get_mr_instruments``) — this tool computes the standard
two-sample MR causal estimate and its sensitivity analyses:

  * **IVW** (inverse-variance weighted, multiplicative random effects) — the
    primary causal estimate.
  * **MR-Egger** — slope (causal estimate robust to directional pleiotropy) plus
    the intercept (a directional-pleiotropy test).
  * **Weighted median** — consistent if <50% of instrument weight is invalid.
  * **Cochran's Q / I^2** — heterogeneity across instruments (invalid-instrument
    diagnostic).

This is the deterministic statistical core of TwoSampleMR's `mr()` (Hemani et
al., eLife 2018) reimplemented in NumPy, so it needs no R and is fully testable.
The weighted-median standard error uses a seeded parametric bootstrap (fixed
seed) so results are reproducible. p-values use the normal approximation
(``math.erf``) to avoid a SciPy dependency; with few instruments treat MR-Egger
p-values as approximate.

``run()`` returns a ``{status, data, metadata}`` dict and never raises.

References
----------
Bowden J, Davey Smith G, Burgess S. "Mendelian randomization with invalid
instruments: effect estimation and bias detection through Egger regression."
Int J Epidemiol 44, 512-525 (2015).
Bowden J, et al. "Consistent estimation in Mendelian randomization with some
invalid instruments using a weighted median estimator." Genet Epidemiol 40,
304-314 (2016).
"""

import math
from typing import Any, Dict, Optional

import numpy as np

from .base_tool import BaseTool
from .tool_registry import register_tool

_BOOTSTRAP = 1000
_SEED = 0


def _norm_p(z: float) -> float:
    """Two-sided p-value for a z-score via the normal approximation (no SciPy)."""
    return 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))


@register_tool("MendelianRandomizationTool")
class MendelianRandomizationTool(BaseTool):
    """Compute two-sample MR causal estimates from harmonized instrument data."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None):
        super().__init__(tool_config)
        self.tool_config = tool_config or {}

    # ------------------------------------------------------------------ run
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = arguments or {}
        arrays = self._validate(args)
        if isinstance(arrays, dict):  # error
            return arrays
        bx, bxse, by, byse = arrays

        estimates = {
            "ivw": self._ivw(bx, by, byse),
            "mr_egger": self._egger(bx, by, byse),
            "weighted_median": self._weighted_median(bx, bxse, by, byse),
        }
        # MR-Egger returns the intercept alongside the slope; the intercept is a
        # separate top-level field, so move it out of the slope estimate.
        egger_intercept = estimates["mr_egger"].pop("intercept")
        heterogeneity = self._heterogeneity(bx, by, byse, estimates["ivw"]["estimate"])
        return {
            "status": "success",
            "data": {
                "n_instruments": int(len(bx)),
                "estimates": estimates,
                "egger_intercept": egger_intercept,
                "heterogeneity": heterogeneity,
            },
            "metadata": {
                "method": "two-sample MR (IVW / MR-Egger / weighted median)",
                "note": (
                    "Estimates are the causal effect of exposure on outcome per "
                    "unit exposure. A non-zero MR-Egger intercept indicates "
                    "directional pleiotropy; high I^2 indicates heterogeneous "
                    "instruments. p-values use a normal approximation."
                ),
            },
        }

    # -------------------------------------------------------------- inputs
    def _validate(self, args: Dict[str, Any]):
        keys = ["beta_exposure", "se_exposure", "beta_outcome", "se_outcome"]
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
            return self._err("All four arrays must have the same length.")
        if n < 3:
            return self._err("At least 3 instruments are required (MR-Egger needs 3+).")
        bx, bxse, by, byse = cols
        if np.any(byse <= 0) or np.any(bxse <= 0):
            return self._err("Standard errors must be positive.")
        if np.any(bx == 0):
            return self._err("beta_exposure values must be non-zero (Wald ratios).")
        return bx, bxse, by, byse

    # -------------------------------------------------------------- methods
    @staticmethod
    def _ivw(bx: np.ndarray, by: np.ndarray, byse: np.ndarray) -> Dict[str, Any]:
        """Inverse-variance weighted estimate (multiplicative random effects)."""
        w = 1.0 / byse**2
        den = np.sum(w * bx**2)
        beta = float(np.sum(w * bx * by) / den)
        n = len(bx)
        q = float(np.sum(w * (by - beta * bx) ** 2))
        phi = max(1.0, q / (n - 1))  # random-effects overdispersion (floored at 1)
        se = float(np.sqrt(phi / den))
        return _estimate(beta, se)

    @staticmethod
    def _egger(bx: np.ndarray, by: np.ndarray, byse: np.ndarray) -> Dict[str, Any]:
        """MR-Egger: weighted regression of by on bx with an intercept."""
        n = len(bx)
        w = 1.0 / byse**2
        x = np.column_stack([np.ones(n), bx])  # [intercept, slope]
        wx = x * w[:, None]
        a = x.T @ wx  # X' W X  (2x2)
        b = wx.T @ by  # X' W y
        coef = np.linalg.solve(a, b)
        resid = by - x @ coef
        phi = max(1.0, float(np.sum(w * resid**2) / (n - 2)))  # overdispersion
        cov = phi * np.linalg.inv(a)
        se = np.sqrt(np.diag(cov))
        out = _estimate(float(coef[1]), float(se[1]))  # slope = causal estimate
        out["intercept"] = _estimate(float(coef[0]), float(se[0]))
        return out

    @staticmethod
    def _weighted_median(
        bx: np.ndarray, bxse: np.ndarray, by: np.ndarray, byse: np.ndarray
    ) -> Dict[str, Any]:
        """Weighted-median estimate with a seeded parametric-bootstrap SE."""
        ratios = by / bx
        weights = bx**2 / byse**2
        beta = _weighted_median_point(ratios, weights)

        rng = np.random.default_rng(_SEED)
        boot = np.empty(_BOOTSTRAP)
        for i in range(_BOOTSTRAP):
            bx_b = rng.normal(bx, bxse)
            by_b = rng.normal(by, byse)
            bx_b[bx_b == 0] = np.finfo(float).eps
            boot[i] = _weighted_median_point(by_b / bx_b, bx_b**2 / byse**2)
        return _estimate(float(beta), float(np.std(boot, ddof=1)))

    @staticmethod
    def _heterogeneity(
        bx: np.ndarray, by: np.ndarray, byse: np.ndarray, ivw_beta: float
    ) -> Dict[str, Any]:
        w = 1.0 / byse**2
        q = float(np.sum(w * (by - ivw_beta * bx) ** 2))
        df = int(len(bx) - 1)
        i2 = max(0.0, (q - df) / q) if q > 0 else 0.0
        return {"cochran_q": q, "df": df, "i_squared": i2}

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": message,
            "source": "MendelianRandomizationTool",
        }


def _estimate(beta: float, se: float) -> Dict[str, Any]:
    z = beta / se if se > 0 else 0.0
    return {"estimate": beta, "se": se, "p_value": _norm_p(z)}


def _weighted_median_point(ratios: np.ndarray, weights: np.ndarray) -> float:
    """Bowden (2016) weighted median of per-instrument Wald ratios."""
    order = np.argsort(ratios)
    r = ratios[order]
    w = weights[order]
    s = np.cumsum(w) - 0.5 * w
    s = s / np.sum(w)
    below = np.where(s < 0.5)[0]
    if len(below) == 0:
        return float(r[0])
    k = int(below[-1])
    if k + 1 >= len(r):
        return float(r[-1])
    return float(r[k] + (r[k + 1] - r[k]) * (0.5 - s[k]) / (s[k + 1] - s[k]))


_WEIGHTED_MEDIAN_POINT = _weighted_median_point  # exported for tests
