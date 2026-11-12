"""
Prototype example: tooluniverse-reaction-engineering

Demonstrates reactor sizing calculations that a chemical engineering skill
would guide. These are hand/Python calculations (the skill describes WHAT to
do and which formulas to use; it does not auto-execute).

Run:
    python example_cstr_pfr.py
"""

import math


def cstr_volume_first_order(F_A0, k, C_A0, X):
    """CSTR volume for first-order reaction, constant density."""
    return F_A0 * X / (k * C_A0 * (1 - X))


def pfr_volume_first_order(F_A0, k, X):
    """PFR volume for first-order reaction (analytic)."""
    return (F_A0 / k) * math.log(1 / (1 - X))


def batch_time_first_order(k, X):
    """Batch reaction time for first-order reaction."""
    return (1 / k) * math.log(1 / (1 - X))


def arrhenius_k(k1, T1, T2, Ea, R=8.314):
    """Arrhenius temperature correction: k2 at T2 given k1 at T1."""
    return k1 * math.exp((Ea / R) * (1 / T1 - 1 / T2))


def main():
    # --- Problem data ---
    F_A0 = 10.0      # mol/min
    k_25 = 0.05      # min^-1 at 25 C
    C_A0 = 2.0       # mol/L
    X = 0.90         # target conversion
    T1 = 25 + 273.15 # K
    T2 = 50 + 273.15 # K
    Ea = 50000       # J/mol

    # --- Phase 1: kinetics stated (first-order) ---
    print("=== Phase 1: Kinetics ===")
    print(f"Rate law: -r_A = k * C_A,  k = {k_25} min^-1 at 25 C")
    print(f"Reaction order: 1 (first-order)")
    print()

    # --- Phase 2: reactor sizing at 25 C ---
    print("=== Phase 2: Reactor Sizing at 25 C ===")
    v0 = F_A0 / C_A0  # L/min

    V_cstr = cstr_volume_first_order(F_A0, k_25, C_A0, X)
    V_pfr = pfr_volume_first_order(F_A0, k_25, X)
    t_batch = batch_time_first_order(k_25, X)

    tau_cstr = V_cstr / v0
    tau_pfr = V_pfr / v0

    print(f"Feed volumetric flow v0 = {v0:.2f} L/min")
    print(f"CSTR volume for {X*100:.0f}% conversion = {V_cstr:.1f} L")
    print(f"CSTR space time = {tau_cstr:.1f} min")
    print(f"PFR volume for {X*100:.0f}% conversion = {V_pfr:.1f} L")
    print(f"PFR space time = {tau_pfr:.1f} min")
    print(f"Batch time for {X*100:.0f}% conversion = {t_batch:.1f} min")
    print(f"CSTR/PFR volume ratio = {V_cstr / V_pfr:.2f}x")
    print()

    # --- Phase 3: Arrhenius correction to 50 C ---
    print("=== Phase 3: Arrhenius Correction to 50 C ===")
    k_50 = arrhenius_k(k_25, T1, T2, Ea)
    print(f"k at 50 C = {k_50:.4f} min^-1")

    V_cstr_50 = cstr_volume_first_order(F_A0, k_50, C_A0, X)
    V_pfr_50 = pfr_volume_first_order(F_A0, k_50, X)
    print(f"CSTR volume at 50 C = {V_cstr_50:.1f} L")
    print(f"PFR volume at 50 C = {V_pfr_50:.1f} L")
    print()

    # --- Assumptions ---
    print("=== Assumptions ===")
    print("- Liquid-phase, constant density")
    print("- Isothermal operation")
    print("- Ideal reactors (CSTR / PFR / batch)")
    print("- First-order kinetics (assumed; verify from data)")
    print()


if __name__ == "__main__":
    main()
