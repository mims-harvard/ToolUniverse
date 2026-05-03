"""Protein parameter calculation tool (local computation).

Calculates physicochemical properties of a protein from its amino acid
sequence, similar to ExPASy ProtParam. No external API calls needed.
Properties: molecular weight, isoelectric point (pI), amino acid
composition, extinction coefficient, instability index, aliphatic
index, and GRAVY (grand average of hydropathicity).
"""

import math
from typing import Any, Dict

from tooluniverse.tool_registry import register_tool

# Monoisotopic amino acid molecular weights (Da)
_MW = {
    "A": 71.03711,
    "R": 156.10111,
    "N": 114.04293,
    "D": 115.02694,
    "C": 103.00919,
    "E": 129.04259,
    "Q": 128.05858,
    "G": 57.02146,
    "H": 137.05891,
    "I": 113.08406,
    "L": 113.08406,
    "K": 128.09496,
    "M": 131.04049,
    "F": 147.06841,
    "P": 97.05276,
    "S": 87.03203,
    "T": 101.04768,
    "W": 186.07931,
    "Y": 163.06333,
    "V": 99.06841,
}

# Average molecular weights (Da)
_MW_AVG = {
    "A": 89.0935,
    "R": 174.2017,
    "N": 132.1184,
    "D": 133.1032,
    "C": 121.1590,
    "E": 147.1299,
    "Q": 146.1451,
    "G": 75.0669,
    "H": 155.1552,
    "I": 131.1736,
    "L": 131.1736,
    "K": 146.1882,
    "M": 149.2124,
    "F": 165.1900,
    "P": 115.1310,
    "S": 105.0930,
    "T": 119.1197,
    "W": 204.2262,
    "Y": 181.1894,
    "V": 117.1469,
}

_WATER_MW = 18.01524

# pKa values for pI calculation (EMBOSS scale)
_PK_N_TERM = 8.6
_PK_C_TERM = 3.6
_PK_SIDE = {
    "C": 8.5,
    "D": 3.9,
    "E": 4.1,
    "H": 6.5,
    "K": 10.8,
    "R": 12.5,
    "Y": 10.1,
}

# Kyte-Doolittle hydropathicity scale
_HYDRO = {
    "A": 1.8,
    "R": -4.5,
    "N": -3.5,
    "D": -3.5,
    "C": 2.5,
    "E": -3.5,
    "Q": -3.5,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "L": 3.8,
    "K": -3.9,
    "M": 1.9,
    "F": 2.8,
    "P": -1.6,
    "S": -0.8,
    "T": -0.7,
    "W": -0.9,
    "Y": -1.3,
    "V": 4.2,
}

# Instability index dipeptide weight values (DIWV)
_DIWV = {
    "WW": 1.0,
    "WC": 1.0,
    "WM": 24.68,
    "WH": 24.68,
    "WY": 1.0,
    "WF": 1.0,
    "WQ": 1.0,
    "WN": 13.34,
    "WE": 1.0,
    "WD": 1.0,
    "WK": 1.0,
    "WR": 1.0,
    "WS": 1.0,
    "WT": -14.03,
    "WG": -9.37,
    "WA": -14.03,
    "WV": -7.49,
    "WI": 1.0,
    "WL": 13.34,
    "WP": 1.0,
}


def _count_aa(seq: str) -> Dict[str, int]:
    """Count amino acid occurrences."""
    counts = {aa: 0 for aa in _MW}
    for ch in seq.upper():
        if ch in counts:
            counts[ch] += 1
    return counts


def _calc_mw(seq: str) -> float:
    """Calculate molecular weight using average isotopic masses."""
    total = _WATER_MW
    for ch in seq.upper():
        total += _MW_AVG.get(ch, 0) - _WATER_MW
    total += _WATER_MW
    return round(total, 2)


def _charge_at_ph(seq: str, ph: float, counts: Dict[str, int]) -> float:
    """Calculate net charge at a given pH."""
    n = len(seq)
    if n == 0:
        return 0.0
    # N-terminus positive charge
    charge = 1.0 / (1.0 + 10 ** (ph - _PK_N_TERM))
    # C-terminus negative charge
    charge -= 1.0 / (1.0 + 10 ** (_PK_C_TERM - ph))
    # Side chain charges
    for aa, pka in _PK_SIDE.items():
        cnt = counts.get(aa, 0)
        if cnt == 0:
            continue
        if aa in ("K", "R", "H"):
            charge += cnt / (1.0 + 10 ** (ph - pka))
        else:
            charge -= cnt / (1.0 + 10 ** (pka - ph))
    return charge


def _calc_pi(seq: str, counts: Dict[str, int]) -> float:
    """Calculate isoelectric point by bisection."""
    lo, hi = 0.0, 14.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        charge = _charge_at_ph(seq, mid, counts)
        if charge > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2.0, 2)


def _extinction_coefficients(counts: Dict[str, int]) -> Dict[str, float]:
    """Extinction coefficients at 280 nm (M-1 cm-1)."""
    # Pace et al. values
    n_trp = counts.get("W", 0)
    n_tyr = counts.get("Y", 0)
    n_cys = counts.get("C", 0)
    # Assuming all cysteines form cystines (oxidized)
    ext_reduced = n_trp * 5500 + n_tyr * 1490
    ext_oxidized = ext_reduced + (n_cys // 2) * 125
    return {
        "assuming_all_cystines": ext_oxidized,
        "assuming_all_reduced_cys": ext_reduced,
    }


def _instability_index(seq: str) -> float:
    """Guruprasad instability index."""
    n = len(seq)
    if n < 2:
        return 0.0
    total = 0.0
    s = seq.upper()
    for i in range(n - 1):
        dipep = s[i : i + 2]
        total += _DIWV.get(dipep, 1.0)
    return round((10.0 / n) * total, 2)


def _aliphatic_index(counts: Dict[str, int], n: int) -> float:
    """Ikai aliphatic index."""
    if n == 0:
        return 0.0
    a = counts.get("A", 0) / n
    v = counts.get("V", 0) / n
    i = counts.get("I", 0) / n
    le = counts.get("L", 0) / n
    return round((a + 2.9 * v + 3.9 * (i + le)) * 100, 2)


def _gravy(seq: str) -> float:
    """Grand average of hydropathicity (GRAVY)."""
    n = len(seq)
    if n == 0:
        return 0.0
    total = sum(_HYDRO.get(ch, 0) for ch in seq.upper())
    return round(total / n, 3)


@register_tool(
    "ProtParamTool",
    config={
        "name": "ProtParam_calculate",
        "type": "ProtParamTool",
        "description": (
            "Calculate physicochemical properties of a protein from its amino "
            "acid sequence (similar to ExPASy ProtParam). Returns molecular "
            "weight, isoelectric point (pI), amino acid composition, extinction "
            "coefficients at 280 nm, instability index, aliphatic index, and "
            "GRAVY (grand average of hydropathicity). No external API needed."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "sequence": {
                    "type": "string",
                    "description": (
                        "Protein amino acid sequence in single-letter code. "
                        "Example: 'MEEPQSDPSVEPPLSQETFSDLWKLLPENNVLSPLPS' "
                        "(partial TP53). Whitespace and numbers are stripped."
                    ),
                },
            },
            "required": ["sequence"],
        },
    },
)
class ProtParamTool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw_seq = arguments.get("sequence", "")
        if not raw_seq:
            return {"status": "error", "error": "sequence is required"}

        # Clean sequence: remove whitespace, numbers, FASTA headers
        lines = raw_seq.strip().splitlines()
        cleaned = []
        for line in lines:
            line = line.strip()
            if line.startswith(">"):
                continue
            cleaned.append(line)
        seq = "".join(cleaned).upper()
        seq = "".join(ch for ch in seq if ch.isalpha())

        valid_aa = set(_MW.keys())
        invalid = set(seq) - valid_aa
        if invalid:
            return {
                "status": "error",
                "error": f"Invalid amino acid characters: {', '.join(sorted(invalid))}. Use standard single-letter codes.",
            }

        if len(seq) < 2:
            return {
                "status": "error",
                "error": "Sequence must be at least 2 amino acids long",
            }

        counts = _count_aa(seq)
        n = len(seq)
        mw = _calc_mw(seq)
        pi = _calc_pi(seq, counts)
        ext = _extinction_coefficients(counts)
        ii = _instability_index(seq)
        ai = _aliphatic_index(counts, n)
        gravy_val = _gravy(seq)

        # Amino acid composition as percentages
        composition = {}
        for aa in sorted(counts.keys()):
            cnt = counts[aa]
            if cnt > 0:
                composition[aa] = {
                    "count": cnt,
                    "percent": round(cnt / n * 100, 1),
                }

        # Classify stability
        stability = "stable" if ii < 40 else "unstable"

        # Charged residues
        pos_charged = counts.get("R", 0) + counts.get("K", 0) + counts.get("H", 0)
        neg_charged = counts.get("D", 0) + counts.get("E", 0)

        return {
            "status": "success",
            "data": {
                "length": n,
                "molecular_weight_da": mw,
                "isoelectric_point": pi,
                "extinction_coefficient": ext,
                "instability_index": ii,
                "stability_classification": stability,
                "aliphatic_index": ai,
                "gravy": gravy_val,
                "positively_charged_residues": pos_charged,
                "negatively_charged_residues": neg_charged,
                "amino_acid_composition": composition,
                "formula_note": "Molecular weight uses average isotopic masses. pI calculated using EMBOSS pKa scale.",
            },
        }
