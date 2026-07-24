#!/usr/bin/env python3
"""Crystal structure validator.

Calculates theoretical density from unit cell parameters, Z value, and
molecular weight, then compares against a reported density to flag
inconsistencies.

Supports all seven crystal systems:
  cubic, tetragonal, orthorhombic, hexagonal, trigonal, monoclinic, triclinic

Usage examples:
  python crystal_validator.py --a 5.43 --b 5.43 --c 5.43 --Z 8 --MW 28.085 --density 2.329
  python crystal_validator.py --a 4.916 --b 4.916 --c 5.405 --alpha 90 --beta 90 --gamma 120 --Z 3 --MW 60.08 --density 2.648
  python crystal_validator.py --a 10.0 --b 11.0 --c 12.0 --alpha 80 --beta 85 --gamma 70 --Z 4 --MW 300.0 --density 1.55
  python crystal_validator.py --datasets datasets.json   # batch mode: validate multiple datasets
"""

import argparse
import json
import math
import sys

AVOGADRO = 6.02214076e23  # mol^-1
ANG3_TO_CM3 = 1e-24  # 1 A^3 = 1e-24 cm^3


def unit_cell_volume(a, b, c, alpha_deg, beta_deg, gamma_deg):
    """Compute unit cell volume in A^3 for any crystal system.

    V = a * b * c * sqrt(1 - cos^2(alpha) - cos^2(beta) - cos^2(gamma)
                         + 2*cos(alpha)*cos(beta)*cos(gamma))
    """
    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    gamma = math.radians(gamma_deg)

    ca = math.cos(alpha)
    cb = math.cos(beta)
    cg = math.cos(gamma)

    val = 1.0 - ca**2 - cb**2 - cg**2 + 2.0 * ca * cb * cg
    if val < 0:
        raise ValueError(
            f"Invalid cell angles: alpha={alpha_deg}, beta={beta_deg}, "
            f"gamma={gamma_deg} produce negative discriminant ({val:.6f})"
        )
    return a * b * c * math.sqrt(val)


def theoretical_density(Z, MW, volume_ang3):
    """Calculate density in g/cm^3.

    d = (Z * MW) / (V * Na)
    where V is in cm^3.
    """
    volume_cm3 = volume_ang3 * ANG3_TO_CM3
    return (Z * MW) / (volume_cm3 * AVOGADRO)


def detect_crystal_system(a, b, c, alpha, beta, gamma, tol=0.01, ang_tol=0.1):
    """Infer crystal system from cell parameters."""
    eq_ab = abs(a - b) < tol
    eq_ac = abs(a - c) < tol
    eq_bc = abs(b - c) < tol
    all_eq = eq_ab and eq_ac

    is_90 = lambda x: abs(x - 90.0) < ang_tol
    is_120 = lambda x: abs(x - 120.0) < ang_tol
    all_90 = is_90(alpha) and is_90(beta) and is_90(gamma)

    if all_eq and all_90:
        return "cubic"
    if eq_ab and all_90 and not eq_ac:
        return "tetragonal"
    if all_90 and not eq_ab and not eq_ac and not eq_bc:
        return "orthorhombic"
    if eq_ab and is_90(alpha) and is_90(beta) and is_120(gamma):
        return "hexagonal"
    if all_eq and abs(alpha - beta) < ang_tol and abs(alpha - gamma) < ang_tol and not all_90:
        return "trigonal (rhombohedral)"
    if is_90(alpha) and is_90(gamma) and not is_90(beta):
        return "monoclinic"
    return "triclinic"


def validate_single(params, label=""):
    """Validate a single crystal dataset. Returns dict with results."""
    a = params["a"]
    b = params["b"]
    c = params["c"]
    alpha = params.get("alpha", 90.0)
    beta = params.get("beta", 90.0)
    gamma = params.get("gamma", 90.0)
    Z = params["Z"]
    MW = params["MW"]
    reported = params.get("density")

    V = unit_cell_volume(a, b, c, alpha, beta, gamma)
    d_calc = theoretical_density(Z, MW, V)
    system = detect_crystal_system(a, b, c, alpha, beta, gamma)

    result = {
        "label": label,
        "crystal_system": system,
        "cell_params": {"a": a, "b": b, "c": c, "alpha": alpha, "beta": beta, "gamma": gamma},
        "volume_ang3": round(V, 4),
        "Z": Z,
        "MW": MW,
        "calculated_density": round(d_calc, 4),
    }

    if reported is not None:
        diff = abs(d_calc - reported)
        pct = (diff / reported) * 100 if reported != 0 else float("inf")
        result["reported_density"] = reported
        result["difference"] = round(diff, 4)
        result["percent_error"] = round(pct, 2)
        if pct < 1.0:
            result["verdict"] = "OK"
        elif pct < 5.0:
            result["verdict"] = "WARNING — deviation > 1%"
        else:
            result["verdict"] = "MISMATCH — deviation > 5%, likely error"
    return result


def print_result(r):
    """Pretty-print a single validation result."""
    if r["label"]:
        print(f"\n=== Dataset: {r['label']} ===")
    print(f"  Crystal system:      {r['crystal_system']}")
    print(f"  Cell:                a={r['cell_params']['a']}, b={r['cell_params']['b']}, "
          f"c={r['cell_params']['c']}")
    print(f"  Angles:              alpha={r['cell_params']['alpha']}, "
          f"beta={r['cell_params']['beta']}, gamma={r['cell_params']['gamma']}")
    print(f"  Volume:              {r['volume_ang3']} A^3")
    print(f"  Z={r['Z']}, MW={r['MW']} g/mol")
    print(f"  Calculated density:  {r['calculated_density']} g/cm^3")
    if "reported_density" in r:
        print(f"  Reported density:    {r['reported_density']} g/cm^3")
        print(f"  Difference:          {r['difference']} g/cm^3 ({r['percent_error']}%)")
        print(f"  Verdict:             {r['verdict']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate crystal structure density from unit cell parameters."
    )
    parser.add_argument("--a", type=float, help="Cell parameter a (Angstroms)")
    parser.add_argument("--b", type=float, help="Cell parameter b (Angstroms)")
    parser.add_argument("--c", type=float, help="Cell parameter c (Angstroms)")
    parser.add_argument("--alpha", type=float, default=90.0, help="Angle alpha (degrees, default 90)")
    parser.add_argument("--beta", type=float, default=90.0, help="Angle beta (degrees, default 90)")
    parser.add_argument("--gamma", type=float, default=90.0, help="Angle gamma (degrees, default 90)")
    parser.add_argument("--Z", type=int, help="Number of formula units per unit cell")
    parser.add_argument("--MW", type=float, help="Molecular weight (g/mol)")
    parser.add_argument("--density", type=float, help="Reported density (g/cm^3) to compare against")
    parser.add_argument(
        "--datasets", type=str,
        help="Path to JSON file with array of datasets to validate in batch mode"
    )
    args = parser.parse_args()

    if args.datasets:
        with open(args.datasets) as f:
            datasets = json.load(f)
        results = []
        for i, ds in enumerate(datasets):
            label = ds.get("label", f"Dataset {i + 1}")
            r = validate_single(ds, label=label)
            results.append(r)
            print_result(r)

        # Summary
        errors = [r for r in results if r.get("verdict", "").startswith("MISMATCH")]
        warnings = [r for r in results if r.get("verdict", "").startswith("WARNING")]
        print("=" * 50)
        print(f"SUMMARY: {len(results)} datasets checked")
        print(f"  OK:       {len(results) - len(errors) - len(warnings)}")
        print(f"  Warnings: {len(warnings)}")
        print(f"  Errors:   {len(errors)}")
        if errors:
            print(f"  Error datasets: {', '.join(r['label'] for r in errors)}")
        return 1 if errors else 0

    elif args.a and args.Z and args.MW:
        params = {
            "a": args.a, "b": args.b or args.a, "c": args.c or args.a,
            "alpha": args.alpha, "beta": args.beta, "gamma": args.gamma,
            "Z": args.Z, "MW": args.MW, "density": args.density,
        }
        r = validate_single(params)
        print_result(r)
        return 1 if r.get("verdict", "").startswith("MISMATCH") else 0

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
