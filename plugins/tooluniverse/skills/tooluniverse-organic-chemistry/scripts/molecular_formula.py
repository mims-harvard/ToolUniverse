"""Calculate molecular formula from combustion analysis data, or analyse a known formula.

Mode 1 — combustion analysis:
    python molecular_formula.py --sample_g 0.5 --CO2_g 0.7472 --H2O_g 0.1834
    python molecular_formula.py --sample_g 0.5 --CO2_g 0.7472 --H2O_g 0.1834 --molar_mass 120
    python molecular_formula.py --sample_g 0.2 --CO2_g 0.4874 --H2O_g 0.1998 --N2_g 0 --molar_mass 78

Mode 2 — formula analysis (MW, DoU, elemental composition):
    python molecular_formula.py --formula C6H12O6
    python molecular_formula.py --formula C8H9NO2
    python molecular_formula.py --formula C6H6

Output: empirical formula, molecular formula (if MW given), degrees of unsaturation,
elemental mass percentages.
"""

import argparse
import sys
from functools import reduce
from math import gcd

# Atomic masses (IUPAC 2021 standard)
ATOMIC_MASS = {"C": 12.011, "H": 1.008, "O": 15.999, "N": 14.007}


def _igcd(values: list[int]) -> int:
    """GCD of a list of positive integers."""
    return reduce(gcd, values)


def combustion_to_empirical(
    mass_sample_g: float,
    mass_CO2_g: float,
    mass_H2O_g: float,
    mass_N2_g: float = 0.0,
) -> dict:
    """
    Convert combustion analysis masses to molar ratios.
    Returns element moles, mole ratios, and empirical formula string.
    """
    M = ATOMIC_MASS
    moles_C = mass_CO2_g / (M["C"] + 2 * M["O"])
    moles_H = mass_H2O_g / (2 * M["H"] + M["O"]) * 2
    moles_N = (mass_N2_g / (2 * M["N"])) * 2

    mass_accounted = moles_C * M["C"] + moles_H * M["H"] + moles_N * M["N"]
    mass_O = mass_sample_g - mass_accounted
    moles_O = max(mass_O / M["O"], 0.0)

    present = {k: v for k, v in {"C": moles_C, "H": moles_H, "O": moles_O, "N": moles_N}.items() if v > 1e-6}
    min_moles = min(present.values())
    ratios = {k: v / min_moles for k, v in present.items()}

    # Scale to near-integers (test denominators 1–6)
    best_denom = 1
    best_err = float("inf")
    for denom in range(1, 7):
        err = sum(abs(r * denom - round(r * denom)) for r in ratios.values())
        if err < best_err:
            best_err = err
            best_denom = denom

    scaled = {k: round(v * best_denom) for k, v in ratios.items()}
    g = _igcd(list(scaled.values()))
    empirical = {k: v // g for k, v in scaled.items()}

    emp_mass = sum(n * M[e] for e, n in empirical.items())
    formula_str = _formula_str(empirical)

    return {
        "moles_C": round(moles_C, 6),
        "moles_H": round(moles_H, 6),
        "moles_O": round(moles_O, 6),
        "moles_N": round(moles_N, 6),
        "empirical_formula": formula_str,
        "empirical_molar_mass": round(emp_mass, 3),
        "mass_O_g": round(mass_O, 4),
    }


def molecular_formula_from_mw(empirical: dict, molar_mass: float) -> dict:
    """Scale empirical formula to molecular formula using known molar mass."""
    M = ATOMIC_MASS
    emp_mass = sum(n * M[e] for e, n in empirical.items())
    factor = round(molar_mass / emp_mass)
    mol = {k: v * factor for k, v in empirical.items()}
    return {
        "factor": factor,
        "molecular_formula": _formula_str(mol),
        "molecular_molar_mass": round(sum(n * M[e] for e, n in mol.items()), 3),
        "atoms": mol,
    }


def parse_formula(formula_str: str) -> dict:
    """
    Parse a molecular formula string into an element-count dict.
    Supports: C6H12O6, C8H9NO2, C6H5Cl, etc.
    Elements must be written with proper capitalisation (C, H, N, O, Cl, Br, F, I, S, P).
    """
    import re

    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula_str)
    atoms: dict[str, int] = {}
    for element, count in tokens:
        if not element:
            continue
        n = int(count) if count else 1
        atoms[element] = atoms.get(element, 0) + n
    return atoms


def degrees_of_unsaturation(atoms: dict) -> float:
    """
    DoU = (2C + 2 + N - H - X) / 2
    O and S do not contribute. Halogens (F, Cl, Br, I) count as -1 each.
    """
    C = atoms.get("C", 0)
    H = atoms.get("H", 0)
    N = atoms.get("N", 0)
    X = sum(atoms.get(x, 0) for x in ("F", "Cl", "Br", "I"))
    return (2 * C + 2 + N - H - X) / 2


def elemental_composition(atoms: dict) -> dict:
    """Mass percentages for each element present."""
    # Use extended mass table for formula analysis mode
    MASS = {
        **ATOMIC_MASS,
        "S": 32.06,
        "P": 30.974,
        "F": 18.998,
        "Cl": 35.45,
        "Br": 79.904,
        "I": 126.904,
    }
    total_mass = sum(n * MASS.get(e, 0.0) for e, n in atoms.items())
    pcts = {e: round(n * MASS.get(e, 0.0) / total_mass * 100, 2) for e, n in atoms.items()}
    return {"molar_mass": round(total_mass, 3), "percentages": pcts}


def _formula_str(atoms: dict) -> str:
    """Hill notation: C first, H second, then remaining elements alphabetically."""
    order = []
    for e in ("C", "H"):
        if e in atoms:
            order.append(e)
    for e in sorted(k for k in atoms if k not in ("C", "H")):
        order.append(e)
    parts = []
    for e in order:
        n = atoms[e]
        parts.append(f"{e}{n if n > 1 else ''}")
    return "".join(parts)


def _interpret_dou(dou: float) -> str:
    if dou == 0:
        return "saturated, open-chain (no rings or double bonds)"
    hints = []
    if dou >= 4:
        hints.append("likely contains a benzene ring (4 DoU)")
    if dou >= 2:
        hints.append("could have a triple bond, or two double bonds, or a ring + double bond")
    if dou == 1:
        hints.append("one ring OR one double bond")
    return "; ".join(hints) if hints else f"DoU = {dou}"


def main():
    parser = argparse.ArgumentParser(
        description="Molecular formula calculator: combustion analysis or formula analysis.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    # Mode 1: combustion analysis
    grp = parser.add_argument_group("Combustion analysis mode")
    grp.add_argument("--sample_g", type=float, help="Mass of sample burned (g).")
    grp.add_argument("--CO2_g", type=float, help="Mass of CO2 collected (g).")
    grp.add_argument("--H2O_g", type=float, help="Mass of H2O collected (g).")
    grp.add_argument("--N2_g", type=float, default=0.0, help="Mass of N2 collected (g); omit if no nitrogen.")
    grp.add_argument("--molar_mass", type=float, default=None, help="Known molar mass (g/mol) to determine molecular formula.")

    # Mode 2: formula analysis
    grp2 = parser.add_argument_group("Formula analysis mode")
    grp2.add_argument("--formula", type=str, default=None, help="Molecular formula string, e.g. C6H12O6.")

    args = parser.parse_args()

    if args.formula:
        # Mode 2
        atoms = parse_formula(args.formula)
        if not atoms:
            print(f"Error: could not parse formula '{args.formula}'.")
            sys.exit(1)
        comp = elemental_composition(atoms)
        dou = degrees_of_unsaturation(atoms)
        dou_hint = _interpret_dou(dou)

        print("=" * 60)
        print(f"  Formula Analysis: {args.formula}")
        print("=" * 60)
        print(f"  Molar mass            : {comp['molar_mass']:.3f} g/mol")
        print()
        print(f"  Elemental composition:")
        for elem, pct in sorted(comp["percentages"].items()):
            print(f"    {elem:<4}: {pct:.2f}%")
        print()
        print(f"  Degrees of unsaturation (DoU): {dou:.1f}")
        print(f"    → {dou_hint}")
        print()
        # Verify: sum of percentages
        total_pct = sum(comp["percentages"].values())
        print(f"  Verification: sum of mass percentages = {total_pct:.2f}%  (should be ~100.00%)")
        print("=" * 60)

    elif args.sample_g is not None and args.CO2_g is not None and args.H2O_g is not None:
        # Mode 1
        if args.sample_g <= 0 or args.CO2_g < 0 or args.H2O_g < 0:
            print("Error: masses must be non-negative (sample_g must be positive).")
            sys.exit(1)

        result = combustion_to_empirical(args.sample_g, args.CO2_g, args.H2O_g, args.N2_g)

        print("=" * 62)
        print("  Combustion Analysis → Molecular Formula")
        print("=" * 62)
        print(f"  Sample mass  : {args.sample_g} g")
        print(f"  CO2 collected: {args.CO2_g} g")
        print(f"  H2O collected: {args.H2O_g} g")
        if args.N2_g:
            print(f"  N2 collected : {args.N2_g} g")
        print()
        print(f"  Moles extracted from combustion products:")
        print(f"    C : {result['moles_C']:.6f} mol   (from CO2)")
        print(f"    H : {result['moles_H']:.6f} mol   (from H2O)")
        if result["moles_N"] > 1e-6:
            print(f"    N : {result['moles_N']:.6f} mol   (from N2)")
        print(f"    O : {result['moles_O']:.6f} mol   (by difference; mass = {result['mass_O_g']} g)")
        print()
        print(f"  Empirical formula     : {result['empirical_formula']}")
        print(f"  Empirical molar mass  : {result['empirical_molar_mass']:.3f} g/mol")

        emp_atoms = parse_formula(result["empirical_formula"])

        if args.molar_mass is not None:
            mf = molecular_formula_from_mw(emp_atoms, args.molar_mass)
            print()
            print(f"  Given molar mass      : {args.molar_mass} g/mol")
            print(f"  Scale factor          : {mf['factor']}  ({args.molar_mass} / {result['empirical_molar_mass']:.3f} ≈ {mf['factor']})")
            print(f"  Molecular formula     : {mf['molecular_formula']}")
            print(f"  Molecular molar mass  : {mf['molecular_molar_mass']:.3f} g/mol")

            mol_atoms = parse_formula(mf["molecular_formula"])
            dou = degrees_of_unsaturation(mol_atoms)
            comp = elemental_composition(mol_atoms)
            print()
            print(f"  Degrees of unsaturation (DoU): {dou:.1f}")
            print(f"    → {_interpret_dou(dou)}")
            print()
            print(f"  Elemental composition (from molecular formula):")
            for elem, pct in sorted(comp["percentages"].items()):
                print(f"    {elem:<4}: {pct:.2f}%")
        else:
            dou = degrees_of_unsaturation(emp_atoms)
            comp = elemental_composition(emp_atoms)
            print()
            print(f"  Degrees of unsaturation (DoU): {dou:.1f}")
            print(f"    → {_interpret_dou(dou)}")
            print()
            print(f"  Elemental composition (empirical formula):")
            for elem, pct in sorted(comp["percentages"].items()):
                print(f"    {elem:<4}: {pct:.2f}%")
            print()
            print("  Tip: provide --molar_mass to determine the molecular formula.")

        # Verification
        print()
        total_pct = sum(elemental_composition(parse_formula(
            result["empirical_formula"] if args.molar_mass is None else mf["molecular_formula"]  # type: ignore[possibly-undefined]
        ))["percentages"].values())
        print(f"  Verification: sum of mass percentages = {total_pct:.2f}%  (should be ~100.00%)")
        print("=" * 62)

    else:
        parser.print_help()
        print("\nError: provide either --formula, or all of --sample_g, --CO2_g, --H2O_g.")
        sys.exit(1)


if __name__ == "__main__":
    main()
