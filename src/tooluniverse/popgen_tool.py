"""
Population Genetics Calculator Tool

Computes Hardy-Weinberg equilibrium tests, Fst (Weir-Cockerham),
inbreeding coefficients, and haplotype diversity estimates.

No external API calls. Pure Python with stdlib math only.
"""

import math
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


# ---------------------------------------------------------------------------
# Chi-square p-value (regularized incomplete gamma function)
# ---------------------------------------------------------------------------


def _chi2_pvalue(x: float, df: int = 1) -> float:
    """Approximate p-value for chi-square distribution."""
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    return _upper_inc_gamma_reg(df / 2.0, x / 2.0)


def _upper_inc_gamma_reg(a: float, x: float) -> float:
    """Q(a, x) = 1 - P(a, x)."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_series(a, x)
    return _gamma_cf(a, x)


def _gamma_series(a: float, x: float, max_iter: int = 200, eps: float = 1e-9) -> float:
    """Series representation of regularized lower incomplete gamma P(a,x)."""
    lg = math.lgamma(a)
    ap = a
    term = 1.0 / a
    total = term
    for _ in range(max_iter):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * eps:
            break
    return total * math.exp(-x + a * math.log(x) - lg)


def _gamma_cf(a: float, x: float, max_iter: int = 200, eps: float = 1e-9) -> float:
    """Continued fraction representation of Q(a, x)."""
    lg = math.lgamma(a)
    fpmin = 1e-30
    b = x + 1.0 - a
    c = 1.0 / fpmin
    d = 1.0 / b
    h = d
    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < fpmin:
            d = fpmin
        c = b + an / c
        if abs(c) < fpmin:
            c = fpmin
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return math.exp(-x + a * math.log(x) - lg) * h


# ---------------------------------------------------------------------------
# Pedigree base F values
# ---------------------------------------------------------------------------

PEDIGREE_BASE_F = {
    "self": 0.5,
    "full-sib": 0.25,
    "half-sib": 0.125,
    "first-cousin": 0.0625,
    "double-first-cousin": 0.125,
    "uncle-niece": 0.125,
    "aunt-nephew": 0.125,
    "half-first-cousin": 0.03125,
    "second-cousin": 0.015625,
}


@register_tool("PopGenTool")
class PopGenTool(BaseTool):
    """Population genetics calculator: HWE, Fst, inbreeding, haplotypes."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "hwe_test": self._hwe_test,
            "fst": self._fst,
            "inbreeding": self._inbreeding,
            "haplotype_count": self._haplotype_count,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Calculation failed: {str(e)}"}

    def _hwe_test(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        obs_AA = arguments.get("obs_AA", 0)
        obs_Aa = arguments.get("obs_Aa", 0)
        obs_aa = arguments.get("obs_aa", 0)

        n = obs_AA + obs_Aa + obs_aa
        if n == 0:
            return {"status": "error", "error": "Total genotype count is zero."}

        p = (2 * obs_AA + obs_Aa) / (2 * n)
        q = 1.0 - p

        exp_AA = n * p**2
        exp_Aa = n * 2 * p * q
        exp_aa = n * q**2

        chi2 = 0.0
        for obs, exp in [(obs_AA, exp_AA), (obs_Aa, exp_Aa), (obs_aa, exp_aa)]:
            if exp > 0:
                chi2 += (obs - exp) ** 2 / exp

        p_value = _chi2_pvalue(chi2, df=1)

        if p_value > 0.05:
            interp = "Locus is in Hardy-Weinberg equilibrium (p > 0.05)."
        else:
            direction = "excess" if obs_Aa > exp_Aa else "deficit"
            interp = (
                f"Significant deviation from HWE (chi2={chi2:.2f}, p={p_value:.4f}). "
                f"Heterozygote {direction} observed."
            )

        return {
            "status": "success",
            "data": {
                "obs_AA": obs_AA,
                "obs_Aa": obs_Aa,
                "obs_aa": obs_aa,
                "exp_AA": round(exp_AA, 2),
                "exp_Aa": round(exp_Aa, 2),
                "exp_aa": round(exp_aa, 2),
                "allele_freq_A": round(p, 4),
                "allele_freq_a": round(q, 4),
                "chi2": round(chi2, 4),
                "p_value": round(p_value, 6),
                "df": 1,
                "in_HWE": p_value > 0.05,
                "interpretation": interp,
            },
        }

    def _fst(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        p1 = arguments.get("p1")
        p2 = arguments.get("p2")
        n1 = arguments.get("n1")
        n2 = arguments.get("n2")

        for name, val in [("p1", p1), ("p2", p2), ("n1", n1), ("n2", n2)]:
            if val is None:
                return {
                    "status": "error",
                    "error": f"Missing required parameter: {name}",
                }

        for val, name in [(p1, "p1"), (p2, "p2")]:
            if not 0.0 <= val <= 1.0:
                return {
                    "status": "error",
                    "error": f"{name}={val} is out of range [0, 1].",
                }
        if n1 <= 0 or n2 <= 0:
            return {
                "status": "error",
                "error": "Sample sizes must be positive integers.",
            }

        p_bar = (n1 * p1 + n2 * p2) / (n1 + n2)

        if p_bar == 0.0 or p_bar == 1.0:
            return {
                "status": "success",
                "data": {
                    "p1": p1,
                    "p2": p2,
                    "n1": n1,
                    "n2": n2,
                    "p_bar": round(p_bar, 4),
                    "Fst": 0.0,
                    "interpretation": "Allele is fixed or absent in both populations; Fst is 0.",
                },
            }

        msp = (n1 * (p1 - p_bar) ** 2 + n2 * (p2 - p_bar) ** 2) / 1.0
        msg = (n1 * p1 * (1 - p1) + n2 * p2 * (1 - p2)) / (n1 + n2 - 2)
        denom = msp + msg
        fst = max(0.0, (msp - msg) / denom) if denom > 0 else 0.0

        if fst < 0.05:
            interp = f"Fst={fst:.4f}: Little genetic differentiation."
        elif fst < 0.15:
            interp = f"Fst={fst:.4f}: Moderate genetic differentiation."
        elif fst < 0.25:
            interp = f"Fst={fst:.4f}: Great genetic differentiation."
        else:
            interp = f"Fst={fst:.4f}: Very great genetic differentiation."

        return {
            "status": "success",
            "data": {
                "p1": p1,
                "p2": p2,
                "n1": n1,
                "n2": n2,
                "p_bar": round(p_bar, 4),
                "Fst": round(fst, 4),
                "interpretation": interp,
            },
        }

    def _inbreeding(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        pedigree = arguments.get("pedigree")
        generations = arguments.get("generations", 1)

        if not pedigree:
            return {"status": "error", "error": "Missing required parameter: pedigree"}

        key = pedigree.lower().strip()
        if key not in PEDIGREE_BASE_F:
            return {
                "status": "error",
                "error": f"Unknown pedigree type '{pedigree}'. Available: {', '.join(sorted(PEDIGREE_BASE_F))}",
            }
        if generations < 1:
            return {"status": "error", "error": "generations must be >= 1."}

        base_f = PEDIGREE_BASE_F[key]
        f_per_gen = []
        f_prev = 0.0
        for _ in range(generations):
            f_g = base_f + (1 - base_f) * f_prev
            f_per_gen.append(round(f_g, 6))
            f_prev = f_g

        cumulative_f = f_per_gen[-1]

        return {
            "status": "success",
            "data": {
                "pedigree": key,
                "base_F_per_mating": base_f,
                "generations": generations,
                "F_per_generation": f_per_gen,
                "cumulative_F": round(cumulative_f, 6),
                "heterozygosity_retained": round(1.0 - cumulative_f, 6),
                "interpretation": (
                    f"After {generations} generation(s) of {key} mating, "
                    f"F = {cumulative_f:.4f}. "
                    f"{(1 - cumulative_f) * 100:.1f}% of heterozygosity retained."
                ),
            },
        }

    def _haplotype_count(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        n_snps = arguments.get("n_snps")
        generations = arguments.get("generations", 1)
        recomb_rate = arguments.get("recomb_rate", 0.5)

        if n_snps is None or n_snps < 1:
            return {"status": "error", "error": "n_snps must be >= 1."}
        if generations < 0:
            return {"status": "error", "error": "generations must be >= 0."}
        if not 0.0 <= recomb_rate <= 1.0:
            return {"status": "error", "error": "recomb_rate must be between 0 and 1."}

        max_haplotypes = 2**n_snps
        n_intervals = max(n_snps - 1, 0)
        expected_crossovers_per_gen = n_intervals * recomb_rate
        p_no_recomb_one_gen = (1.0 - recomb_rate) ** n_intervals
        p_at_least_one_recomb = 1.0 - p_no_recomb_one_gen**generations

        if generations == 0:
            estimated_haplotypes = 2
        else:
            ld_decay = (1.0 - recomb_rate) ** generations
            diversity_fraction = 1.0 - ld_decay
            estimated_haplotypes = max(
                2, int(round(2 + (max_haplotypes - 2) * diversity_fraction))
            )
            estimated_haplotypes = min(estimated_haplotypes, max_haplotypes)

        return {
            "status": "success",
            "data": {
                "n_snps": n_snps,
                "n_intervals": n_intervals,
                "recomb_rate_per_interval": recomb_rate,
                "generations": generations,
                "max_theoretical_haplotypes": max_haplotypes,
                "expected_crossovers_per_gamete_per_gen": round(
                    expected_crossovers_per_gen, 4
                ),
                "p_at_least_one_recombination": round(p_at_least_one_recomb, 6),
                "estimated_distinct_haplotypes": estimated_haplotypes,
                "interpretation": (
                    f"After {generations} generation(s) with r={recomb_rate}: "
                    f"~{estimated_haplotypes} of {max_haplotypes} possible haplotypes "
                    f"({100.0 * estimated_haplotypes / max_haplotypes:.1f}% of max diversity)."
                ),
            },
        }
