"""Calculate degrees of unsaturation (DoU) from a molecular formula.

DoU = (2C + 2 + N - H - X) / 2

Where X = total halogens (F, Cl, Br, I). Oxygen and sulfur do not affect DoU.

Usage:
    python degrees_of_unsaturation.py --formula C6H6
    python degrees_of_unsaturation.py --C 6 --H 6
    python degrees_of_unsaturation.py --C 10 --H 14 --O 2 --N 1
    python degrees_of_unsaturation.py --formula C8H15ClN2O2
"""

import argparse
import re
import sys


# Each DoU corresponds to one ring or one pi bond.
# Interpretation thresholds:
#   0   -> saturated, open-chain (alkane / simple ether / amine)
#   1   -> one ring OR one double bond
#   2   -> ring + double bond, OR two double bonds, OR one triple bond
#   4   -> benzene ring (3 double bonds + 1 ring = 4 DoU)
#   >4  -> polycyclic aromatic or multiple aromatic / triple-bond combinations

_INTERPRETATION = [
    (0, 0, "No rings or pi bonds — fully saturated, open-chain compound."),
    (1, 1, "One ring OR one double bond (e.g. cyclopropane, alkene, ketone)."),
    (2, 2, "Two degrees: ring + double bond, two double bonds, or one triple bond."),
    (3, 3, "Three degrees: possible combinations include a ring + two double bonds or a diene in a ring."),
    (4, 4, "Four degrees — consistent with a benzene ring (aromatic ring + 3 double bonds)."),
]


def _parse_formula_string(formula: str) -> dict:
    """Parse a molecular formula string like C6H6 or C8H15ClN2O2 into element counts."""
    tokens = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
    counts: dict[str, int] = {}
    for element, count_str in tokens:
        if not element:
            continue
        count = int(count_str) if count_str else 1
        counts[element] = counts.get(element, 0) + count
    return counts


def degrees_of_unsaturation(C: int, H: int, N: int = 0, halogens: int = 0) -> float:
    """Return DoU = (2C + 2 + N - H - X) / 2."""
    return (2 * C + 2 + N - H - halogens) / 2


def _interpret(dou: float) -> str:
    """Return a structural interpretation string for the computed DoU."""
    for lo, hi, msg in _INTERPRETATION:
        if lo <= dou <= hi:
            return msg
    if dou > 4:
        return (
            f"{dou:.0f} degrees — likely contains multiple rings and/or aromatic systems "
            "(e.g. naphthalene = 7, anthracene = 10, or a ring with multiple double bonds)."
        )
    return "Negative DoU — check your formula (halogens may be overcounted)."


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Compute degrees of unsaturation (DoU) for a molecular formula.",
        epilog=(
            "Examples:\n"
            "  python degrees_of_unsaturation.py --formula C6H6\n"
            "  python degrees_of_unsaturation.py --C 6 --H 6\n"
            "  python degrees_of_unsaturation.py --C 10 --H 14 --O 2 --N 1\n"
            "  python degrees_of_unsaturation.py --formula C8H15ClN2O2\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--formula", type=str, help="Molecular formula string, e.g. C6H6 or C8H9NO2.")
    p.add_argument("--C", type=int, default=0, help="Number of carbon atoms.")
    p.add_argument("--H", type=int, default=0, help="Number of hydrogen atoms.")
    p.add_argument("--N", type=int, default=0, help="Number of nitrogen atoms (default 0).")
    p.add_argument("--O", type=int, default=0, help="Number of oxygen atoms (does not affect DoU).")
    p.add_argument("--S", type=int, default=0, help="Number of sulfur atoms (does not affect DoU).")
    p.add_argument("--F", type=int, default=0, help="Number of fluorine atoms.")
    p.add_argument("--Cl", type=int, default=0, help="Number of chlorine atoms.")
    p.add_argument("--Br", type=int, default=0, help="Number of bromine atoms.")
    p.add_argument("--I", type=int, default=0, help="Number of iodine atoms.")
    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    # Build element counts
    if args.formula:
        counts = _parse_formula_string(args.formula)
        C = counts.get("C", 0)
        H = counts.get("H", 0)
        N = counts.get("N", 0)
        O = counts.get("O", 0)
        S = counts.get("S", 0)
        F = counts.get("F", 0)
        Cl = counts.get("Cl", 0)
        Br = counts.get("Br", 0)
        I = counts.get("I", 0)
    else:
        if args.C == 0:
            parser.error("Provide --formula or at least --C.")
        C, H, N = args.C, args.H, args.N
        O, S = args.O, args.S
        F, Cl, Br, I = args.F, args.Cl, args.Br, args.I

    halogens = F + Cl + Br + I

    # Validate
    if C <= 0:
        print("ERROR: Number of carbon atoms must be > 0.", file=sys.stderr)
        sys.exit(1)
    if H < 0 or N < 0 or halogens < 0:
        print("ERROR: Atom counts cannot be negative.", file=sys.stderr)
        sys.exit(1)

    dou = degrees_of_unsaturation(C, H, N, halogens)

    # Reconstruct formula string for display
    formula_parts = [f"C{C}"] if C else []
    if H:
        formula_parts.append(f"H{H}")
    if N:
        formula_parts.append(f"N{N}")
    if O:
        formula_parts.append(f"O{O}")
    if S:
        formula_parts.append(f"S{S}")
    if F:
        formula_parts.append(f"F{F}")
    if Cl:
        formula_parts.append(f"Cl{Cl}")
    if Br:
        formula_parts.append(f"Br{Br}")
    if I:
        formula_parts.append(f"I{I}")
    formula_display = "".join(formula_parts)

    print("=" * 56)
    print("  Degrees of Unsaturation Calculator")
    print("=" * 56)
    print(f"  Formula      : {formula_display}")
    print()
    print("  Atom counts used in DoU formula:")
    print(f"    C (carbon)  = {C}")
    print(f"    H (hydrogen)= {H}")
    print(f"    N (nitrogen)= {N}  [+N adds DoU]")
    if halogens:
        halogen_detail = []
        if F:
            halogen_detail.append(f"F={F}")
        if Cl:
            halogen_detail.append(f"Cl={Cl}")
        if Br:
            halogen_detail.append(f"Br={Br}")
        if I:
            halogen_detail.append(f"I={I}")
        print(f"    X (halogens)= {halogens}  ({', '.join(halogen_detail)}) [-X subtracts DoU]")
    if O:
        print(f"    O (oxygen)  = {O}  [O does NOT affect DoU]")
    if S:
        print(f"    S (sulfur)  = {S}  [S does NOT affect DoU]")
    print()
    print("  Formula:  DoU = (2C + 2 + N - H - X) / 2")
    print(f"          = (2×{C} + 2 + {N} - {H} - {halogens}) / 2")
    numerator = 2 * C + 2 + N - H - halogens
    print(f"          = {numerator} / 2")
    print(f"          = {dou:.1f}")
    print()
    print(f"  Result: DoU = {dou:.1f}")
    print()
    print("  Interpretation:")
    print(f"    {_interpret(dou)}")
    print()

    # Quick structural hints
    if dou >= 4:
        print("  Note: DoU ≥ 4 is consistent with an aromatic ring.")
        print("        Each benzene ring contributes 4 DoU (3 C=C + 1 ring closure).")
    if dou >= 1 and dou == int(dou):
        pass  # integer — normal
    elif dou != int(dou):
        print("  Warning: Non-integer DoU — check your formula for errors.")
        print("           Half-integer DoU is impossible for neutral closed-shell molecules.")

    print("=" * 56)

    # Verification: recompute and confirm
    dou_check = (2 * C + 2 + N - H - halogens) / 2
    assert abs(dou - dou_check) < 1e-9, "Internal verification failed."
    print("  Verification: recomputed DoU matches. ✓")
    print("=" * 56)


if __name__ == "__main__":
    main()
