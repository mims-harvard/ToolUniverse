#!/usr/bin/env python3
"""Population genetics calculator for HWE, Fst, inbreeding coefficients, and haplotypes.

Usage:
  python popgen_calculator.py --type hwe --AA 100 --Aa 50 --aa 25
  python popgen_calculator.py --type fst --p1 0.8 --p2 0.3 --n1 100 --n2 100
  python popgen_calculator.py --type inbreeding --pedigree "half-sib" --generations 3
  python popgen_calculator.py --type haplotypes --snps 5 --generations 3 --recomb_rate 0.5
"""
import argparse
import math
import sys


# ---------------------------------------------------------------------------
# HWE chi-square test
# ---------------------------------------------------------------------------

def hwe_test(obs_AA: int, obs_Aa: int, obs_aa: int) -> dict:
    """Test Hardy-Weinberg equilibrium for a biallelic locus.

    Args:
        obs_AA: Observed count of homozygous dominant genotypes.
        obs_Aa: Observed count of heterozygous genotypes.
        obs_aa: Observed count of homozygous recessive genotypes.

    Returns:
        dict with chi2, p_value, in_HWE flag, allele frequencies, expected counts.
    """
    n = obs_AA + obs_Aa + obs_aa
    if n == 0:
        return {"error": "Total count is zero; no data to test."}

    p = (2 * obs_AA + obs_Aa) / (2 * n)
    q = 1.0 - p

    exp_AA = n * p ** 2
    exp_Aa = n * 2 * p * q
    exp_aa = n * q ** 2

    # Chi-square with 1 degree of freedom (HWE test)
    chi2 = 0.0
    for obs, exp in [(obs_AA, exp_AA), (obs_Aa, exp_Aa), (obs_aa, exp_aa)]:
        if exp > 0:
            chi2 += (obs - exp) ** 2 / exp

    # Approximate p-value using chi-square CDF (1 df)
    p_value = _chi2_pvalue(chi2, df=1)

    return {
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
        "interpretation": _hwe_interpretation(chi2, p_value, obs_Aa, exp_Aa),
    }


def _hwe_interpretation(chi2: float, p_value: float, obs_het: int, exp_het: float) -> str:
    if p_value > 0.05:
        return "Locus is in Hardy-Weinberg equilibrium (p > 0.05)."
    direction = "excess" if obs_het > exp_het else "deficit"
    return (
        f"Significant deviation from HWE (chi2={chi2:.2f}, p={p_value:.4f}). "
        f"Heterozygote {direction} observed. "
        "Possible causes: selection, inbreeding, assortative mating, or genotyping error."
    )


# ---------------------------------------------------------------------------
# Fst (Weir-Cockerham simplified)
# ---------------------------------------------------------------------------

def weir_cockerham_fst(p1: float, p2: float, n1: int, n2: int) -> dict:
    """Simplified Weir-Cockerham Fst between two populations.

    Args:
        p1: Allele frequency in population 1.
        p2: Allele frequency in population 2.
        n1: Sample size (individuals) for population 1.
        n2: Sample size (individuals) for population 2.

    Returns:
        dict with Fst value and interpretation.
    """
    for val, name in [(p1, "p1"), (p2, "p2")]:
        if not 0.0 <= val <= 1.0:
            return {"error": f"{name}={val} is out of range [0, 1]."}
    if n1 <= 0 or n2 <= 0:
        return {"error": "Sample sizes must be positive integers."}

    p_bar = (n1 * p1 + n2 * p2) / (n1 + n2)

    if p_bar == 0.0 or p_bar == 1.0:
        return {
            "p1": p1, "p2": p2, "n1": n1, "n2": n2,
            "p_bar": round(p_bar, 4),
            "Fst": 0.0,
            "interpretation": "Allele is fixed or absent in both populations; Fst is undefined, set to 0.",
        }

    msp = (n1 * (p1 - p_bar) ** 2 + n2 * (p2 - p_bar) ** 2) / 1.0
    msg = (n1 * p1 * (1 - p1) + n2 * p2 * (1 - p2)) / (n1 + n2 - 2)

    denom = msp + msg
    fst = max(0.0, (msp - msg) / denom) if denom > 0 else 0.0

    return {
        "p1": p1,
        "p2": p2,
        "n1": n1,
        "n2": n2,
        "p_bar": round(p_bar, 4),
        "Fst": round(fst, 4),
        "interpretation": _fst_interpretation(fst),
    }


def _fst_interpretation(fst: float) -> str:
    if fst < 0.05:
        return f"Fst={fst:.4f}: Little genetic differentiation between populations."
    if fst < 0.15:
        return f"Fst={fst:.4f}: Moderate genetic differentiation."
    if fst < 0.25:
        return f"Fst={fst:.4f}: Great genetic differentiation."
    return f"Fst={fst:.4f}: Very great genetic differentiation (unusual for human populations)."


# ---------------------------------------------------------------------------
# Inbreeding coefficient from pedigree type
# ---------------------------------------------------------------------------

# Base inbreeding coefficients per generation for common pedigree types.
# F for one mating of that type; raised to the power of generations if requested.
PEDIGREE_BASE_F = {
    "self":          0.5,
    "full-sib":      0.25,
    "half-sib":      0.125,
    "first-cousin":  0.0625,
    "double-first-cousin": 0.125,
    "uncle-niece":   0.125,
    "aunt-nephew":   0.125,
    "half-first-cousin": 0.03125,
    "second-cousin": 0.015625,
}


def inbreeding_coefficient(pedigree: str, generations: int = 1) -> dict:
    """Compute inbreeding coefficient F for a known pedigree type.

    For iterated mating (generations > 1) uses the recurrence:
        F_t = base_F + (1 - base_F) * F_{t-1}
    which converges toward 1 with repeated inbreeding.

    Args:
        pedigree:    One of the pedigree type strings (e.g., "half-sib").
        generations: Number of successive inbreeding generations.

    Returns:
        dict with F value per generation and cumulative F.
    """
    pedigree_key = pedigree.lower().strip()
    if pedigree_key not in PEDIGREE_BASE_F:
        available = ", ".join(sorted(PEDIGREE_BASE_F))
        return {"error": f"Unknown pedigree type '{pedigree}'. Available: {available}"}
    if generations < 1:
        return {"error": "generations must be >= 1."}

    base_f = PEDIGREE_BASE_F[pedigree_key]

    # Compute F for each generation using the recurrence
    f_per_gen = []
    f_prev = 0.0
    for g in range(1, generations + 1):
        # Each generation: offspring of two relatives with F = f_prev
        f_g = base_f + (1 - base_f) * f_prev
        f_per_gen.append(round(f_g, 6))
        f_prev = f_g

    cumulative_f = f_per_gen[-1]

    return {
        "pedigree": pedigree_key,
        "base_F_per_mating": base_f,
        "generations": generations,
        "F_per_generation": f_per_gen,
        "cumulative_F": round(cumulative_f, 6),
        "heterozygosity_retained": round(1.0 - cumulative_f, 6),
        "interpretation": _inbreeding_interpretation(pedigree_key, generations, cumulative_f),
    }


def _inbreeding_interpretation(pedigree: str, generations: int, f: float) -> str:
    if f < 0.0625:
        severity = "low"
    elif f < 0.25:
        severity = "moderate"
    else:
        severity = "high"
    return (
        f"After {generations} generation(s) of {pedigree} mating, "
        f"F = {f:.4f} ({severity} inbreeding). "
        f"{(1 - f) * 100:.1f}% of heterozygosity retained."
    )


# ---------------------------------------------------------------------------
# Haplotype counting after recombination
# ---------------------------------------------------------------------------

def haplotype_count(n_snps: int, generations: int, recomb_rate: float) -> dict:
    """Estimate distinct haplotypes after recombination.

    Starting from 2^n_snps possible haplotypes, each generation recombination
    reshuffles combinations. We track:
      - Maximum theoretical haplotypes = 2^n_snps
      - Expected recombinants per generation per chromosome pair = (n_snps - 1) * recomb_rate
      - Cumulative probability of having recombined at least once across generations

    Args:
        n_snps:       Number of biallelic SNP loci in the region.
        generations:  Number of generations of random mating.
        recomb_rate:  Per-adjacent-interval recombination rate (0-1) per generation.

    Returns:
        dict with theoretical max haplotypes, expected recombinants, and estimates.
    """
    if n_snps < 1:
        return {"error": "n_snps must be >= 1."}
    if generations < 0:
        return {"error": "generations must be >= 0."}
    if not 0.0 <= recomb_rate <= 1.0:
        return {"error": "recomb_rate must be between 0 and 1."}

    max_haplotypes = 2 ** n_snps
    n_intervals = max(n_snps - 1, 0)

    # Expected number of crossovers per gamete per generation
    expected_crossovers_per_gen = n_intervals * recomb_rate

    # Probability that no recombination occurs anywhere across all intervals in one generation
    p_no_recomb_one_gen = (1.0 - recomb_rate) ** n_intervals

    # Over G generations: P(at least one recombination event somewhere)
    p_at_least_one_recomb = 1.0 - p_no_recomb_one_gen ** generations

    # Rough haplotype diversity estimate using decay of linkage disequilibrium.
    # Each generation, LD between flanking markers decays as (1 - r)^G.
    # Haplotypes diversify as: H(G) ~ H_max * (1 - (1-r)^G) + 2  (at least 2 ancestral)
    if generations == 0:
        estimated_haplotypes = 2  # ancestral
    else:
        ld_decay = (1.0 - recomb_rate) ** generations
        diversity_fraction = 1.0 - ld_decay
        estimated_haplotypes = max(2, int(round(2 + (max_haplotypes - 2) * diversity_fraction)))
        estimated_haplotypes = min(estimated_haplotypes, max_haplotypes)

    # Table of cumulative expected crossovers per generation
    gen_table = []
    cumulative_crossovers = 0.0
    for g in range(1, generations + 1):
        cumulative_crossovers += expected_crossovers_per_gen
        p_no_recomb_cum = p_no_recomb_one_gen ** g
        gen_table.append({
            "generation": g,
            "cumulative_expected_crossovers": round(cumulative_crossovers, 4),
            "p_no_recomb_so_far": round(p_no_recomb_cum, 6),
        })

    return {
        "n_snps": n_snps,
        "n_intervals": n_intervals,
        "recomb_rate_per_interval": recomb_rate,
        "generations": generations,
        "max_theoretical_haplotypes": max_haplotypes,
        "expected_crossovers_per_gamete_per_gen": round(expected_crossovers_per_gen, 4),
        "p_at_least_one_recombination": round(p_at_least_one_recomb, 6),
        "estimated_distinct_haplotypes_after_G_gen": estimated_haplotypes,
        "per_generation_table": gen_table,
        "interpretation": _haplotype_interpretation(
            n_snps, generations, recomb_rate, estimated_haplotypes, max_haplotypes
        ),
    }


def _haplotype_interpretation(
    n_snps: int, gens: int, r: float, estimated: int, max_h: int
) -> str:
    pct = 100.0 * estimated / max_h if max_h > 0 else 0.0
    if gens == 0:
        return f"Before recombination: 2 ancestral haplotypes out of {max_h} theoretically possible."
    return (
        f"After {gens} generation(s) with r={r} per interval: "
        f"~{estimated} of {max_h} possible haplotypes expected ({pct:.1f}% of maximum diversity). "
        f"{'High LD retained.' if r < 0.1 else 'Substantial LD decay expected.'}"
    )


# ---------------------------------------------------------------------------
# Chi-square p-value approximation (regularized incomplete gamma function)
# ---------------------------------------------------------------------------

def _chi2_pvalue(x: float, df: int = 1) -> float:
    """Approximate p-value for chi-square distribution using series expansion.

    Uses the regularized upper incomplete gamma function Q(a, x) = 1 - P(a, x).
    For df=1 this simplifies to: p = erfc(sqrt(x/2)).
    """
    if x <= 0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    # General case: use series / continued fraction via log-gamma
    # P(df/2, x/2) approximated via regularized incomplete gamma
    return _upper_incomplete_gamma_regularized(df / 2.0, x / 2.0)


def _upper_incomplete_gamma_regularized(a: float, x: float) -> float:
    """Q(a, x) = 1 - P(a, x) via series for small x, continued fraction for large x."""
    if x < 0:
        return 1.0
    if x == 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_series(a, x)
    return _gamma_continued_fraction(a, x)


def _gamma_series(a: float, x: float, max_iter: int = 200, eps: float = 1e-9) -> float:
    """Series representation of regularized lower incomplete gamma P(a,x)."""
    log_gamma_a = math.lgamma(a)
    ap = a
    delta = term = 1.0 / a
    total = term
    for _ in range(max_iter):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * eps:
            break
    return total * math.exp(-x + a * math.log(x) - log_gamma_a)


def _gamma_continued_fraction(a: float, x: float, max_iter: int = 200, eps: float = 1e-9) -> float:
    """Continued fraction representation of Q(a, x)."""
    log_gamma_a = math.lgamma(a)
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
    return math.exp(-x + a * math.log(x) - log_gamma_a) * h


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Population genetics calculator: HWE, Fst, inbreeding, haplotypes.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["hwe", "fst", "inbreeding", "haplotypes"],
        help="Calculation type.",
    )
    # HWE arguments
    p.add_argument("--AA", type=int, default=0, help="[hwe] Observed AA genotype count.")
    p.add_argument("--Aa", type=int, default=0, help="[hwe] Observed Aa genotype count.")
    p.add_argument("--aa", type=int, default=0, help="[hwe] Observed aa genotype count.")
    # Fst arguments
    p.add_argument("--p1", type=float, default=None, help="[fst] Allele freq in population 1.")
    p.add_argument("--p2", type=float, default=None, help="[fst] Allele freq in population 2.")
    p.add_argument("--n1", type=int, default=None, help="[fst] Sample size for population 1.")
    p.add_argument("--n2", type=int, default=None, help="[fst] Sample size for population 2.")
    # Inbreeding arguments
    p.add_argument(
        "--pedigree",
        type=str,
        default=None,
        help=(
            "[inbreeding] Pedigree type: self, full-sib, half-sib, first-cousin, "
            "double-first-cousin, uncle-niece, aunt-nephew, half-first-cousin, second-cousin."
        ),
    )
    p.add_argument("--generations", type=int, default=1, help="Number of generations (default 1).")
    # Haplotype arguments
    p.add_argument("--snps", type=int, default=None, help="[haplotypes] Number of SNP loci.")
    p.add_argument(
        "--recomb_rate",
        type=float,
        default=0.5,
        help="[haplotypes] Recombination rate per adjacent interval per generation (default 0.5).",
    )
    return p


def _print_result(result: dict) -> None:
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    for key, value in result.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            print(f"{key}:")
            for row in value:
                row_str = "  " + ", ".join(f"{k}={v}" for k, v in row.items())
                print(row_str)
        else:
            print(f"  {key}: {value}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    calc_type = args.type

    if calc_type == "hwe":
        result = hwe_test(args.AA, args.Aa, args.aa)

    elif calc_type == "fst":
        missing = [n for n, v in [("p1", args.p1), ("p2", args.p2), ("n1", args.n1), ("n2", args.n2)] if v is None]
        if missing:
            parser.error(f"--type fst requires: {', '.join('--' + m for m in missing)}")
        result = weir_cockerham_fst(args.p1, args.p2, args.n1, args.n2)

    elif calc_type == "inbreeding":
        if args.pedigree is None:
            parser.error("--type inbreeding requires --pedigree")
        result = inbreeding_coefficient(args.pedigree, args.generations)

    elif calc_type == "haplotypes":
        if args.snps is None:
            parser.error("--type haplotypes requires --snps")
        result = haplotype_count(args.snps, args.generations, args.recomb_rate)

    else:
        parser.error(f"Unknown type: {calc_type}")

    print(f"\n=== popgen_calculator: {calc_type.upper()} ===")
    _print_result(result)


if __name__ == "__main__":
    main()
