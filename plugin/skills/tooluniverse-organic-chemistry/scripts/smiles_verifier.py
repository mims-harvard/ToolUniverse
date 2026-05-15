#!/usr/bin/env python3
"""
SMILES Verifier — parse a SMILES string (no RDKit) and compute:
  - Molecular weight
  - Heavy atom count (non-H)
  - Valence electron count (sum of valence electrons per atom)
  - Total atom count (including implicit H)
  - Formal charge

Usage:
  python smiles_verifier.py --smiles "CC(C)(C(=N)N)N=NC(C)(C)C(=N)N"
  python smiles_verifier.py --smiles "CC(C)(C(=N)N)N=NC(C)(C)C(=N)N" --mw 198.15 --heavy_atoms 14 --valence_electrons 80
  python smiles_verifier.py --smiles "C1COCCN1CCOCCN2CCOCC2" --heavy_atoms 17 --valence_electrons 102
"""

import argparse
import re
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ATOMIC_WEIGHTS = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "S": 32.06,
    "P": 30.974,
    "F": 18.998,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
}

VALENCE_ELECTRONS = {
    "H": 1,
    "C": 4,
    "N": 5,
    "O": 6,
    "S": 6,
    "P": 5,
    "F": 7,
    "Cl": 7,
    "Br": 7,
    "I": 7,
}

# Standard valences used for implicit-H calculation (organic subset).
# For atoms in the organic subset (outside brackets), SMILES assumes the
# lowest "normal" valence that is >= the number of explicit bonds.
STANDARD_VALENCES = {
    "C": [4],
    "N": [3, 5],
    "O": [2],
    "S": [2, 4, 6],
    "P": [3, 5],
    "F": [1],
    "Cl": [1],
    "Br": [1],
    "I": [1],
}

# Two-letter organic-subset symbols that can appear WITHOUT brackets
TWO_LETTER_ORGANIC = {"Cl", "Br"}


# ---------------------------------------------------------------------------
# SMILES parser
# ---------------------------------------------------------------------------


def parse_smiles(smiles: str) -> dict:
    """Parse a SMILES string and return atom/bond information.

    Returns a dict with keys:
      atoms:  list of dicts, each with 'symbol', 'charge', 'hcount' (explicit),
              'in_bracket', 'aromatic'
      bonds:  list of (i, j, order) tuples
    """
    atoms = []
    bonds = []
    ring_opens = {}  # digit -> atom index
    stack = []  # branch stack of atom indices
    prev_atom = None
    pending_bond_order = 1

    i = 0
    n = len(smiles)

    while i < n:
        ch = smiles[i]

        # --- branch open/close ---
        if ch == "(":
            stack.append(prev_atom)
            i += 1
            continue
        if ch == ")":
            prev_atom = stack.pop()
            i += 1
            continue

        # --- bond symbols ---
        if ch == "=":
            pending_bond_order = 2
            i += 1
            continue
        if ch == "#":
            pending_bond_order = 3
            i += 1
            continue
        if ch == "-":
            pending_bond_order = 1
            i += 1
            continue
        if ch == ":":
            # aromatic bond indicator — treat as 1.5 but we model as 1
            # for implicit H purposes aromatic is handled via lowercase
            pending_bond_order = 1  # simplified
            i += 1
            continue
        if ch in "/\\":
            # cis/trans markers — ignore
            i += 1
            continue
        if ch == ".":
            # disconnected fragments
            prev_atom = None
            i += 1
            continue

        # --- bracket atom [  ] ---
        if ch == "[":
            j = smiles.index("]", i)
            bracket_content = smiles[i + 1 : j]
            atom_info = _parse_bracket(bracket_content)
            atom_idx = len(atoms)
            atoms.append(atom_info)
            if prev_atom is not None:
                bonds.append((prev_atom, atom_idx, pending_bond_order))
                pending_bond_order = 1
            prev_atom = atom_idx
            i = j + 1
            # Handle ring digits right after bracket
            i = _consume_ring_digits(
                smiles, i, n, atom_idx, ring_opens, bonds, pending_bond_order
            )
            pending_bond_order = 1
            continue

        # --- organic subset atom (no brackets) ---
        symbol, consumed, aromatic = _read_organic_atom(smiles, i)
        if symbol is not None:
            atom_idx = len(atoms)
            atoms.append(
                {
                    "symbol": symbol,
                    "charge": 0,
                    "hcount": None,  # implicit — will be computed later
                    "in_bracket": False,
                    "aromatic": aromatic,
                }
            )
            if prev_atom is not None:
                bonds.append((prev_atom, atom_idx, pending_bond_order))
                pending_bond_order = 1
            prev_atom = atom_idx
            i += consumed
            # Handle ring digits right after atom
            i = _consume_ring_digits(
                smiles, i, n, atom_idx, ring_opens, bonds, pending_bond_order
            )
            pending_bond_order = 1
            continue

        # --- ring digit ---
        if ch == "%" or ch.isdigit():
            # standalone ring digit (should have been consumed; fallback)
            i = _consume_ring_digits(
                smiles, i, n, prev_atom, ring_opens, bonds, pending_bond_order
            )
            pending_bond_order = 1
            continue

        # skip unknown
        i += 1

    # --- compute implicit H for organic-subset atoms ---
    _compute_implicit_h(atoms, bonds)

    return {"atoms": atoms, "bonds": bonds}


def _parse_bracket(content: str) -> dict:
    """Parse content inside [...] and return atom info dict."""
    pos = 0
    n = len(content)

    # skip isotope
    while pos < n and content[pos].isdigit():
        pos += 1

    # read symbol
    aromatic = False
    if pos < n and content[pos].islower():
        aromatic = True
        symbol_start = pos
        pos += 1
        symbol = content[symbol_start:pos].upper()
    elif pos < n and content[pos].isupper():
        symbol_start = pos
        pos += 1
        if pos < n and content[pos].islower():
            pos += 1
        symbol = content[symbol_start:pos]
    else:
        symbol = "C"

    # read chirality (@, @@)
    while pos < n and content[pos] == "@":
        pos += 1

    # read H count
    hcount = 0
    if pos < n and content[pos] == "H":
        pos += 1
        if pos < n and content[pos].isdigit():
            hcount = int(content[pos])
            pos += 1
        else:
            hcount = 1

    # read charge
    charge = 0
    if pos < n and content[pos] in "+-":
        sign = 1 if content[pos] == "+" else -1
        pos += 1
        if pos < n and content[pos].isdigit():
            charge = sign * int(content[pos])
            pos += 1
        else:
            # count consecutive +/-
            charge = sign
            while pos < n and content[pos] == ("+" if sign > 0 else "-"):
                charge += sign
                pos += 1

    return {
        "symbol": symbol,
        "charge": charge,
        "hcount": hcount,
        "in_bracket": True,
        "aromatic": aromatic,
    }


def _read_organic_atom(smiles: str, pos: int) -> tuple:
    """Read an organic-subset atom at position pos.

    Returns (symbol, chars_consumed, is_aromatic) or (None, 0, False).
    """
    n = len(smiles)
    ch = smiles[pos]

    # aromatic atoms (lowercase)
    if ch in "cnospb":
        return ch.upper(), 1, True

    # two-letter atoms (Cl, Br)
    if pos + 1 < n:
        two = smiles[pos : pos + 2]
        if two in TWO_LETTER_ORGANIC:
            return two, 2, False

    # single-letter atoms
    if ch in "BCNOSPFI":
        return ch, 1, False

    return None, 0, False


def _consume_ring_digits(
    smiles: str, pos: int, n: int, atom_idx, ring_opens, bonds, default_order
) -> int:
    """Consume ring-closure digits (or %NN) starting at pos. Returns new pos."""
    while pos < n:
        if smiles[pos] == "%":
            if pos + 2 < n and smiles[pos + 1 : pos + 3].isdigit():
                rnum = int(smiles[pos + 1 : pos + 3])
                pos += 3
            else:
                break
        elif smiles[pos].isdigit():
            rnum = int(smiles[pos])
            pos += 1
        else:
            break

        if rnum in ring_opens:
            other = ring_opens.pop(rnum)
            bonds.append((other, atom_idx, default_order))
        else:
            ring_opens[rnum] = atom_idx

    return pos


def _compute_implicit_h(atoms: list, bonds: list) -> None:
    """Fill in implicit H counts for organic-subset atoms (hcount=None)."""
    # Compute bond-order sum per atom
    bond_order_sum = [0] * len(atoms)
    for i, j, order in bonds:
        bond_order_sum[i] += order
        bond_order_sum[j] += order

    for idx, atom in enumerate(atoms):
        if atom["hcount"] is not None:
            # bracket atom — explicit H already set
            continue

        sym = atom["symbol"]
        if sym not in STANDARD_VALENCES:
            atom["hcount"] = 0
            continue

        bo = bond_order_sum[idx]
        # For aromatic atoms, add 1 to bond order (the "missing" aromatic bond
        # contribution from Kekulization simplified model)
        if atom["aromatic"]:
            bo += 1

        # Find the lowest standard valence >= bo
        valences = STANDARD_VALENCES[sym]
        chosen = None
        for v in sorted(valences):
            if v >= bo:
                chosen = v
                break
        if chosen is None:
            chosen = max(valences)

        atom["hcount"] = max(0, chosen - bo)


# ---------------------------------------------------------------------------
# Molecular property calculations
# ---------------------------------------------------------------------------


def compute_properties(parsed: dict) -> dict:
    """Compute molecular properties from parsed SMILES."""
    atoms = parsed["atoms"]

    # Count atoms
    heavy_counts = {}
    h_count = 0

    for atom in atoms:
        sym = atom["symbol"]
        heavy_counts[sym] = heavy_counts.get(sym, 0) + 1
        h_count += atom.get("hcount", 0)

    # Molecular weight
    mw = 0.0
    for sym, count in heavy_counts.items():
        mw += ATOMIC_WEIGHTS.get(sym, 0.0) * count
    mw += ATOMIC_WEIGHTS["H"] * h_count

    # Heavy atom count
    heavy_atom_count = sum(heavy_counts.values())

    # Total atom count
    total_atoms = heavy_atom_count + h_count

    # Valence electrons (sum over ALL atoms including H)
    ve = 0
    for sym, count in heavy_counts.items():
        ve += VALENCE_ELECTRONS.get(sym, 0) * count
    ve += VALENCE_ELECTRONS["H"] * h_count

    # Formal charge
    formal_charge = sum(atom["charge"] for atom in atoms)

    # Adjust valence electrons for formal charge:
    # Positive charge means electrons removed, negative means added
    ve -= formal_charge

    # Element breakdown
    formula = dict(heavy_counts)
    if h_count > 0:
        formula["H"] = h_count

    return {
        "molecular_weight": round(mw, 3),
        "heavy_atom_count": heavy_atom_count,
        "total_atom_count": total_atoms,
        "valence_electrons": ve,
        "formal_charge": formal_charge,
        "formula": formula,
        "h_count": h_count,
    }


# ---------------------------------------------------------------------------
# Constraint checking
# ---------------------------------------------------------------------------


def check_constraints(props: dict, constraints: dict) -> list:
    """Check properties against constraints. Returns list of result dicts."""
    results = []
    mapping = {
        "mw": ("molecular_weight", "Molecular Weight"),
        "heavy_atoms": ("heavy_atom_count", "Heavy Atom Count"),
        "valence_electrons": ("valence_electrons", "Valence Electrons"),
        "total_atoms": ("total_atom_count", "Total Atom Count"),
        "formal_charge": ("formal_charge", "Formal Charge"),
    }

    for key, (prop_key, label) in mapping.items():
        if key in constraints and constraints[key] is not None:
            expected = constraints[key]
            actual = props[prop_key]
            if key == "mw":
                match = abs(actual - expected) < 0.5
                results.append(
                    {
                        "property": label,
                        "expected": expected,
                        "actual": actual,
                        "match": match,
                        "note": f"delta={abs(actual - expected):.3f}",
                    }
                )
            else:
                match = actual == expected
                results.append(
                    {
                        "property": label,
                        "expected": expected,
                        "actual": actual,
                        "match": match,
                    }
                )
    return results


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------


def format_formula(formula: dict) -> str:
    """Format a formula dict into a string like C10H20N4."""
    # Standard Hill order: C first, H second, then alphabetical
    parts = []
    for sym in ["C", "H"]:
        if sym in formula:
            parts.append(f"{sym}{formula[sym] if formula[sym] > 1 else ''}")
    for sym in sorted(formula.keys()):
        if sym not in ("C", "H"):
            parts.append(f"{sym}{formula[sym] if formula[sym] > 1 else ''}")
    return "".join(parts)


def print_results(smiles: str, props: dict, checks: list) -> None:
    print(f"\nSMILES: {smiles}")
    print(f"Formula: {format_formula(props['formula'])}")
    print(f"  Molecular Weight:    {props['molecular_weight']:.3f}")
    print(f"  Heavy Atoms:         {props['heavy_atom_count']}")
    print(f"  Total Atoms:         {props['total_atom_count']}")
    print(f"  Valence Electrons:   {props['valence_electrons']}")
    print(f"  Formal Charge:       {props['formal_charge']}")
    print(f"  Implicit H count:    {props['h_count']}")

    if checks:
        print("\nConstraint checks:")
        all_pass = True
        for c in checks:
            status = "PASS" if c["match"] else "FAIL"
            if not c["match"]:
                all_pass = False
            note = f"  ({c['note']})" if "note" in c else ""
            print(
                f"  {c['property']}: expected={c['expected']}, actual={c['actual']} -> {status}{note}"
            )
        print(f"\nOverall: {'ALL CONSTRAINTS MET' if all_pass else 'CONSTRAINTS NOT MET'}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Verify SMILES molecular properties (no RDKit required)"
    )
    parser.add_argument("--smiles", required=True, help="SMILES string to verify")
    parser.add_argument("--mw", type=float, default=None, help="Expected MW")
    parser.add_argument(
        "--heavy_atoms", type=int, default=None, help="Expected heavy atom count"
    )
    parser.add_argument(
        "--valence_electrons",
        type=int,
        default=None,
        help="Expected valence electron count",
    )
    parser.add_argument(
        "--total_atoms", type=int, default=None, help="Expected total atom count"
    )
    parser.add_argument(
        "--formal_charge", type=int, default=None, help="Expected formal charge"
    )
    args = parser.parse_args()

    parsed = parse_smiles(args.smiles)
    props = compute_properties(parsed)

    constraints = {
        "mw": args.mw,
        "heavy_atoms": args.heavy_atoms,
        "valence_electrons": args.valence_electrons,
        "total_atoms": args.total_atoms,
        "formal_charge": args.formal_charge,
    }

    checks = check_constraints(props, constraints)
    print_results(args.smiles, props, checks)


if __name__ == "__main__":
    main()
