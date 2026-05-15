"""Basic statistical tests using pure Python stdlib — no scipy, numpy, or pandas required.

Implements:
  chi_square   Chi-square goodness-of-fit test using the gamma function for the p-value.
  fisher_exact Fisher's exact test for a 2×2 table using combinatorics (hypergeometric).
  regression   Simple linear regression by ordinary least squares (closed-form solution).

Usage:
    python stat_tests.py --type chi_square --observed 100,50,25 --expected 87.5,50,37.5
    python stat_tests.py --type fisher_exact --a 10 --b 5 --c 3 --d 20
    python stat_tests.py --type regression --x "1,2,3,4,5" --y "2.1,4.0,5.9,8.1,10.0"
"""

import argparse
import math
import sys


# ---------------------------------------------------------------------------
# Utility: gamma-function-based chi-square CDF (upper tail)
# ---------------------------------------------------------------------------

def _ln_gamma(x: float) -> float:
    """Natural log of gamma(x) via Lanczos approximation (Numerical Recipes)."""
    if x <= 0:
        raise ValueError(f"lgamma argument must be > 0 (got {x}).")
    # Use math.lgamma which is in stdlib since Python 2.7
    return math.lgamma(x)


def _regularized_gamma_upper(a: float, x: float, max_iter: int = 300, eps: float = 1e-12) -> float:
    """
    Upper regularized incomplete gamma function: Q(a, x) = 1 - P(a, x).

    This is the chi-square survival function (p-value) when called as
    Q(df/2, chi2/2).

    Uses the continued fraction representation for x > a+1 and the series
    representation for x <= a+1, both from Numerical Recipes §6.2.
    """
    if x < 0 or a <= 0:
        raise ValueError(f"Invalid arguments: a={a}, x={x}.")
    if x == 0:
        return 1.0

    log_gamma_a = _ln_gamma(a)

    if x < a + 1.0:
        # Series representation for P(a, x)
        ap = a
        delta = 1.0 / a
        total = delta
        for _ in range(max_iter):
            ap += 1.0
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * eps:
                break
        return 1.0 - math.exp(-x + a * math.log(x) - log_gamma_a) * total
    else:
        # Continued fraction representation for Q(a, x) via Lentz method
        fpmin = 1e-300
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


def chi_square_p_value(chi2: float, df: int) -> float:
    """P-value for chi-square statistic with given degrees of freedom (upper tail)."""
    if df <= 0:
        raise ValueError(f"Degrees of freedom must be > 0 (got {df}).")
    if chi2 < 0:
        raise ValueError(f"Chi-square statistic must be >= 0 (got {chi2}).")
    if chi2 == 0:
        return 1.0
    return _regularized_gamma_upper(df / 2.0, chi2 / 2.0)


# ---------------------------------------------------------------------------
# Chi-square goodness-of-fit
# ---------------------------------------------------------------------------

def chi_square_gof(observed: list[float], expected: list[float]) -> dict:
    """
    Chi-square goodness-of-fit test.

    Args:
        observed: Observed counts/frequencies.
        expected: Expected counts/frequencies (same length; will be rescaled if totals differ).

    Returns dict with chi2, df, p_value, contributions.
    """
    if len(observed) != len(expected):
        raise ValueError(f"observed and expected must have the same length "
                         f"({len(observed)} vs {len(expected)}).")
    if len(observed) < 2:
        raise ValueError("Need at least 2 categories.")

    n_obs = sum(observed)
    n_exp = sum(expected)
    if n_obs <= 0:
        raise ValueError("Sum of observed counts must be > 0.")
    if n_exp <= 0:
        raise ValueError("Sum of expected counts must be > 0.")

    # Rescale expected to match observed total
    scale = n_obs / n_exp
    expected_scaled = [e * scale for e in expected]

    # Check minimum expected cell count
    min_exp = min(expected_scaled)
    warning = None
    if min_exp < 5:
        warning = (f"Warning: minimum expected count {min_exp:.2f} < 5. "
                   "Chi-square approximation may be unreliable. Consider Fisher's exact test.")

    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected_scaled))
    df = len(observed) - 1
    p = chi_square_p_value(chi2, df)

    contributions = [(o - e) ** 2 / e for o, e in zip(observed, expected_scaled)]

    return {
        "observed": observed,
        "expected_original": expected,
        "expected_scaled": expected_scaled,
        "scale_factor": scale,
        "chi2": chi2,
        "df": df,
        "p_value": p,
        "contributions": contributions,
        "warning": warning,
    }


def print_chi_square(res: dict) -> None:
    print("=" * 60)
    print("  Chi-Square Goodness-of-Fit Test")
    print("=" * 60)
    obs = res["observed"]
    exp = res["expected_scaled"]
    contribs = res["contributions"]
    print(f"  {'Category':>8}  {'Observed':>10}  {'Expected':>10}  {'(O-E)²/E':>10}")
    print(f"  {'-'*8}  {'-'*10}  {'-'*10}  {'-'*10}")
    for i, (o, e, c) in enumerate(zip(obs, exp, contribs)):
        print(f"  {i+1:>8}  {o:>10.2f}  {e:>10.4f}  {c:>10.4f}")
    print(f"  {'TOTAL':>8}  {sum(obs):>10.2f}  {sum(exp):>10.4f}  {sum(contribs):>10.4f}")
    print()
    if abs(res["scale_factor"] - 1.0) > 1e-9:
        print(f"  Note: Expected rescaled by factor {res['scale_factor']:.4f} to match observed total.")
        print()
    print(f"  χ²  = {res['chi2']:.4f}")
    print(f"  df  = {res['df']}  (k - 1 = {len(obs)} - 1)")
    print(f"  p   = {res['p_value']:.6f}")
    print()
    sig = res["p_value"] < 0.05
    print(f"  Result: {'SIGNIFICANT' if sig else 'NOT significant'} at α = 0.05")
    if sig:
        print("  Observed distribution differs significantly from expected.")
    else:
        print("  No significant deviation from expected distribution.")
    if res["warning"]:
        print()
        print(f"  {res['warning']}")
    print()
    print("  Verification:")
    check = sum((o - e) ** 2 / e for o, e in zip(obs, exp))
    assert abs(check - res["chi2"]) < 1e-8, "Chi2 mismatch"
    print(f"    Σ (O-E)²/E = {check:.6f}  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Fisher's exact test (2×2)
# ---------------------------------------------------------------------------

def _log_comb(n: int, k: int) -> float:
    """log C(n, k) using log-gamma for large values."""
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def _hypergeometric_pmf(k: int, n1: int, n2: int, n: int) -> float:
    """P(X = k) where X ~ Hypergeometric(n1, n2, n). n = total draws."""
    return math.exp(_log_comb(n1, k) + _log_comb(n2, n - k) - _log_comb(n1 + n2, n))


def fisher_exact(a: int, b: int, c: int, d: int, alternative: str = "two-sided") -> dict:
    """
    Fisher's exact test for a 2×2 contingency table.

    Table layout:
        +----------+----------+
        | a (TP)   | b (FP)   |  row 1 total = a + b
        | c (FN)   | d (TN)   |  row 2 total = c + d
        +----------+----------+
          col1=a+c   col2=b+d    N = a+b+c+d

    Args:
        a, b, c, d: Cell counts (non-negative integers).
        alternative: "two-sided", "less", or "greater".

    Returns dict with odds_ratio, p_value.
    """
    for name, val in [("a", a), ("b", b), ("c", c), ("d", d)]:
        if val < 0:
            raise ValueError(f"{name} must be >= 0 (got {val}).")

    n1 = a + b  # row 1 total
    n2 = c + d  # row 2 total
    n = a + c   # column 1 total (number of draws)
    N = a + b + c + d

    if N == 0:
        raise ValueError("All counts are zero.")

    # OR = (a*d) / (b*c)
    if b * c == 0:
        if a * d == 0:
            OR = float("nan")
        else:
            OR = float("inf")
    else:
        OR = (a * d) / (b * c)

    # Enumerate all possible tables with same marginals
    # k ranges from max(0, n - n2) to min(n1, n)
    k_min = max(0, n - n2)
    k_max = min(n1, n)
    all_probs = {k: _hypergeometric_pmf(k, n1, n2, n) for k in range(k_min, k_max + 1)}

    p_obs = all_probs.get(a, 0.0)

    if alternative == "two-sided":
        p_value = sum(p for p in all_probs.values() if p <= p_obs + 1e-10)
    elif alternative == "less":
        p_value = sum(p for k, p in all_probs.items() if k <= a)
    elif alternative == "greater":
        p_value = sum(p for k, p in all_probs.items() if k >= a)
    else:
        raise ValueError(f"alternative must be 'two-sided', 'less', or 'greater' (got {alternative}).")

    p_value = min(p_value, 1.0)  # floating-point guard

    return {
        "a": a, "b": b, "c": c, "d": d,
        "OR": OR,
        "p_value": p_value,
        "p_obs": p_obs,
        "alternative": alternative,
        "n_tables_enumerated": len(all_probs),
        "row1": n1, "row2": n2, "col1": a + c, "col2": b + d, "N": N,
    }


def print_fisher_exact(res: dict) -> None:
    print("=" * 60)
    print("  Fisher's Exact Test (2×2 table)")
    print("=" * 60)
    print("  Table:")
    print(f"    {'':12} | {'Group A':>8} | {'Group B':>8} | {'Total':>8}")
    print(f"    {'-'*12}-+-{'-'*8}-+-{'-'*8}-+-{'-'*8}")
    print(f"    {'Outcome +':12} | {res['a']:>8} | {res['b']:>8} | {res['row1']:>8}")
    print(f"    {'Outcome -':12} | {res['c']:>8} | {res['d']:>8} | {res['row2']:>8}")
    print(f"    {'Total':12} | {res['col1']:>8} | {res['col2']:>8} | {res['N']:>8}")
    print()
    OR = res["OR"]
    if math.isnan(OR):
        print("  Odds Ratio: undefined (0/0)")
    elif math.isinf(OR):
        print("  Odds Ratio: ∞  (zero in denominator b×c)")
    else:
        print(f"  Odds Ratio (OR) = (a×d) / (b×c)")
        print(f"                  = ({res['a']}×{res['d']}) / ({res['b']}×{res['c']})")
        ad = res["a"] * res["d"]
        bc = res["b"] * res["c"]
        print(f"                  = {ad} / {bc} = {OR:.4f}")
    print()
    print(f"  Alternative hypothesis : {res['alternative']}")
    print(f"  Tables enumerated      : {res['n_tables_enumerated']}")
    print(f"  P(observed table)      : {res['p_obs']:.6f}")
    print(f"  p-value                : {res['p_value']:.6f}")
    print()
    sig = res["p_value"] < 0.05
    print(f"  Result: {'SIGNIFICANT' if sig else 'NOT significant'} at α = 0.05")
    if sig:
        print("  Evidence for association between rows and columns.")
    else:
        print("  No significant association between rows and columns.")
    print()
    print("  Verification:")
    check_sum = sum(
        math.exp(_log_comb(res["row1"], k) + _log_comb(res["row2"], res["col1"] - k)
                 - _log_comb(res["N"], res["col1"]))
        for k in range(max(0, res["col1"] - res["row2"]), min(res["row1"], res["col1"]) + 1)
    )
    assert abs(check_sum - 1.0) < 1e-8, f"Hypergeometric probabilities do not sum to 1: {check_sum}"
    print(f"    Sum of all hypergeometric probabilities = {check_sum:.8f}  ✓")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Simple linear regression (OLS, closed-form)
# ---------------------------------------------------------------------------

def linear_regression(x: list[float], y: list[float]) -> dict:
    """
    Simple OLS linear regression: y = b0 + b1*x.

    Uses closed-form formulas:
        b1 = Σ(xi - x̄)(yi - ȳ) / Σ(xi - x̄)²
        b0 = ȳ - b1 * x̄

    Returns dict with slope, intercept, R², SE of slope, t-statistic, p-value,
    predicted values, and residuals.
    """
    n = len(x)
    if n != len(y):
        raise ValueError(f"x and y must have the same length ({len(x)} vs {len(y)}).")
    if n < 3:
        raise ValueError(f"Need at least 3 data points for regression (got {n}).")

    x_mean = sum(x) / n
    y_mean = sum(y) / n

    Sxx = sum((xi - x_mean) ** 2 for xi in x)
    Sxy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    Syy = sum((yi - y_mean) ** 2 for yi in y)

    if Sxx == 0:
        raise ValueError("All x values are identical — regression is undefined.")

    b1 = Sxy / Sxx
    b0 = y_mean - b1 * x_mean

    y_pred = [b0 + b1 * xi for xi in x]
    residuals = [yi - yp for yi, yp in zip(y, y_pred)]

    SSR = sum(r ** 2 for r in residuals)   # Residual sum of squares
    SST = Syy                               # Total sum of squares
    SSM = SST - SSR                         # Model sum of squares

    R2 = 1.0 - SSR / SST if SST > 0 else float("nan")
    R2_adj = 1.0 - (SSR / (n - 2)) / (SST / (n - 1)) if n > 2 and SST > 0 else float("nan")

    s2 = SSR / (n - 2)   # Mean squared error (unbiased)
    s = math.sqrt(s2)

    se_b1 = math.sqrt(s2 / Sxx)
    se_b0 = math.sqrt(s2 * (1.0 / n + x_mean ** 2 / Sxx))

    # t-statistics
    t_b1 = b1 / se_b1 if se_b1 > 0 else float("nan")
    t_b0 = b0 / se_b0 if se_b0 > 0 else float("nan")

    # p-values via t-distribution (df = n-2)
    # Use two-tailed survival function of t: 2 * P(T > |t|, df)
    # Approximated via regularized incomplete beta function: I(df/(df+t²), df/2, 0.5)
    def _t_pvalue(t_stat: float, df: int) -> float:
        if math.isnan(t_stat):
            return float("nan")
        t2 = t_stat ** 2
        x_beta = df / (df + t2)
        # I(x, a, b) with a=df/2, b=0.5 via regularized incomplete gamma
        # P(|T| > |t|) = I(df/(df+t²), df/2, 1/2) — use numerical approach
        # For the incomplete beta function we use the continued fraction expansion
        # Available as math.betainc in Python 3.12+, but for wider compatibility
        # we implement a basic version.
        return _incomplete_beta_regularized(x_beta, df / 2.0, 0.5)

    def _incomplete_beta_regularized(x: float, a: float, b: float,
                                     max_iter: int = 300, eps: float = 1e-12) -> float:
        """I_x(a, b) — regularized incomplete beta via continued fraction (Numerical Recipes)."""
        if x <= 0:
            return 0.0
        if x >= 1:
            return 1.0
        ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
        front = math.exp(a * math.log(x) + b * math.log(1 - x) - ln_beta)
        # Use symmetry: I_x(a,b) = 1 - I_{1-x}(b,a) when x > (a+1)/(a+b+2)
        if x > (a + 1.0) / (a + b + 2.0):
            return 1.0 - _incomplete_beta_regularized(1 - x, b, a, max_iter, eps)
        # Continued fraction
        fpmin = 1e-300
        qab = a + b
        qap = a + 1.0
        qam = a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        if abs(d) < fpmin:
            d = fpmin
        d = 1.0 / d
        h = d
        for m in range(1, max_iter + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < fpmin:
                d = fpmin
            c = 1.0 + aa / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < eps:
                break
        return front * h / a

    p_b1 = _t_pvalue(t_b1, n - 2)
    p_b0 = _t_pvalue(t_b0, n - 2)

    # Pearson r
    r = Sxy / math.sqrt(Sxx * Syy) if Sxx > 0 and Syy > 0 else float("nan")

    return {
        "n": n,
        "x_mean": x_mean,
        "y_mean": y_mean,
        "slope": b1,
        "intercept": b0,
        "se_slope": se_b1,
        "se_intercept": se_b0,
        "t_slope": t_b1,
        "t_intercept": t_b0,
        "p_slope": p_b1,
        "p_intercept": p_b0,
        "R2": R2,
        "R2_adj": R2_adj,
        "r": r,
        "SSR": SSR,
        "SST": SST,
        "SSM": SSM,
        "s": s,
        "y_pred": y_pred,
        "residuals": residuals,
        "Sxx": Sxx,
        "Sxy": Sxy,
    }


def print_regression(res: dict, x: list[float], y: list[float]) -> None:
    print("=" * 60)
    print("  Simple Linear Regression (OLS)")
    print("=" * 60)
    print(f"  n = {res['n']}  |  x̄ = {res['x_mean']:.4f}  |  ȳ = {res['y_mean']:.4f}")
    print()
    print("  Data:")
    print(f"  {'i':>3}  {'x':>8}  {'y':>8}  {'ŷ':>8}  {'residual':>10}")
    print(f"  {'-'*3}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*10}")
    for i, (xi, yi, yp, ri) in enumerate(zip(x, y, res["y_pred"], res["residuals"]), 1):
        print(f"  {i:>3}  {xi:>8.4f}  {yi:>8.4f}  {yp:>8.4f}  {ri:>10.4f}")
    print()
    print("  Coefficients:")
    print(f"  {'Parameter':>12}  {'Estimate':>10}  {'SE':>8}  {'t':>8}  {'p-value':>10}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*8}  {'-'*8}  {'-'*10}")
    b0_sig = "*" if res["p_intercept"] < 0.05 else ""
    b1_sig = "*" if res["p_slope"] < 0.05 else ""
    print(
        f"  {'Intercept (b0)':>12}  {res['intercept']:>10.4f}  "
        f"{res['se_intercept']:>8.4f}  {res['t_intercept']:>8.4f}  "
        f"{res['p_intercept']:>10.6f}{b0_sig}"
    )
    print(
        f"  {'Slope (b1)':>12}  {res['slope']:>10.4f}  "
        f"{res['se_slope']:>8.4f}  {res['t_slope']:>8.4f}  "
        f"{res['p_slope']:>10.6f}{b1_sig}"
    )
    print("  (* p < 0.05)")
    print()
    print("  Model Fit:")
    print(f"    R²              = {res['R2']:.6f}")
    print(f"    Adjusted R²     = {res['R2_adj']:.6f}")
    print(f"    Pearson r       = {res['r']:.6f}")
    print(f"    Residual SE (s) = {res['s']:.6f}")
    print(f"    SSM (model)     = {res['SSM']:.6f}")
    print(f"    SSR (residual)  = {res['SSR']:.6f}")
    print(f"    SST (total)     = {res['SST']:.6f}")
    print()
    print(f"  Equation: ŷ = {res['intercept']:.4f} + {res['slope']:.4f} × x")
    print()
    print("  Interpretation:")
    print(f"    For each unit increase in x, y changes by {res['slope']:.4f} units.")
    print(f"    The model explains {res['R2'] * 100:.2f}% of the variance in y.")
    if res["p_slope"] < 0.05:
        print(f"    The slope is statistically significant (p = {res['p_slope']:.4f}).")
    else:
        print(f"    The slope is NOT significant (p = {res['p_slope']:.4f}).")
    print()
    print("  Verification:")
    check_b1 = res["Sxy"] / res["Sxx"]
    check_b0 = res["y_mean"] - check_b1 * res["x_mean"]
    assert abs(check_b1 - res["slope"]) < 1e-8, "Slope mismatch"
    assert abs(check_b0 - res["intercept"]) < 1e-8, "Intercept mismatch"
    print(f"    Sxy/Sxx = {check_b1:.6f}  ✓  (slope)")
    print(f"    ȳ - b1*x̄ = {check_b0:.6f}  ✓  (intercept)")
    check_R2 = 1.0 - res["SSR"] / res["SST"]
    assert abs(check_R2 - res["R2"]) < 1e-8, "R2 mismatch"
    print(f"    1 - SSR/SST = {check_R2:.6f}  ✓  (R²)")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_floats(s: str) -> list[float]:
    """Parse a comma-separated string of floats."""
    return [float(v.strip()) for v in s.split(",")]


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Statistical tests (pure stdlib): chi-square, Fisher's exact, linear regression.",
        epilog=(
            "Examples:\n"
            "  python stat_tests.py --type chi_square --observed 100,50,25 --expected 87.5,50,37.5\n"
            "  python stat_tests.py --type fisher_exact --a 10 --b 5 --c 3 --d 20\n"
            "  python stat_tests.py --type regression --x \"1,2,3,4,5\" --y \"2.1,4.0,5.9,8.1,10.0\"\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["chi_square", "fisher_exact", "regression"],
        help="Test type.",
    )
    # chi_square
    p.add_argument("--observed", type=str, help="Comma-separated observed counts (chi_square).")
    p.add_argument("--expected", type=str, help="Comma-separated expected counts (chi_square).")
    # fisher_exact
    p.add_argument("--a", type=int, help="Top-left cell (fisher_exact).")
    p.add_argument("--b", type=int, help="Top-right cell (fisher_exact).")
    p.add_argument("--c", type=int, help="Bottom-left cell (fisher_exact).")
    p.add_argument("--d", type=int, help="Bottom-right cell (fisher_exact).")
    p.add_argument(
        "--alternative",
        choices=["two-sided", "less", "greater"],
        default="two-sided",
        help="Alternative hypothesis for Fisher's exact (default: two-sided).",
    )
    # regression
    p.add_argument("--x", type=str, help="Comma-separated x values (regression).")
    p.add_argument("--y", type=str, help="Comma-separated y values (regression).")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    try:
        if args.type == "chi_square":
            if args.observed is None or args.expected is None:
                parser.error("--type chi_square requires --observed and --expected.")
            obs = _parse_floats(args.observed)
            exp = _parse_floats(args.expected)
            res = chi_square_gof(obs, exp)
            print_chi_square(res)

        elif args.type == "fisher_exact":
            for flag in ("--a", "--b", "--c", "--d"):
                attr = flag.lstrip("-")
                if getattr(args, attr) is None:
                    parser.error(f"--type fisher_exact requires {flag}.")
            res = fisher_exact(args.a, args.b, args.c, args.d, args.alternative)
            print_fisher_exact(res)

        elif args.type == "regression":
            if args.x is None or args.y is None:
                parser.error("--type regression requires --x and --y.")
            x_vals = _parse_floats(args.x)
            y_vals = _parse_floats(args.y)
            res = linear_regression(x_vals, y_vals)
            print_regression(res, x_vals, y_vals)

    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
