#!/usr/bin/env python3
"""Equilibrium solver for solubility, complex formation, and common-ion problems.

Handles:
  - ksp_simple:  MaXb(s) <-> aM + bX, solve for solubility s
  - ksp_kf:      Dissolution + complex formation (e.g., Al(OH)3 in excess OH-)
  - common_ion:  Ksp with an additional common-ion concentration

Examples:
  python equilibrium_solver.py --type ksp_simple --ksp 5.3e-27 --stoich 1:3
  python equilibrium_solver.py --type ksp_kf --ksp 5.3e-27 --kf 1.1e33 --stoich 1:3
  python equilibrium_solver.py --type common_ion --ksp 1.8e-10 --stoich 1:1 --common-ion 0.1
"""

import argparse
import math
import sys


def solve_ksp_simple(ksp: float, a: int, b: int) -> dict:
    """Solve MaXb(s) <-> aM^n+ + bX^m- with Ksp = (a*s)^a * (b*s)^b.

    Ksp = a^a * b^b * s^(a+b)  =>  s = (Ksp / (a^a * b^b))^(1/(a+b))
    """
    coeff = (a**a) * (b**b)
    n = a + b
    s = (ksp / coeff) ** (1.0 / n)
    return {
        "solubility_mol_per_L": s,
        "cation_conc": a * s,
        "anion_conc": b * s,
        "expression": f"Ksp = ({a}s)^{a} * ({b}s)^{b} = {coeff} * s^{n}",
        "Ksp": ksp,
    }


def solve_ksp_kf(ksp: float, kf: float, a: int, b: int) -> dict:
    """Solve dissolution + complex-formation equilibrium.

    Example — Al(OH)3 (a=1, b=3):
      Al(OH)3(s) <-> Al3+ + 3 OH-          Ksp
      Al3+ + 4 OH- <-> Al(OH)4-             Kf
      -----------------------------------------------
      Overall: Al(OH)3(s) + OH- <-> Al(OH)4-   K = Ksp * Kf

    For the general case MX_b:
      MX_b(s) <-> M^b+ + b X^-              Ksp
      M^b+ + (b+1) X^- <-> MX_(b+1)^-      Kf
      Overall: MX_b(s) + X^- <-> MX_(b+1)^-  K_overall = Ksp * Kf

    In pure water the only source of OH- is from the dissolution itself.
    Let s = solubility of Al(OH)3.

    Species produced per mole dissolved:
      - Al(OH)4^-: from complex formation
      - Al3+: free cation (minor when Kf is large)
      - OH-: from Ksp dissolution, consumed by complex formation

    For Al(OH)3 specifically:
      Each mole dissolved produces 1 Al3+ and 3 OH-.
      Complex formation consumes 1 Al3+ and 4 OH-.
      Net per mole that goes to complex: consumes 1 extra OH-.

    But in excess NaOH or when K_overall >> 1, effectively all dissolved
    Al goes to Al(OH)4^-, and the free [OH-] drives the overall reaction.

    For the standard problem (pure water, large K_overall):
      s = moles Al(OH)3 dissolved per liter
      Nearly all Al is Al(OH)4^-: [Al(OH)4^-] ~ s
      OH- balance: 3s produced - 4s consumed for complex = net -s consumed
        => need OH- from water autoionization, but Kw is tiny.

    Actually, for Al(OH)3 in pure water with large Kf:
      The overall reaction Al(OH)3(s) + OH- -> Al(OH)4^-  has K = Ksp*Kf
      Let s = solubility. Then [Al(OH)4^-] = s.
      The reaction consumes 1 OH- per mole dissolved.
      OH- sources: water autoionization (Kw = 1e-14).
      Mass balance on OH-: [OH-] = [OH-]_water - s (consumed)
      This is complicated — in practice we need the full system.

    Full system for Al(OH)3 in pure water:
      Let x = [Al3+], y = [Al(OH)4^-], h = [OH-]
      s = x + y  (total dissolved Al)

      Ksp = x * h^3                              ... (1)
      Kf = y / (x * h^4)                         ... (2)
      Charge balance: 3x + Kw/h = h + y          ... (3)
        (3x from Al3+, Kw/h = [H+], h = [OH-], y = [Al(OH)4^-])

    We solve this system numerically with Newton's method.
    """
    k_overall = ksp * kf
    kw = 1e-14

    # Newton's method on the full system.
    # Variables: x = [Al3+], h = [OH-]
    # Then y = Kf * x * h^4  (from eq 2)
    # Constraint from Ksp: x * h^3 = Ksp => x = Ksp / h^3
    # So y = Kf * (Ksp / h^3) * h^4 = Kf * Ksp * h = K_overall * h
    # Charge balance: 3x + Kw/h = h + y
    #   3 * Ksp/h^3 + Kw/h = h + K_overall * h
    #   3*Ksp/h^3 + Kw/h - h - K_overall*h = 0

    # f(h) = 3*Ksp*h^(-3) + Kw*h^(-1) - h - K_overall*h = 0
    # f'(h) = -9*Ksp*h^(-4) - Kw*h^(-2) - 1 - K_overall

    # Initial guess: assume complex dominates, so y ~ s, and charge balance
    # gives roughly K_overall*h ~ 3*Ksp/h^3 => h^4 ~ 3*Ksp/K_overall
    h = (3.0 * ksp / k_overall) ** 0.25 if k_overall > 0 else 1e-7

    for _ in range(200):
        h2 = h * h
        h3 = h2 * h
        h4 = h3 * h
        f_val = 3.0 * ksp / h3 + kw / h - h - k_overall * h
        f_prime = -9.0 * ksp / h4 - kw / h2 - 1.0 - k_overall
        delta = f_val / f_prime
        h_new = h - delta
        if h_new <= 0:
            h = h / 2.0
            continue
        if abs(delta) < 1e-20 * h:
            h = h_new
            break
        h = h_new

    x = ksp / (h**3)  # [Al3+]
    y = k_overall * h  # [Al(OH)4^-]
    s = x + y  # total solubility

    return {
        "solubility_mol_per_L": s,
        "free_cation_conc": x,
        "complex_conc": y,
        "free_anion_conc": h,
        "K_overall": k_overall,
        "Ksp": ksp,
        "Kf": kf,
        "note": (
            f"Overall K = Ksp * Kf = {k_overall:.4e}. "
            f"Complex dominates: [complex]/[free cation] = {y / x:.2e}"
        ),
    }


def solve_common_ion(ksp: float, a: int, b: int, common_ion_conc: float) -> dict:
    """Solve Ksp with a common-ion already present in solution.

    MaXb(s) <-> aM + bX, with extra [X] = c already in solution.
    Ksp = (a*s)^a * (b*s + c)^b

    For small s (common approximation when c >> b*s):
      Ksp ~ (a*s)^a * c^b  =>  s ~ (Ksp / (a^a * c^b))^(1/a)

    We solve exactly via bisection for general cases.
    """
    c = common_ion_conc

    def ksp_expr(s):
        return ((a * s) ** a) * ((b * s + c) ** b)

    # Upper bound: the simple Ksp solubility (no common ion)
    s_max = (ksp / ((a**a) * (b**b))) ** (1.0 / (a + b))
    s_lo, s_hi = 0.0, s_max

    for _ in range(200):
        s_mid = (s_lo + s_hi) / 2.0
        if ksp_expr(s_mid) < ksp:
            s_lo = s_mid
        else:
            s_hi = s_mid
        if (s_hi - s_lo) < 1e-20:
            break

    s = (s_lo + s_hi) / 2.0

    # Also compute the approximate value
    s_approx = (ksp / ((a**a) * (c**b))) ** (1.0 / a)

    return {
        "solubility_mol_per_L": s,
        "solubility_approx_mol_per_L": s_approx,
        "cation_conc": a * s,
        "anion_conc": b * s + c,
        "common_ion_added": c,
        "Ksp": ksp,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Equilibrium solver for Ksp, complex formation, and common-ion problems."
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=["ksp_simple", "ksp_kf", "common_ion"],
        help="Type of equilibrium problem",
    )
    parser.add_argument("--ksp", type=float, required=True, help="Ksp value")
    parser.add_argument("--kf", type=float, default=None, help="Kf (formation constant)")
    parser.add_argument(
        "--stoich",
        type=str,
        default="1:1",
        help="Stoichiometry a:b for MaXb (e.g., 1:3 for Al(OH)3)",
    )
    parser.add_argument(
        "--common-ion",
        type=float,
        default=None,
        help="Common ion concentration (mol/L)",
    )

    args = parser.parse_args()
    parts = args.stoich.split(":")
    if len(parts) != 2:
        print("ERROR: --stoich must be in form a:b (e.g., 1:3)", file=sys.stderr)
        sys.exit(1)
    a, b = int(parts[0]), int(parts[1])

    if args.type == "ksp_simple":
        result = solve_ksp_simple(args.ksp, a, b)
    elif args.type == "ksp_kf":
        if args.kf is None:
            print("ERROR: --kf required for ksp_kf mode", file=sys.stderr)
            sys.exit(1)
        result = solve_ksp_kf(args.ksp, args.kf, a, b)
    elif args.type == "common_ion":
        if args.common_ion is None:
            print("ERROR: --common-ion required for common_ion mode", file=sys.stderr)
            sys.exit(1)
        result = solve_common_ion(args.ksp, a, b, args.common_ion)
    else:
        print(f"ERROR: Unknown type {args.type}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Equilibrium Solver — mode: {args.type}")
    print(f"{'='*60}")
    for key, val in result.items():
        if isinstance(val, float):
            print(f"  {key:30s} = {val:.6e}")
        else:
            print(f"  {key:30s} = {val}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
