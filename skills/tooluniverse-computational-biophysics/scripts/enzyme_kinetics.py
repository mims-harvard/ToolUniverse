#!/usr/bin/env python3
"""Enzyme kinetics calculator: Km/Vmax, Hill coefficient, and Ki determination.

No external dependencies — uses only math stdlib.

Usage:
  python enzyme_kinetics.py --type km_vmax --substrate "1,2,5,10,20" --velocity "0.5,0.8,1.2,1.5,1.7"
  python enzyme_kinetics.py --type hill --substrate "0.1,0.5,1,2,5,10,50" --velocity "0.02,0.1,0.2,0.35,0.6,0.8,0.95"
  python enzyme_kinetics.py --type ki --substrate "1,2,5,10,20" --velocity_no_inh "0.5,0.8,1.2,1.5,1.7" --velocity_inh "0.3,0.5,0.8,1.0,1.1" --inhibitor_conc 5 --inhibition_type competitive
"""

import argparse
import math
import sys


# ---------------------------------------------------------------------------
# Km / Vmax via Lineweaver-Burk linear regression (1/v vs 1/[S])
# ---------------------------------------------------------------------------

def _linreg(xs, ys):
    """Simple linear regression: y = slope*x + intercept. Returns (slope, intercept, r2)."""
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-30:
        raise ValueError("Degenerate data — all x values identical.")
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy * sxx - sx * sxy) / denom
    y_mean = sy / n
    ss_tot = sum((y - y_mean) ** 2 for y in ys)
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(xs, ys))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return slope, intercept, r2


def calc_km_vmax(substrate, velocity):
    """Determine Km and Vmax using Lineweaver-Burk and direct nonlinear grid search."""
    if len(substrate) != len(velocity):
        raise ValueError("substrate and velocity must have the same length.")
    if len(substrate) < 3:
        raise ValueError("Need at least 3 data points.")

    # --- Method 1: Lineweaver-Burk ---
    inv_s = [1.0 / s for s in substrate]
    inv_v = [1.0 / v for v in velocity]
    slope, intercept, r2 = _linreg(inv_s, inv_v)

    if intercept <= 0 or slope <= 0:
        lb_vmax = None
        lb_km = None
        lb_note = "Lineweaver-Burk gave non-physical (negative) parameters — data may not follow Michaelis-Menten."
    else:
        lb_vmax = 1.0 / intercept
        lb_km = slope * lb_vmax
        lb_note = None

    # --- Method 2: Nonlinear least-squares via grid + refinement ---
    vmax_est = max(velocity) * 1.2
    km_est = substrate[len(substrate) // 2]
    best_sse = float("inf")
    best_km, best_vmax = km_est, vmax_est

    for vmax_mult in [x * 0.1 for x in range(5, 31)]:
        for km_mult in [x * 0.1 for x in range(1, 51)]:
            vm = max(velocity) * vmax_mult
            km = max(substrate) * km_mult * 0.1
            sse = sum((v - vm * s / (km + s)) ** 2 for s, v in zip(substrate, velocity))
            if sse < best_sse:
                best_sse = sse
                best_km, best_vmax = km, vm

    # Refine with smaller steps around best
    for _ in range(3):
        step_v = best_vmax * 0.05
        step_k = best_km * 0.05
        improved = False
        for dv in [-step_v, 0, step_v]:
            for dk in [-step_k, 0, step_k]:
                vm = best_vmax + dv
                km = best_km + dk
                if vm <= 0 or km <= 0:
                    continue
                sse = sum((v - vm * s / (km + s)) ** 2 for s, v in zip(substrate, velocity))
                if sse < best_sse:
                    best_sse = sse
                    best_km, best_vmax = km, vm
                    improved = True
        if not improved:
            break

    # R-squared for nonlinear fit
    v_mean = sum(velocity) / len(velocity)
    ss_tot = sum((v - v_mean) ** 2 for v in velocity)
    nl_r2 = 1.0 - best_sse / ss_tot if ss_tot > 0 else 0.0

    print("=" * 60)
    print("MICHAELIS-MENTEN KINETICS: Km and Vmax")
    print("=" * 60)
    print(f"\nData points: {len(substrate)}")
    print(f"[S] range: {min(substrate):.4g} - {max(substrate):.4g}")
    print(f"v range:   {min(velocity):.4g} - {max(velocity):.4g}")

    print("\n--- Lineweaver-Burk (1/v vs 1/[S]) ---")
    if lb_vmax is not None:
        print(f"  Vmax = {lb_vmax:.4g}")
        print(f"  Km   = {lb_km:.4g}")
        print(f"  R²   = {r2:.4f}")
    else:
        print(f"  {lb_note}")

    print("\n--- Nonlinear fit (grid search) ---")
    print(f"  Vmax = {best_vmax:.4g}")
    print(f"  Km   = {best_km:.4g}")
    print(f"  R²   = {nl_r2:.4f}")
    print(f"  SSE  = {best_sse:.4g}")

    print("\n--- Predicted vs Observed ---")
    print(f"  {'[S]':>10s}  {'v_obs':>10s}  {'v_pred':>10s}  {'residual':>10s}")
    for s, v in zip(substrate, velocity):
        v_pred = best_vmax * s / (best_km + s)
        print(f"  {s:10.4g}  {v:10.4g}  {v_pred:10.4g}  {v - v_pred:10.4g}")

    print("\n--- Catalytic efficiency ---")
    print(f"  kcat/Km = Vmax/Km = {best_vmax / best_km:.4g} (units depend on [E] normalization)")
    print("\nNote: For publication-quality fits, use scipy.optimize.curve_fit with proper error estimates.")


# ---------------------------------------------------------------------------
# Hill coefficient from cooperative binding data
# ---------------------------------------------------------------------------

def calc_hill(substrate, velocity):
    """Determine Hill coefficient from log-log linearization of binding data."""
    if len(substrate) != len(velocity):
        raise ValueError("substrate and velocity must have the same length.")
    if len(substrate) < 3:
        raise ValueError("Need at least 3 data points.")

    vmax_est = max(velocity) * 1.1

    # Hill linearization: log(v / (Vmax - v)) = nH * log([S]) - nH * log(K0.5)
    # Use data points where 0.1*Vmax < v < 0.9*Vmax for reliable linearization
    log_s = []
    log_y = []
    for s, v in zip(substrate, velocity):
        if 0.1 * vmax_est < v < 0.9 * vmax_est:
            y = v / (vmax_est - v)
            if y > 0:
                log_s.append(math.log10(s))
                log_y.append(math.log10(y))

    if len(log_s) < 2:
        # Try broader range with adjusted Vmax
        vmax_est = max(velocity) * 1.3
        for s, v in zip(substrate, velocity):
            if 0.05 * vmax_est < v < 0.95 * vmax_est:
                y = v / (vmax_est - v)
                if y > 0:
                    log_s.append(math.log10(s))
                    log_y.append(math.log10(y))

    if len(log_s) < 2:
        print("ERROR: Insufficient data points in the 10-90% saturation range for Hill analysis.")
        print("Provide more data points spanning a wider concentration range.")
        sys.exit(1)

    slope, intercept, r2 = _linreg(log_s, log_y)
    nH = slope
    k05 = 10 ** (-intercept / nH) if abs(nH) > 1e-10 else float("inf")

    print("=" * 60)
    print("HILL ANALYSIS: Cooperative Binding")
    print("=" * 60)
    print(f"\nData points used for Hill plot: {len(log_s)} of {len(substrate)}")
    print(f"Estimated Vmax: {vmax_est:.4g}")
    print(f"\n--- Hill Parameters ---")
    print(f"  Hill coefficient (nH) = {nH:.3f}")
    print(f"  K0.5                  = {k05:.4g}")
    print(f"  R² (Hill plot)        = {r2:.4f}")

    print(f"\n--- Interpretation ---")
    if nH > 1.05:
        print(f"  nH = {nH:.2f} > 1 → POSITIVE cooperativity")
        print(f"  Binding at one site increases affinity at other sites.")
    elif nH < 0.95:
        print(f"  nH = {nH:.2f} < 1 → NEGATIVE cooperativity")
        print(f"  Binding at one site decreases affinity at other sites.")
    else:
        print(f"  nH = {nH:.2f} ≈ 1 → NO cooperativity (independent sites)")

    print(f"\n--- Predicted vs Observed ---")
    print(f"  {'[S]':>10s}  {'v_obs':>10s}  {'v_pred':>10s}")
    for s, v in zip(substrate, velocity):
        v_pred = vmax_est * (s ** nH) / (k05 ** nH + s ** nH)
        print(f"  {s:10.4g}  {v:10.4g}  {v_pred:10.4g}")

    print(f"\nNote: nH is an empirical parameter, not the number of binding sites.")
    print(f"True number of sites must be determined by stoichiometry (ITC, AUC).")


# ---------------------------------------------------------------------------
# Ki from inhibition data
# ---------------------------------------------------------------------------

def calc_ki(substrate, velocity_no_inh, velocity_inh, inhibitor_conc, inhibition_type):
    """Determine Ki from paired velocity data with and without inhibitor."""
    n = len(substrate)
    if len(velocity_no_inh) != n or len(velocity_inh) != n:
        raise ValueError("All data arrays must have the same length.")
    if n < 3:
        raise ValueError("Need at least 3 data points.")

    # First, get Km and Vmax from uninhibited data
    inv_s = [1.0 / s for s in substrate]
    inv_v0 = [1.0 / v for v in velocity_no_inh]
    slope0, intercept0, r2_0 = _linreg(inv_s, inv_v0)

    if intercept0 <= 0 or slope0 <= 0:
        print("ERROR: Uninhibited data does not give valid Km/Vmax. Check data.")
        sys.exit(1)

    vmax = 1.0 / intercept0
    km = slope0 * vmax

    # Get apparent parameters from inhibited data
    inv_vi = [1.0 / v for v in velocity_inh]
    slope_i, intercept_i, r2_i = _linreg(inv_s, inv_vi)

    if intercept_i <= 0 or slope_i <= 0:
        print("ERROR: Inhibited data does not give valid apparent parameters. Check data.")
        sys.exit(1)

    vmax_app = 1.0 / intercept_i
    km_app = slope_i * vmax_app

    inh_type = inhibition_type.lower().strip()
    ki = None

    print("=" * 60)
    print(f"ENZYME INHIBITION ANALYSIS: {inhibition_type.title()}")
    print("=" * 60)
    print(f"\nInhibitor concentration: {inhibitor_conc}")
    print(f"\n--- Uninhibited Parameters ---")
    print(f"  Vmax = {vmax:.4g}")
    print(f"  Km   = {km:.4g}")
    print(f"  R²   = {r2_0:.4f}")
    print(f"\n--- Inhibited Apparent Parameters ---")
    print(f"  Vmax_app = {vmax_app:.4g}")
    print(f"  Km_app   = {km_app:.4g}")
    print(f"  R²       = {r2_i:.4f}")

    if inh_type == "competitive":
        # Competitive: Km_app = Km * (1 + [I]/Ki), Vmax unchanged
        # Ki = [I] / (Km_app/Km - 1)
        ratio = km_app / km
        if ratio <= 1.0:
            print(f"\nWARNING: Km_app ({km_app:.4g}) <= Km ({km:.4g}). Not consistent with competitive inhibition.")
        else:
            ki = inhibitor_conc / (ratio - 1.0)
        print(f"\n--- Competitive Inhibition ---")
        print(f"  Km_app / Km = {ratio:.4f}")
        print(f"  Expected: Vmax_app ≈ Vmax (ratio = {vmax_app / vmax:.3f})")

    elif inh_type == "uncompetitive":
        # Uncompetitive: Vmax_app = Vmax / (1 + [I]/Ki), Km_app = Km / (1 + [I]/Ki)
        ratio = vmax / vmax_app
        if ratio <= 1.0:
            print(f"\nWARNING: Vmax_app ({vmax_app:.4g}) >= Vmax ({vmax:.4g}). Not consistent with uncompetitive inhibition.")
        else:
            ki = inhibitor_conc / (ratio - 1.0)
        print(f"\n--- Uncompetitive Inhibition ---")
        print(f"  Vmax / Vmax_app = {ratio:.4f}")
        print(f"  Km / Km_app = {km / km_app:.4f} (should ≈ {ratio:.4f})")

    elif inh_type in ("noncompetitive", "non-competitive"):
        # Pure noncompetitive: Vmax_app = Vmax / (1 + [I]/Ki), Km unchanged
        ratio = vmax / vmax_app
        if ratio <= 1.0:
            print(f"\nWARNING: Vmax_app ({vmax_app:.4g}) >= Vmax ({vmax:.4g}). Not consistent with noncompetitive inhibition.")
        else:
            ki = inhibitor_conc / (ratio - 1.0)
        print(f"\n--- Noncompetitive Inhibition ---")
        print(f"  Vmax / Vmax_app = {ratio:.4f}")
        print(f"  Expected: Km_app ≈ Km (ratio = {km_app / km:.3f})")

    else:
        print(f"\nERROR: Unknown inhibition type '{inhibition_type}'. Use: competitive, uncompetitive, noncompetitive.")
        sys.exit(1)

    if ki is not None:
        print(f"\n  Ki = {ki:.4g}")
        print(f"\n--- Verification ---")
        print(f"  {'[S]':>10s}  {'v_obs':>10s}  {'v_pred':>10s}  {'residual':>10s}")
        for s, v_obs in zip(substrate, velocity_inh):
            if inh_type == "competitive":
                v_pred = vmax * s / (km * (1 + inhibitor_conc / ki) + s)
            elif inh_type == "uncompetitive":
                factor = 1 + inhibitor_conc / ki
                v_pred = (vmax / factor) * s / (km / factor + s)
            else:  # noncompetitive
                v_pred = (vmax / (1 + inhibitor_conc / ki)) * s / (km + s)
            print(f"  {s:10.4g}  {v_obs:10.4g}  {v_pred:10.4g}  {v_obs - v_pred:10.4g}")
    else:
        print(f"\n  Ki could not be determined — check data consistency with {inhibition_type} model.")

    print(f"\nNote: Lineweaver-Burk analysis amplifies error at low [S]. For publication, use nonlinear regression.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_floats(s):
    """Parse comma-separated float string."""
    return [float(x.strip()) for x in s.split(",")]


def main():
    parser = argparse.ArgumentParser(description="Enzyme kinetics calculator")
    parser.add_argument("--type", required=True, choices=["km_vmax", "hill", "ki"],
                        help="Calculation type")
    parser.add_argument("--substrate", help="Comma-separated substrate concentrations")
    parser.add_argument("--velocity", help="Comma-separated velocity values")
    parser.add_argument("--velocity_no_inh", help="Velocities without inhibitor (for ki)")
    parser.add_argument("--velocity_inh", help="Velocities with inhibitor (for ki)")
    parser.add_argument("--inhibitor_conc", type=float, help="Inhibitor concentration (for ki)")
    parser.add_argument("--inhibition_type", default="competitive",
                        help="Type of inhibition: competitive, uncompetitive, noncompetitive")

    args = parser.parse_args()

    if args.type == "km_vmax":
        if not args.substrate or not args.velocity:
            parser.error("--substrate and --velocity required for km_vmax")
        calc_km_vmax(parse_floats(args.substrate), parse_floats(args.velocity))

    elif args.type == "hill":
        if not args.substrate or not args.velocity:
            parser.error("--substrate and --velocity required for hill")
        calc_hill(parse_floats(args.substrate), parse_floats(args.velocity))

    elif args.type == "ki":
        if not args.substrate or not args.velocity_no_inh or not args.velocity_inh:
            parser.error("--substrate, --velocity_no_inh, and --velocity_inh required for ki")
        if args.inhibitor_conc is None:
            parser.error("--inhibitor_conc required for ki")
        calc_ki(
            parse_floats(args.substrate),
            parse_floats(args.velocity_no_inh),
            parse_floats(args.velocity_inh),
            args.inhibitor_conc,
            args.inhibition_type,
        )


if __name__ == "__main__":
    main()
