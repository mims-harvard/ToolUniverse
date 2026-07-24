"""
Radioactive decay calculator for nuclear medicine applications.

Three modes of operation:

  Forward       — how much activity remains after a given time?
  Reverse       — how long until activity drops to a target level?
  Parent-daughter — Bateman equation for parent→daughter chains with
                    two measurements to solve for elapsed time.

Formula (single nuclide):
    A(t) = A0 * (0.5 ^ (t / t_half))
    t    = t_half * log2(A0 / A_target)     [reverse]

Formula (parent-daughter):
    A_daughter(t) = A_parent0 * [lD/(lD-lP)] * [exp(-lP*t) - exp(-lD*t)]
    where lP, lD = ln(2)/t_half for parent and daughter

Supported units: mCi, Bq  (default: mCi)

Usage:
    python radioactive_decay.py --A0 8 --half_life 67.3 --time 72
    python radioactive_decay.py --A0 8 --half_life 67.3 --target 5
    python radioactive_decay.py --A0 370 --half_life 6.0 --time 24 --unit Bq

    # Parent-daughter: solve for time from two activity measurements
    python radioactive_decay.py --parent_daughter \\
        --half_life_parent 306.05 --half_life_daughter 40.27 \\
        --A1 1.4 --A2 2.1 --delta_t 336 --counted daughter
"""

import argparse
import math
import sys

# Conversion factor: 1 mCi = 37 MBq = 3.7e7 Bq
MCI_TO_BQ = 3.7e7


def decay_forward(A0: float, half_life: float, time: float) -> float:
    """Activity remaining after `time` units: A(t) = A0 * 2^(-t/t_half)."""
    return A0 * math.pow(0.5, time / half_life)


def decay_reverse(A0: float, half_life: float, target: float) -> float:
    """Time to reach `target` activity: t = t_half * log2(A0 / target)."""
    if target <= 0:
        raise ValueError("Target activity must be > 0.")
    if target >= A0:
        raise ValueError("Target activity must be less than initial activity A0.")
    return half_life * math.log2(A0 / target)


def fraction_remaining(A0: float, A_final: float) -> float:
    return A_final / A0


def num_half_lives(time: float, half_life: float) -> float:
    return time / half_life


# ---------------------------------------------------------------------------
# Parent-daughter (Bateman equation)
# ---------------------------------------------------------------------------


def daughter_activity(A_parent0: float, t: float,
                      half_life_parent: float, half_life_daughter: float) -> float:
    """
    Daughter activity at time t via Bateman equation.
    Assumes daughter activity = 0 at t = 0 (freshly separated).
    A_d(t) = A_p0 * [lD/(lD-lP)] * [exp(-lP*t) - exp(-lD*t)]
    """
    lP = math.log(2) / half_life_parent
    lD = math.log(2) / half_life_daughter
    ratio = lD / (lD - lP)
    return A_parent0 * ratio * (math.exp(-lP * t) - math.exp(-lD * t))


def parent_plus_daughter(A_parent0: float, t: float,
                         half_life_parent: float, half_life_daughter: float) -> tuple:
    """Parent and daughter activities at time t. Returns (A_parent, A_daughter)."""
    lP = math.log(2) / half_life_parent
    A_p = A_parent0 * math.exp(-lP * t)
    A_d = daughter_activity(A_parent0, t, half_life_parent, half_life_daughter)
    return A_p, A_d


def solve_parent_daughter_time(A1: float, A2: float, delta_t: float,
                               half_life_parent: float, half_life_daughter: float,
                               counted: str = "daughter") -> dict:
    """
    Given two measurements (A1 at time t1, A2 at time t1+delta_t),
    find t1 (time since daughter was removed / system was separated).

    counted: which nuclides contribute to the measured activity.
        "daughter"  — only the daughter is detected (e.g., Cherenkov counting
                       detects only the high-energy daughter)
        "both"      — both parent and daughter are detected
        "parent"    — only the parent is detected (trivial case)

    Returns dict with t1, A_parent0, and verification values.
    """
    lP = math.log(2) / half_life_parent
    lD = math.log(2) / half_life_daughter
    ratio = lD / (lD - lP)

    def measured_activity(A_p0, t):
        A_p = A_p0 * math.exp(-lP * t)
        A_d = A_p0 * ratio * (math.exp(-lP * t) - math.exp(-lD * t))
        if counted == "daughter":
            return A_d
        elif counted == "both":
            return A_p + A_d
        else:  # parent only
            return A_p

    def activity_ratio(t1):
        """Ratio A2/A1 as a function of t1 (A_p0 cancels)."""
        m1 = measured_activity(1.0, t1)
        m2 = measured_activity(1.0, t1 + delta_t)
        if m1 < 1e-30:
            return float("inf")
        return m2 / m1

    target_ratio = A2 / A1

    # Binary search for t1
    # The ratio function varies depending on t1. Search a wide range.
    t_lo, t_hi = 1e-6, half_life_parent * 50
    best_t1 = None
    best_err = float("inf")

    # Scan to find bracket
    n_scan = 10000
    prev_r = activity_ratio(t_lo)
    for i in range(1, n_scan + 1):
        t_test = t_lo + (t_hi - t_lo) * i / n_scan
        r = activity_ratio(t_test)
        if math.isnan(r) or math.isinf(r):
            prev_r = r
            continue
        err = abs(r - target_ratio)
        if err < best_err:
            best_err = err
            best_t1 = t_test
        # Check for sign change (root crossing)
        if not (math.isnan(prev_r) or math.isinf(prev_r)):
            if (prev_r - target_ratio) * (r - target_ratio) < 0:
                # Bisection refinement
                lo = t_lo + (t_hi - t_lo) * (i - 1) / n_scan
                hi = t_test
                for _ in range(100):
                    mid = (lo + hi) / 2
                    rm = activity_ratio(mid)
                    if (rm - target_ratio) * (activity_ratio(lo) - target_ratio) < 0:
                        hi = mid
                    else:
                        lo = mid
                best_t1 = (lo + hi) / 2
                best_err = abs(activity_ratio(best_t1) - target_ratio)
                break
        prev_r = r

    if best_t1 is None or best_err > 0.01:
        raise ValueError(
            f"Could not find t1 where A2/A1 = {target_ratio:.4f}. "
            f"Best error: {best_err:.6f} at t1 = {best_t1}."
        )

    t1 = best_t1
    # Recover A_parent0 from A1
    m1_unit = measured_activity(1.0, t1)
    A_p0 = A1 / m1_unit if m1_unit > 1e-30 else float("nan")

    # Verification
    A1_check = measured_activity(A_p0, t1)
    A2_check = measured_activity(A_p0, t1 + delta_t)

    return {
        "t1": t1,
        "A_parent0": A_p0,
        "A1_check": A1_check,
        "A2_check": A2_check,
        "ratio_target": target_ratio,
        "ratio_actual": A2_check / A1_check if A1_check > 0 else float("nan"),
        "half_life_parent": half_life_parent,
        "half_life_daughter": half_life_daughter,
        "counted": counted,
        "delta_t": delta_t,
    }


def print_parent_daughter(res: dict) -> None:
    print("=" * 62)
    print("  Parent-Daughter Decay Analysis (Bateman Equation)")
    print("=" * 62)
    print(f"  Parent half-life   : {res['half_life_parent']} h")
    print(f"  Daughter half-life : {res['half_life_daughter']} h")
    print(f"  Counted species    : {res['counted']}")
    print(f"  Time between measurements (delta_t): {res['delta_t']} h")
    t1 = res["t1"]
    print()
    print(f"  Solved: t1 = {t1:.2f} h")
    if t1 >= 24:
        d = int(t1 // 24)
        h = t1 - d * 24
        print(f"         = {d} d {h:.1f} h")
    print()
    print(f"  Derived initial parent activity: {res['A_parent0']:.4f}")
    print()
    print("  Verification:")
    print(f"    A1 measured: target vs computed = {res['ratio_target'] * res['A2_check'] / res['ratio_actual']:.4f} vs {res['A1_check']:.4f}")
    print(f"    A2 measured: target vs computed = {res['ratio_target'] * res['A1_check']:.4f} vs {res['A2_check']:.4f}")
    print(f"    Ratio: target {res['ratio_target']:.4f} vs actual {res['ratio_actual']:.4f}")
    print("=" * 62)


def main():
    parser = argparse.ArgumentParser(
        description="Radioactive decay: forward (time->activity), reverse (activity->time), or parent-daughter.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # --- Parent-daughter mode flag ---
    parser.add_argument(
        "--parent_daughter",
        action="store_true",
        help="Enable parent-daughter mode (Bateman equation). Requires --half_life_parent, "
             "--half_life_daughter, --A1, --A2, --delta_t.",
    )
    parser.add_argument("--half_life_parent", type=float, help="Parent half-life in hours (parent-daughter mode).")
    parser.add_argument("--half_life_daughter", type=float, help="Daughter half-life in hours (parent-daughter mode).")
    parser.add_argument("--A1", type=float, help="First activity measurement (parent-daughter mode).")
    parser.add_argument("--A2", type=float, help="Second activity measurement (parent-daughter mode).")
    parser.add_argument("--delta_t", type=float, help="Time between measurements in hours (parent-daughter mode).")
    parser.add_argument(
        "--counted",
        choices=["daughter", "both", "parent"],
        default="daughter",
        help="Which species the detector counts (parent-daughter mode, default: daughter).",
    )

    # --- Single-nuclide mode ---
    parser.add_argument("--A0", type=float, help="Initial activity (single-nuclide mode).")
    parser.add_argument("--half_life", type=float, help="Physical half-life in hours (single-nuclide mode).")
    parser.add_argument("--time", type=float, help="[Forward] Elapsed time in hours.")
    parser.add_argument("--target", type=float, help="[Reverse] Target activity to reach.")
    parser.add_argument(
        "--unit",
        choices=["mCi", "Bq"],
        default="mCi",
        help="Activity unit (default: mCi). Affects display only.",
    )
    args = parser.parse_args()

    # ---- Parent-daughter mode ----
    if args.parent_daughter:
        for flag, attr in [("--half_life_parent", "half_life_parent"),
                           ("--half_life_daughter", "half_life_daughter"),
                           ("--A1", "A1"), ("--A2", "A2"), ("--delta_t", "delta_t")]:
            if getattr(args, attr) is None:
                parser.error(f"--parent_daughter mode requires {flag}.")
        try:
            res = solve_parent_daughter_time(
                args.A1, args.A2, args.delta_t,
                args.half_life_parent, args.half_life_daughter,
                counted=args.counted,
            )
            print_parent_daughter(res)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    # ---- Single-nuclide mode ----
    if args.A0 is None:
        parser.error("--A0 is required (or use --parent_daughter mode).")
    if args.half_life is None:
        parser.error("--half_life is required.")
    if args.time is None and args.target is None:
        parser.error("Provide --time (forward) or --target (reverse).")
    if args.time is not None and args.target is not None:
        parser.error("--time and --target are mutually exclusive.")

    A0 = args.A0
    t_half = args.half_life
    unit = args.unit

    if A0 <= 0:
        print(f"Error: A0 must be positive (got {A0}).")
        sys.exit(1)
    if t_half <= 0:
        print(f"Error: half_life must be positive (got {t_half}).")
        sys.exit(1)

    print("=" * 58)
    print("  Radioactive Decay Calculator")
    print("=" * 58)
    print(f"  Initial activity (A0) : {A0} {unit}")
    print(f"  Physical half-life    : {t_half} h")

    if args.time is not None:
        # ---- Forward mode ----
        t = args.time
        if t < 0:
            print("Error: time must be >= 0.")
            sys.exit(1)

        A_t = decay_forward(A0, t_half, t)
        n_halves = num_half_lives(t, t_half)
        frac = fraction_remaining(A0, A_t)

        print(f"  Elapsed time          : {t} h")
        print("-" * 58)
        print(f"  Number of half-lives  : {n_halves:.4f}")
        print(f"  Fraction remaining    : {frac:.6f}  ({frac * 100:.4f}%)")
        print(f"  Remaining activity    : {A_t:.6f} {unit}")

        # Also show in alternate unit
        if unit == "mCi":
            A_t_bq = A_t * MCI_TO_BQ
            print(f"  (in Bq)               : {A_t_bq:.4e} Bq  = {A_t_bq / 1e6:.4f} MBq")
        else:
            A_t_mci = A_t / MCI_TO_BQ
            print(f"  (in mCi)              : {A_t_mci:.6f} mCi")

        # Verification: reconstruct A0
        A0_check = A_t / frac
        print()
        print(f"  Verification: A_t / fraction = {A0_check:.6f} {unit}  (should equal A0 = {A0})")

    else:
        # ---- Reverse mode ----
        target = args.target
        try:
            t_reach = decay_reverse(A0, t_half, target)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

        frac = fraction_remaining(A0, target)
        n_halves = num_half_lives(t_reach, t_half)
        A_verify = decay_forward(A0, t_half, t_reach)

        print(f"  Target activity       : {target} {unit}")
        print("-" * 58)
        print(f"  Fraction to reach     : {frac:.6f}  ({frac * 100:.4f}%)")
        print(f"  Number of half-lives  : {n_halves:.4f}")
        print(f"  Time to target        : {t_reach:.4f} h")

        # Helpful breakdown in days + hours if > 24 h
        if t_reach >= 24:
            days = int(t_reach // 24)
            hours_rem = t_reach - days * 24
            print(f"  (= {days} d {hours_rem:.2f} h)")

        # Verification
        print()
        print(f"  Verification: A(t={t_reach:.4f} h) = {A_verify:.6f} {unit}  (should equal target = {target})")

    print("=" * 58)


if __name__ == "__main__":
    main()
