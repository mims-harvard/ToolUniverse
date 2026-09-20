#!/usr/bin/env python3
"""
Sample-size / power calculator for clinical trial protocols.

Implements three standard closed-form approximations used throughout
clinical trial statistical sections:

  1. two-proportion  -- comparing a binary response/event rate between two arms
  2. two-mean         -- comparing a continuous outcome between two arms
  3. survival         -- comparing time-to-event outcomes via the Schoenfeld
                         formula for the number of required events, converted
                         to total enrollment via an assumed event probability

All formulas are textbook closed-form approximations (not simulated), cited
in the docstring of each function. Requires scipy (already a ToolUniverse
dependency) for the normal quantile function.

Usage:
    python3 sample_size_calculator.py two-proportion --p1 0.3 --p2 0.5 --alpha 0.05 --power 0.8
    python3 sample_size_calculator.py two-mean --mean-diff 0.5 --sd 1.0 --alpha 0.05 --power 0.8
    python3 sample_size_calculator.py survival --hr 0.7 --event-rate 0.6 --alpha 0.05 --power 0.8
    python3 sample_size_calculator.py --self-test
"""

import argparse
import math
import sys

from scipy.stats import norm


def z(alpha_or_beta_tail_prob):
    """Upper-tail standard normal quantile, e.g. z(0.025) = 1.959964 (z_alpha/2 for alpha=0.05 two-sided)."""
    return norm.ppf(1 - alpha_or_beta_tail_prob)


def two_proportion_n(p1, p2, alpha=0.05, power=0.8, two_sided=True):
    """
    Sample size per arm to compare two independent proportions.

    Uses the standard formula with pooled variance under the null and
    unpooled variance under the alternative (Fleiss, Levin & Paik,
    "Statistical Methods for Rates and Proportions", 3rd ed., Ch. 3;
    also the formula used in FDA statistical review templates):

        n = [ z_(a/2) * sqrt(2*pbar*(1-pbar)) + z_b * sqrt(p1*(1-p1) + p2*(1-p2)) ]^2
            / (p1 - p2)^2

    where pbar = (p1 + p2) / 2.
    """
    alpha_tail = alpha / 2 if two_sided else alpha
    za = z(alpha_tail)
    zb = z(1 - power)
    pbar = (p1 + p2) / 2.0
    term_null = math.sqrt(2 * pbar * (1 - pbar))
    term_alt = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    numerator = (za * term_null + zb * term_alt) ** 2
    denominator = (p1 - p2) ** 2
    n = numerator / denominator
    return math.ceil(n)


def two_mean_n(mean_diff, sd, alpha=0.05, power=0.8, two_sided=True):
    """
    Sample size per arm to compare two independent means with equal variance.

    Standard formula (Chow, Shao & Wang, "Sample Size Calculations in
    Clinical Research", 2nd ed., Ch. 3):

        n = 2 * (z_(a/2) + z_b)^2 * sigma^2 / delta^2

    where delta = mean_diff (clinically meaningful difference) and
    sigma = common standard deviation.
    """
    alpha_tail = alpha / 2 if two_sided else alpha
    za = z(alpha_tail)
    zb = z(1 - power)
    n = 2 * (za + zb) ** 2 * (sd ** 2) / (mean_diff ** 2)
    return math.ceil(n)


def survival_events(hazard_ratio, alpha=0.05, power=0.8, allocation_ratio=1.0, two_sided=True):
    """
    Number of events required to detect a given hazard ratio (Schoenfeld, 1983,
    "Sample-size formula for the proportional-hazards regression model",
    Biometrics 39:499-503). For 1:1 allocation:

        d = 4 * (z_(a/2) + z_b)^2 / (ln(HR))^2

    For unequal allocation ratio r = n_treatment / n_control, the general form is:

        d = (1 + r)^2 / r * (z_(a/2) + z_b)^2 / (ln(HR))^2
    """
    alpha_tail = alpha / 2 if two_sided else alpha
    za = z(alpha_tail)
    zb = z(1 - power)
    r = allocation_ratio
    d = ((1 + r) ** 2 / r) * (za + zb) ** 2 / (math.log(hazard_ratio) ** 2)
    return math.ceil(d)


def survival_total_n(hazard_ratio, event_rate, alpha=0.05, power=0.8, allocation_ratio=1.0, two_sided=True):
    """
    Total enrollment required, given the number of events needed (Schoenfeld)
    and the expected probability that a given enrolled subject experiences the
    event during the study (event_rate, e.g. estimated from historical/precedent
    trials -- must be looked up, never guessed from memory).

        n_total = d / event_rate
    """
    d = survival_events(hazard_ratio, alpha=alpha, power=power,
                         allocation_ratio=allocation_ratio, two_sided=two_sided)
    return d, math.ceil(d / event_rate)


def _print_two_proportion(args):
    n = two_proportion_n(args.p1, args.p2, alpha=args.alpha, power=args.power)
    print("Two-proportion comparison")
    print(f"  p1 = {args.p1}, p2 = {args.p2}, alpha = {args.alpha} (two-sided), power = {args.power}")
    print("  Formula: n = [z_(a/2)*sqrt(2*pbar*(1-pbar)) + z_b*sqrt(p1(1-p1)+p2(1-p2))]^2 / (p1-p2)^2")
    print(f"  Required n per arm: {n}")
    print(f"  Total enrollment (2 arms): {2 * n}")


def _print_two_mean(args):
    n = two_mean_n(args.mean_diff, args.sd, alpha=args.alpha, power=args.power)
    print("Two-mean comparison")
    print(f"  mean_diff = {args.mean_diff}, sd = {args.sd}, alpha = {args.alpha} (two-sided), power = {args.power}")
    print("  Formula: n = 2*(z_(a/2)+z_b)^2 * sigma^2 / delta^2")
    print(f"  Required n per arm: {n}")
    print(f"  Total enrollment (2 arms): {2 * n}")


def _print_survival(args):
    d, n_total = survival_total_n(args.hr, args.event_rate, alpha=args.alpha,
                                   power=args.power, allocation_ratio=args.allocation_ratio)
    print("Survival / time-to-event comparison (Schoenfeld)")
    print(f"  hazard_ratio = {args.hr}, event_rate = {args.event_rate}, "
          f"alpha = {args.alpha} (two-sided), power = {args.power}, "
          f"allocation_ratio = {args.allocation_ratio}")
    print("  Formula: d = (1+r)^2/r * (z_(a/2)+z_b)^2 / ln(HR)^2 ; n_total = d / event_rate")
    print(f"  Required number of events: {d}")
    print(f"  Required total enrollment: {n_total}")


def run_self_test():
    """
    Regression-checks the three formulas against hand-derived reference values.
    Each reference value is computed independently in this function (not by
    calling the functions under test) using the same published formula, worked
    through with the documented z-quantiles, so a coding error (wrong sign,
    wrong pooling, wrong exponent) will cause a mismatch.
    """
    failures = []

    # --- Two-proportion: p1=0.3, p2=0.5, alpha=0.05 (two-sided), power=0.8 ---
    # z_0.025 = 1.959964, z_0.20 = 0.841621
    za, zb = 1.959964, 0.841621
    pbar = 0.4
    expected = math.ceil(
        (za * math.sqrt(2 * pbar * (1 - pbar)) + zb * math.sqrt(0.3 * 0.7 + 0.5 * 0.5)) ** 2
        / (0.3 - 0.5) ** 2
    )
    got = two_proportion_n(0.3, 0.5, alpha=0.05, power=0.8)
    status = "PASS" if got == expected else "FAIL"
    if got != expected:
        failures.append(("two-proportion", expected, got))
    print(f"[{status}] two-proportion(p1=0.3, p2=0.5, alpha=0.05, power=0.8): "
          f"expected n={expected} per arm, got n={got} per arm "
          "(reference: Fleiss/Levin & Paik pooled-null formula)")

    # --- Two-mean: Cohen's medium effect size d=0.5 (mean_diff=0.5, sd=1.0) ---
    # This is the standard textbook "medium effect size" example (Cohen, 1988);
    # commonly cited result is ~64 per group (some texts use a t-based
    # correction that rounds to 64; the plain z-based formula below gives 63).
    expected = math.ceil(2 * (za + zb) ** 2 * (1.0 ** 2) / (0.5 ** 2))
    got = two_mean_n(0.5, 1.0, alpha=0.05, power=0.8)
    status = "PASS" if got == expected else "FAIL"
    if got != expected:
        failures.append(("two-mean", expected, got))
    print(f"[{status}] two-mean(mean_diff=0.5, sd=1.0, alpha=0.05, power=0.8): "
          f"expected n={expected} per arm, got n={got} per arm "
          "(reference: Chow/Shao/Wang formula; z-based value is 63, "
          "commonly rounded to 64 in t-based texts for Cohen's d=0.5)")

    # --- Survival: HR=0.7, alpha=0.05, power=0.8, 1:1 allocation ---
    # d = 4*(za+zb)^2 / ln(0.7)^2  -- standard Schoenfeld worked example
    # widely cited in oncology trial design texts as ~247 events for HR=0.7.
    ln_hr = math.log(0.7)
    expected_d = math.ceil(4 * (za + zb) ** 2 / (ln_hr ** 2))
    got_d = survival_events(0.7, alpha=0.05, power=0.8, allocation_ratio=1.0)
    status = "PASS" if got_d == expected_d else "FAIL"
    if got_d != expected_d:
        failures.append(("survival-events", expected_d, got_d))
    print(f"[{status}] survival-events(hr=0.7, alpha=0.05, power=0.8, 1:1 allocation): "
          f"expected d={expected_d} events, got d={got_d} events "
          "(reference: Schoenfeld 1983 4*(z_a/2+z_b)^2/ln(HR)^2 worked example)")

    print()
    if failures:
        print(f"SELF-TEST FAILED: {len(failures)} mismatch(es): {failures}")
        return 1
    print("SELF-TEST PASSED: all three formulas match their hand-derived reference values.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true", help="Run regression self-test and exit")
    sub = parser.add_subparsers(dest="mode")

    p_prop = sub.add_parser("two-proportion", help="Compare two binary response/event rates")
    p_prop.add_argument("--p1", type=float, required=True, help="Response rate in arm 1 (0-1)")
    p_prop.add_argument("--p2", type=float, required=True, help="Response rate in arm 2 (0-1)")
    p_prop.add_argument("--alpha", type=float, default=0.05)
    p_prop.add_argument("--power", type=float, default=0.8)

    p_mean = sub.add_parser("two-mean", help="Compare two continuous-outcome means")
    p_mean.add_argument("--mean-diff", type=float, required=True, help="Clinically meaningful mean difference")
    p_mean.add_argument("--sd", type=float, required=True, help="Common (pooled) standard deviation")
    p_mean.add_argument("--alpha", type=float, default=0.05)
    p_mean.add_argument("--power", type=float, default=0.8)

    p_surv = sub.add_parser("survival", help="Compare two survival/time-to-event curves")
    p_surv.add_argument("--hr", type=float, required=True, help="Target hazard ratio (treatment vs control)")
    p_surv.add_argument("--event-rate", type=float, required=True,
                         help="Expected probability an enrolled subject has the event during the study "
                              "(look this up from precedent trials -- do not guess)")
    p_surv.add_argument("--alpha", type=float, default=0.05)
    p_surv.add_argument("--power", type=float, default=0.8)
    p_surv.add_argument("--allocation-ratio", type=float, default=1.0,
                         help="n_treatment / n_control (default 1.0 = equal allocation)")

    args = parser.parse_args()

    if args.self_test:
        sys.exit(run_self_test())

    if args.mode == "two-proportion":
        _print_two_proportion(args)
    elif args.mode == "two-mean":
        _print_two_mean(args)
    elif args.mode == "survival":
        _print_survival(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
