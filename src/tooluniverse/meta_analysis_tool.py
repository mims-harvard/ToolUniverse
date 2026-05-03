"""
MetaAnalysisTool — pure-Python fixed-effects and random-effects meta-analysis.

No external API calls. Implements inverse-variance weighting (fixed)
and DerSimonian-Laird estimator (random). Uses normal approximation
for p-values (no scipy dependency).
"""

import math
from typing import Any, Dict, List

from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("MetaAnalysisTool")
class MetaAnalysisTool(BaseTool):
    """Run fixed-effects or random-effects meta-analysis."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._meta_analyze(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Meta-analysis failed: {e}"}

    def _meta_analyze(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        studies = arguments.get("studies")
        if not studies or not isinstance(studies, list):
            return {
                "status": "error",
                "error": "Parameter 'studies' is required (list of study objects).",
            }

        if len(studies) < 2:
            return {
                "status": "error",
                "error": "At least 2 studies are required for meta-analysis.",
            }

        # Validate studies
        for i, s in enumerate(studies):
            if "effect_size" not in s or "se" not in s or "name" not in s:
                return {
                    "status": "error",
                    "error": f"Study at index {i} missing required fields (name, effect_size, se).",
                }
            if s["se"] <= 0:
                return {
                    "status": "error",
                    "error": f"Study '{s['name']}' has non-positive standard error ({s['se']}).",
                }

        method = arguments.get("method") or "random"
        if method not in ("fixed", "random"):
            return {
                "status": "error",
                "error": f"Unknown method '{method}'. Use 'fixed' or 'random'.",
            }

        k = len(studies)
        effects = [s["effect_size"] for s in studies]
        ses = [s["se"] for s in studies]
        variances = [se**2 for se in ses]

        # Fixed-effects weights: w_i = 1 / var_i
        w_fixed = [1.0 / v for v in variances]
        sum_w = sum(w_fixed)
        pooled_fixed = sum(w * e for w, e in zip(w_fixed, effects)) / sum_w

        # Cochran's Q statistic
        q_stat = sum(w * (e - pooled_fixed) ** 2 for w, e in zip(w_fixed, effects))
        q_df = k - 1

        # Q p-value via chi-squared survival function (normal approx for large df)
        q_p = _chi2_sf(q_stat, q_df)

        # I-squared
        i_squared = max(0.0, (q_stat - q_df) / q_stat * 100) if q_stat > 0 else 0.0

        # DerSimonian-Laird tau-squared
        c = sum_w - sum(w**2 for w in w_fixed) / sum_w
        tau_sq = max(0.0, (q_stat - q_df) / c) if c > 0 else 0.0

        if method == "fixed":
            weights = w_fixed
            pooled = pooled_fixed
            pooled_var = 1.0 / sum_w
            tau_sq_out = None
        else:
            # Random-effects weights: w_i = 1 / (var_i + tau^2)
            weights = [1.0 / (v + tau_sq) for v in variances]
            sum_w_re = sum(weights)
            pooled = sum(w * e for w, e in zip(weights, effects)) / sum_w_re
            pooled_var = 1.0 / sum_w_re
            tau_sq_out = round(tau_sq, 6)

        pooled_se = math.sqrt(pooled_var)
        z = pooled / pooled_se if pooled_se > 0 else 0.0
        p_value = 2 * _norm_sf(abs(z))
        ci_lower = pooled - 1.96 * pooled_se
        ci_upper = pooled + 1.96 * pooled_se

        # Per-study details
        total_weight = sum(weights)
        per_study: List[Dict[str, Any]] = []
        for s, w in zip(studies, weights):
            se = s["se"]
            per_study.append(
                {
                    "name": s["name"],
                    "effect_size": round(s["effect_size"], 6),
                    "se": round(se, 6),
                    "weight_pct": round(w / total_weight * 100, 2),
                    "ci_lower": round(s["effect_size"] - 1.96 * se, 6),
                    "ci_upper": round(s["effect_size"] + 1.96 * se, 6),
                }
            )

        # Interpretation
        sig = (
            "statistically significant"
            if p_value < 0.05
            else "not statistically significant"
        )
        het_text = (
            f"Low heterogeneity (I²={round(i_squared, 1)}%)"
            if i_squared < 25
            else f"Moderate heterogeneity (I²={round(i_squared, 1)}%)"
            if i_squared < 75
            else f"High heterogeneity (I²={round(i_squared, 1)}%)"
        )
        interpretation = (
            f"{'Random' if method == 'random' else 'Fixed'}-effects meta-analysis of {k} studies. "
            f"Pooled effect = {round(pooled, 4)} (95% CI: {round(ci_lower, 4)} to {round(ci_upper, 4)}), "
            f"p = {_format_p(p_value)}, {sig}. "
            f"{het_text}."
        )
        if method == "random" and tau_sq_out and tau_sq_out > 0:
            interpretation += f" Between-study variance (tau²) = {tau_sq_out}."

        return {
            "status": "success",
            "data": {
                "method": method,
                "num_studies": k,
                "pooled_effect": round(pooled, 6),
                "pooled_se": round(pooled_se, 6),
                "pooled_ci_lower": round(ci_lower, 6),
                "pooled_ci_upper": round(ci_upper, 6),
                "pooled_z": round(z, 4),
                "pooled_p_value": round(p_value, 8),
                "heterogeneity": {
                    "Q": round(q_stat, 4),
                    "Q_df": q_df,
                    "Q_p_value": round(q_p, 6),
                    "I_squared": round(i_squared, 2),
                    "tau_squared": tau_sq_out,
                },
                "per_study": per_study,
                "interpretation": interpretation,
            },
        }


# ---------- Pure-Python statistical helpers (no scipy) ----------


def _norm_sf(z: float) -> float:
    """Standard normal survival function P(Z > z) using Abramowitz & Stegun approximation."""
    if z < 0:
        return 1.0 - _norm_sf(-z)
    # Rational approximation (A&S 26.2.17, max error 7.5e-8)
    p = 0.2316419
    b1, b2, b3, b4, b5 = (
        0.319381530,
        -0.356563782,
        1.781477937,
        -1.821255978,
        1.330274429,
    )
    t = 1.0 / (1.0 + p * z)
    phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
    return phi * t * (b1 + t * (b2 + t * (b3 + t * (b4 + t * b5))))


def _chi2_sf(x: float, df: int) -> float:
    """Chi-squared survival function using Wilson-Hilferty normal approximation."""
    if df <= 0 or x < 0:
        return 1.0
    if df == 1 and x == 0:
        return 1.0
    # Wilson-Hilferty approximation
    z = ((x / df) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * df))) / math.sqrt(
        2.0 / (9.0 * df)
    )
    return _norm_sf(z)


def _format_p(p: float) -> str:
    """Format p-value for display."""
    if p < 0.001:
        return f"{p:.2e}"
    return f"{p:.4f}"
