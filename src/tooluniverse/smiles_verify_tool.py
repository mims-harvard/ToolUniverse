"""
SMILES Verifier Tool

Parse a SMILES string without RDKit and compute molecular weight, heavy atom
count, ring count, valence electrons, formal charge, and molecular formula.
Optionally verify against expected constraints.

No external dependencies. Pure Python with stdlib re only.
"""

import re
from typing import Any, Dict, List
from .base_tool import BaseTool
from .tool_registry import register_tool


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

TWO_LETTER_ORGANIC = {"Cl", "Br"}


# ---------------------------------------------------------------------------
# SMILES parser
# ---------------------------------------------------------------------------


def _parse_smiles(smiles: str) -> Dict[str, Any]:
    """Parse SMILES and return atoms/bonds."""
    atoms: List[Dict] = []
    bonds: List[tuple] = []
    ring_opens: Dict[int, int] = {}
    stack: List[int] = []
    prev_atom = None
    pending_order = 1
    ring_bond_count = 0

    i = 0
    n = len(smiles)

    while i < n:
        ch = smiles[i]

        if ch == "(":
            stack.append(prev_atom)
            i += 1
            continue
        if ch == ")":
            prev_atom = stack.pop()
            i += 1
            continue
        if ch == "=":
            pending_order = 2
            i += 1
            continue
        if ch == "#":
            pending_order = 3
            i += 1
            continue
        if ch == "-":
            pending_order = 1
            i += 1
            continue
        if ch == ":":
            pending_order = 1
            i += 1
            continue
        if ch in "/\\":
            i += 1
            continue
        if ch == ".":
            prev_atom = None
            i += 1
            continue

        # Bracket atom
        if ch == "[":
            j = smiles.index("]", i)
            atom_info = _parse_bracket(smiles[i + 1 : j])
            atom_idx = len(atoms)
            atoms.append(atom_info)
            if prev_atom is not None:
                bonds.append((prev_atom, atom_idx, pending_order))
                pending_order = 1
            prev_atom = atom_idx
            i = j + 1
            i, rc = _consume_rings(
                smiles, i, n, atom_idx, ring_opens, bonds, pending_order
            )
            ring_bond_count += rc
            pending_order = 1
            continue

        # Organic subset atom
        symbol, consumed, aromatic = _read_organic(smiles, i)
        if symbol is not None:
            atom_idx = len(atoms)
            atoms.append(
                {
                    "symbol": symbol,
                    "charge": 0,
                    "hcount": None,
                    "in_bracket": False,
                    "aromatic": aromatic,
                }
            )
            if prev_atom is not None:
                bonds.append((prev_atom, atom_idx, pending_order))
                pending_order = 1
            prev_atom = atom_idx
            i += consumed
            i, rc = _consume_rings(
                smiles, i, n, atom_idx, ring_opens, bonds, pending_order
            )
            ring_bond_count += rc
            pending_order = 1
            continue

        if ch == "%" or ch.isdigit():
            i, rc = _consume_rings(
                smiles, i, n, prev_atom, ring_opens, bonds, pending_order
            )
            ring_bond_count += rc
            pending_order = 1
            continue

        i += 1

    _compute_implicit_h(atoms, bonds)
    return {"atoms": atoms, "bonds": bonds, "ring_closures": ring_bond_count}


def _parse_bracket(content: str) -> Dict:
    pos = 0
    n = len(content)

    while pos < n and content[pos].isdigit():
        pos += 1

    aromatic = False
    if pos < n and content[pos].islower():
        aromatic = True
        symbol = content[pos].upper()
        pos += 1
    elif pos < n and content[pos].isupper():
        start = pos
        pos += 1
        if pos < n and content[pos].islower():
            pos += 1
        symbol = content[start:pos]
    else:
        symbol = "C"

    while pos < n and content[pos] == "@":
        pos += 1

    hcount = 0
    if pos < n and content[pos] == "H":
        pos += 1
        if pos < n and content[pos].isdigit():
            hcount = int(content[pos])
            pos += 1
        else:
            hcount = 1

    charge = 0
    if pos < n and content[pos] in "+-":
        sign = 1 if content[pos] == "+" else -1
        pos += 1
        if pos < n and content[pos].isdigit():
            charge = sign * int(content[pos])
            pos += 1
        else:
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


def _read_organic(smiles: str, pos: int) -> tuple:
    n = len(smiles)
    ch = smiles[pos]

    if ch in "cnospb":
        return ch.upper(), 1, True

    if pos + 1 < n:
        two = smiles[pos : pos + 2]
        if two in TWO_LETTER_ORGANIC:
            return two, 2, False

    if ch in "BCNOSPFI":
        return ch, 1, False

    return None, 0, False


def _consume_rings(
    smiles: str, pos: int, n: int, atom_idx, ring_opens, bonds, default_order
) -> tuple:
    """Consume ring digits, return (new_pos, ring_closures_count)."""
    closures = 0
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
            closures += 1
        else:
            ring_opens[rnum] = atom_idx
    return pos, closures


def _compute_implicit_h(atoms: list, bonds: list) -> None:
    bond_order_sum = [0] * len(atoms)
    for i, j, order in bonds:
        bond_order_sum[i] += order
        bond_order_sum[j] += order

    for idx, atom in enumerate(atoms):
        if atom["hcount"] is not None:
            continue

        sym = atom["symbol"]
        if sym not in STANDARD_VALENCES:
            atom["hcount"] = 0
            continue

        bo = bond_order_sum[idx]
        if atom["aromatic"]:
            bo += 1

        valences = STANDARD_VALENCES[sym]
        chosen = None
        for v in sorted(valences):
            if v >= bo:
                chosen = v
                break
        if chosen is None:
            chosen = max(valences)

        atom["hcount"] = max(0, chosen - bo)


def _compute_properties(parsed: Dict) -> Dict:
    atoms = parsed["atoms"]
    heavy_counts: Dict[str, int] = {}
    h_count = 0

    for atom in atoms:
        sym = atom["symbol"]
        heavy_counts[sym] = heavy_counts.get(sym, 0) + 1
        h_count += atom.get("hcount", 0)

    mw = sum(
        ATOMIC_WEIGHTS.get(sym, 0.0) * count for sym, count in heavy_counts.items()
    )
    mw += ATOMIC_WEIGHTS["H"] * h_count

    heavy_atom_count = sum(heavy_counts.values())
    total_atoms = heavy_atom_count + h_count

    ve = sum(
        VALENCE_ELECTRONS.get(sym, 0) * count for sym, count in heavy_counts.items()
    )
    ve += VALENCE_ELECTRONS["H"] * h_count

    formal_charge = sum(atom["charge"] for atom in atoms)
    ve -= formal_charge

    formula = dict(heavy_counts)
    if h_count > 0:
        formula["H"] = h_count

    ring_count = parsed.get("ring_closures", 0)

    # Degrees of unsaturation for carbon-containing molecules
    dou = None
    if "C" in heavy_counts:
        C = heavy_counts.get("C", 0)
        H = h_count
        N = heavy_counts.get("N", 0)
        halogens = sum(heavy_counts.get(x, 0) for x in ("F", "Cl", "Br", "I"))
        dou = (2 * C + 2 + N - H - halogens) / 2

    return {
        "molecular_weight": round(mw, 3),
        "heavy_atom_count": heavy_atom_count,
        "total_atom_count": total_atoms,
        "valence_electrons": ve,
        "formal_charge": formal_charge,
        "formula": formula,
        "h_count": h_count,
        "ring_count": ring_count,
        "degrees_of_unsaturation": dou,
    }


def _format_formula(formula: Dict[str, int]) -> str:
    parts = []
    for sym in ["C", "H"]:
        if sym in formula:
            parts.append(f"{sym}{formula[sym] if formula[sym] > 1 else ''}")
    for sym in sorted(formula.keys()):
        if sym not in ("C", "H"):
            parts.append(f"{sym}{formula[sym] if formula[sym] > 1 else ''}")
    return "".join(parts)


@register_tool("SMILESVerifyTool")
class SMILESVerifyTool(BaseTool):
    """Parse SMILES and compute/verify molecular properties without RDKit."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        smiles = arguments.get("smiles")
        if not smiles:
            return {"status": "error", "error": "Missing required parameter: smiles"}

        try:
            parsed = _parse_smiles(smiles)
            props = _compute_properties(parsed)
        except Exception as e:
            return {"status": "error", "error": f"SMILES parsing failed: {str(e)}"}

        formula_str = _format_formula(props["formula"])

        data = {
            "smiles": smiles,
            "molecular_formula": formula_str,
            "molecular_weight": props["molecular_weight"],
            "heavy_atom_count": props["heavy_atom_count"],
            "total_atom_count": props["total_atom_count"],
            "valence_electrons": props["valence_electrons"],
            "formal_charge": props["formal_charge"],
            "h_count": props["h_count"],
            "ring_count": props["ring_count"],
            "degrees_of_unsaturation": props["degrees_of_unsaturation"],
        }

        # Check constraints if provided
        checks = []
        constraint_map = {
            "expected_mw": ("molecular_weight", "Molecular Weight", True),
            "expected_heavy_atoms": ("heavy_atom_count", "Heavy Atom Count", False),
            "expected_valence_electrons": (
                "valence_electrons",
                "Valence Electrons",
                False,
            ),
            "expected_formula": ("molecular_formula", "Molecular Formula", False),
        }

        for param_name, (prop_key, label, is_float) in constraint_map.items():
            expected = arguments.get(param_name)
            if expected is not None:
                actual = data[prop_key]
                if is_float:
                    match = abs(actual - expected) < 0.5
                elif isinstance(expected, str):
                    match = actual == expected
                else:
                    match = actual == expected
                checks.append(
                    {
                        "property": label,
                        "expected": expected,
                        "actual": actual,
                        "match": match,
                    }
                )

        if checks:
            data["constraint_checks"] = checks
            data["all_constraints_met"] = all(c["match"] for c in checks)

        return {"status": "success", "data": data}
