"""
Herd immunity threshold calculator.

Computes the minimum vaccination coverage (Vc) required to achieve herd immunity,
accounting for vaccine efficacy (VE).

Formula:
    Vc = (1 - 1/R0) / VE

Where:
    R0  = basic reproduction number (average infections caused by one case in fully susceptible pop)
    VE  = vaccine efficacy (fraction of vaccinated individuals who are protected, 0–1)
    Vc  = minimum fraction of the population that must be vaccinated

Usage:
    python herd_immunity.py --R0 4.2 --VE 0.94
    python herd_immunity.py --R0 14 --VE 0.97        # measles
    python herd_immunity.py --R0 2.5 --VE 0.85       # seasonal flu
"""

import argparse
import sys


def herd_immunity_threshold(R0: float) -> float:
    """Herd immunity threshold with perfect (100%) vaccine: Hc = 1 - 1/R0."""
    if R0 <= 1:
        raise ValueError(f"R0 must be > 1 for an epidemic to occur (got {R0}).")
    return 1.0 - 1.0 / R0


def vaccination_coverage_needed(R0: float, VE: float) -> float:
    """
    Minimum vaccination coverage Vc = (1 - 1/R0) / VE.

    This is the fraction of the total population that must be vaccinated so that
    the effective reproduction number Re drops to 1 (herd immunity).
    """
    if not (0 < VE <= 1):
        raise ValueError(f"VE must be between 0 (exclusive) and 1 (got {VE}).")
    Hc = herd_immunity_threshold(R0)
    return Hc / VE


def effective_R(R0: float, VE: float, coverage: float) -> float:
    """
    Effective reproduction number given vaccination coverage and efficacy.
    Re = R0 * (1 - VE * coverage)
    """
    return R0 * (1.0 - VE * coverage)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate herd immunity vaccination coverage requirement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--R0",
        type=float,
        required=True,
        help="Basic reproduction number (must be > 1).",
    )
    parser.add_argument(
        "--VE",
        type=float,
        required=True,
        help="Vaccine efficacy as a fraction, e.g. 0.94 for 94%%.",
    )
    parser.add_argument(
        "--check_coverage",
        type=float,
        default=None,
        metavar="FRAC",
        help="Optional: evaluate Re at this vaccination coverage fraction.",
    )
    args = parser.parse_args()

    R0 = args.R0
    VE = args.VE

    # Validate inputs
    if R0 <= 1:
        print(f"Error: R0 must be > 1 (got {R0}). With R0 ≤ 1 the pathogen cannot sustain an epidemic.")
        sys.exit(1)
    if not (0 < VE <= 1):
        print(f"Error: VE must be between 0 (exclusive) and 1 (got {VE}).")
        sys.exit(1)

    Hc = herd_immunity_threshold(R0)
    Vc = vaccination_coverage_needed(R0, VE)

    print("=" * 55)
    print("  Herd Immunity Threshold Calculator")
    print("=" * 55)
    print(f"  Input R0          : {R0}")
    print(f"  Input VE          : {VE:.1%}")
    print("-" * 55)
    print(f"  Herd immunity threshold (perfect vaccine)")
    print(f"    Hc = 1 - 1/R0  = {Hc:.4f}  ({Hc:.1%})")
    print()
    print(f"  Required vaccination coverage (VE-adjusted)")
    print(f"    Vc = Hc / VE   = {Vc:.4f}  ({Vc:.1%})")

    if Vc > 1.0:
        print()
        print(f"  WARNING: Vc > 100% — herd immunity is mathematically")
        print(f"  unachievable at this VE level. A more efficacious vaccine")
        print(f"  or additional non-pharmaceutical interventions are required.")
    else:
        print()
        # Show Re at exact Vc coverage
        Re_at_Vc = effective_R(R0, VE, Vc)
        print(f"  Verification: Re at Vc coverage = {Re_at_Vc:.4f} (should be ≈ 1.00)")

    # Optional: evaluate Re at a user-supplied coverage
    if args.check_coverage is not None:
        cov = args.check_coverage
        if not (0 <= cov <= 1):
            print(f"\n  Error: --check_coverage must be 0–1 (got {cov}).")
        else:
            Re_check = effective_R(R0, VE, cov)
            status = "epidemic suppressed" if Re_check < 1 else "epidemic can grow"
            print()
            print(f"  At {cov:.1%} coverage → Re = {Re_check:.4f}  ({status})")

    print("=" * 55)


if __name__ == "__main__":
    main()
