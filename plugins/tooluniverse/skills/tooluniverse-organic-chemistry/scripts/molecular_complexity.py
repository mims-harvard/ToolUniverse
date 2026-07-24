#!/usr/bin/env python3
"""
Böttcher Molecular Complexity (Cm) calculator.

Cm = sum over all atoms of: (n_i * log2(n_i)) - (N * log2(N))
where n_i = number of atoms of element i, N = total atoms.

Actually, the standard Böttcher complexity is:
Cm = N * log2(N) - sum(n_i * log2(n_i))
where N = total non-hydrogen atoms, n_i = count of each element type.

But the most common version used in cheminformatics is based on the
molecular graph complexity considering bonds, rings, and symmetry.

For the Bertz/Böttcher complexity:
  C_m = 2 * |E| * log2(|E|) - sum(e_k * log2(e_k)) + ...

This script implements the basic atom-type entropy-based complexity.

Usage:
  python molecular_complexity.py --formula "C5H9ClO"
  python molecular_complexity.py --smiles "OC(=O)C1CCCCC1"  # requires no external deps for formula
"""

import argparse
import math
import re
import sys


def parse_formula(formula: str) -> dict:
    """Parse molecular formula like C6H12O6 into element counts."""
    pattern = r'([A-Z][a-z]?)(\d*)'
    elements = {}
    for match in re.finditer(pattern, formula):
        elem = match.group(1)
        count = int(match.group(2)) if match.group(2) else 1
        if elem:
            elements[elem] = elements.get(elem, 0) + count
    return elements


def bottcher_complexity(elements: dict, include_h: bool = False) -> float:
    """
    Calculate Böttcher molecular complexity.

    Standard formula (atom-type entropy):
    Cm = N * log2(N) - sum(n_i * log2(n_i))

    where N = total atoms, n_i = count of element i.

    Args:
        elements: dict of element -> count
        include_h: whether to include hydrogen atoms (default: False for heavy-atom only)
    """
    if not include_h:
        elements = {k: v for k, v in elements.items() if k != 'H'}

    N = sum(elements.values())
    if N <= 1:
        return 0.0

    # N * log2(N)
    total_term = N * math.log2(N)

    # sum(n_i * log2(n_i))
    element_term = sum(n * math.log2(n) for n in elements.values() if n > 0)

    return total_term - element_term


def bertz_complexity(elements: dict, n_bonds: int = 0, n_rings: int = 0) -> float:
    """
    Calculate Bertz complexity (extended Böttcher).

    C = C_atoms + C_bonds + C_rings
    where:
      C_atoms = 2*N*log2(N) - sum(2*n_i*log2(n_i))  [atom-type contribution]
      C_bonds = 2*B*log2(B) - sum(2*b_j*log2(b_j))  [bond-type contribution]
      C_rings = ring contribution

    This is a simplified version. For full Bertz complexity, bond types
    (single, double, triple, aromatic) need to be counted.
    """
    # Atom contribution
    c_atoms = bottcher_complexity(elements, include_h=False)

    # Bond contribution (if provided)
    c_bonds = 0.0
    if n_bonds > 0:
        c_bonds = n_bonds * math.log2(n_bonds) if n_bonds > 1 else 0

    # Ring contribution
    c_rings = n_rings * math.log2(n_rings) if n_rings > 1 else (0 if n_rings == 0 else 0)

    return c_atoms + c_bonds + c_rings


def main():
    parser = argparse.ArgumentParser(
        description="Calculate Böttcher Molecular Complexity from molecular formula."
    )
    parser.add_argument("--formula", help="Molecular formula (e.g., C6H12O6)")
    parser.add_argument("--include-h", action="store_true",
                       help="Include hydrogen in complexity calculation")
    parser.add_argument("--bonds", type=int, default=0,
                       help="Number of bonds (for Bertz complexity)")
    parser.add_argument("--rings", type=int, default=0,
                       help="Number of rings (for Bertz complexity)")

    args = parser.parse_args()

    if not args.formula:
        print("Error: --formula is required")
        print("Usage: python molecular_complexity.py --formula C5H9ClO")
        sys.exit(1)

    elements = parse_formula(args.formula)

    print(f"Formula: {args.formula}")
    print(f"Elements: {elements}")

    N_heavy = sum(v for k, v in elements.items() if k != 'H')
    N_total = sum(elements.values())
    print(f"Heavy atoms: {N_heavy}")
    print(f"Total atoms: {N_total}")

    # Standard Böttcher (heavy atoms only)
    cm_heavy = bottcher_complexity(elements, include_h=False)
    print(f"\nBöttcher Complexity (heavy atoms): {cm_heavy:.2f}")

    if args.include_h:
        cm_all = bottcher_complexity(elements, include_h=True)
        print(f"Böttcher Complexity (all atoms):   {cm_all:.2f}")

    if args.bonds > 0 or args.rings > 0:
        bertz = bertz_complexity(elements, args.bonds, args.rings)
        print(f"\nBertz Complexity: {bertz:.2f}")
        print(f"  (atom contribution: {bottcher_complexity(elements, False):.2f}, "
              f"bond contribution: ~{args.bonds * math.log2(args.bonds) if args.bonds > 1 else 0:.2f}, "
              f"ring contribution: ~{args.rings * math.log2(args.rings) if args.rings > 1 else 0:.2f})")


if __name__ == "__main__":
    main()
