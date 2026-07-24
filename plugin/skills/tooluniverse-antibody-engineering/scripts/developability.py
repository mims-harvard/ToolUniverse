#!/usr/bin/env python3
"""Sequence-based antibody developability flags (aggregation, charge, hydrophobicity).

The antibody-engineering workflow calls several `predict_*` helpers that were
never defined. This script implements the parts that are legitimately computable
from sequence alone, using published methods, and is explicit about what it
does NOT cover.

Implemented (real, citable):
- Aggregation-prone regions via AGGRESCAN (Conchillo-Sole et al. 2007): per-residue
  intrinsic aggregation propensity (a3v), window-smoothed (a4v), with hot-spot
  detection. Higher = more aggregation-prone.
- Isoelectric point (pI) via Henderson-Hasselbalch (EMBOSS pKa set).
- Surface-hydrophobic patches via windowed Kyte-Doolittle.

NOT computable from sequence alone (do NOT fabricate these — use external tools):
- Binding ddG / affinity maturation -> needs a structure + FoldX, Rosetta Flex
  ddG, or an ML interface predictor (mutate the modeled Fv:antigen complex).
- Thermal stability (Tm/Tonset) and expression titer -> sequence->Tm/titer ML
  predictors (e.g. NetSolP, or developability ML suites); not a simple formula.

Usage:
    python developability.py --seq EVQLVESGGGLVQPGGSLRLSCAAS...
    python developability.py --fasta vh.fasta
"""

from __future__ import annotations

import argparse
import sys

# AGGRESCAN intrinsic aggregation-propensity values (a3v), Conchillo-Sole 2007.
A3V = {
    "A": -0.036, "R": -1.240, "N": -1.302, "D": -1.836, "C": 0.604,
    "Q": -1.231, "E": -1.412, "G": -0.535, "H": -1.033, "I": 1.822,
    "L": 1.380, "K": -0.931, "M": 0.910, "F": 1.754, "P": -1.236,
    "S": -0.294, "T": -0.159, "W": 1.037, "Y": 1.159, "V": 1.594,
}
HOT_SPOT_THRESHOLD = -0.02  # AGGRESCAN HST: a4v above this = aggregation-prone

# Kyte-Doolittle hydropathy.
KD = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}

# EMBOSS pKa values for isoelectric point.
PKA = {"D": 3.9, "E": 4.1, "C": 8.5, "Y": 10.1, "H": 6.5, "K": 10.8, "R": 12.5}
N_TERM, C_TERM = 8.6, 3.6


def _window(values, w=5):
    half = w // 2
    out = []
    n = len(values)
    for i in range(n):
        lo, hi = max(0, i - half), min(n, i + half + 1)
        seg = values[lo:hi]
        out.append(sum(seg) / len(seg))
    return out


def aggrescan(seq):
    a3v = [A3V.get(aa, 0.0) for aa in seq]
    a4v = _window(a3v, 5)
    # hot spots: contiguous runs with a4v > threshold, length >= 5 (AGGRESCAN min)
    spots = []
    start = None
    for i, v in enumerate(a4v):
        if v > HOT_SPOT_THRESHOLD and start is None:
            start = i
        elif v <= HOT_SPOT_THRESHOLD and start is not None:
            if i - start >= 5:
                spots.append((start, i - 1))
            start = None
    if start is not None and len(a4v) - start >= 5:
        spots.append((start, len(a4v) - 1))
    regions = [
        {
            "start": s + 1,
            "end": e + 1,
            "peptide": seq[s : e + 1],
            "mean_a4v": round(sum(a4v[s : e + 1]) / (e - s + 1), 3),
        }
        for s, e in spots
    ]
    na4vss = sum(max(0.0, v - HOT_SPOT_THRESHOLD) for v in a4v) / len(a4v)
    return {"hot_spots": regions, "n_hot_spots": len(regions), "Na4vSS": round(na4vss, 4)}


def isoelectric_point(seq):
    counts = {aa: seq.count(aa) for aa in set(seq)}

    def charge(ph):
        pos = 10 ** (N_TERM - ph) / (1 + 10 ** (N_TERM - ph))
        pos += counts.get("K", 0) * 10 ** (PKA["K"] - ph) / (1 + 10 ** (PKA["K"] - ph))
        pos += counts.get("R", 0) * 10 ** (PKA["R"] - ph) / (1 + 10 ** (PKA["R"] - ph))
        pos += counts.get("H", 0) * 10 ** (PKA["H"] - ph) / (1 + 10 ** (PKA["H"] - ph))
        neg = 1 / (1 + 10 ** (C_TERM - ph))
        neg += counts.get("D", 0) / (1 + 10 ** (PKA["D"] - ph))
        neg += counts.get("E", 0) / (1 + 10 ** (PKA["E"] - ph))
        neg += counts.get("C", 0) / (1 + 10 ** (PKA["C"] - ph))
        neg += counts.get("Y", 0) / (1 + 10 ** (PKA["Y"] - ph))
        return pos - neg

    lo, hi = 0.0, 14.0
    for _ in range(100):
        mid = (lo + hi) / 2
        if charge(mid) > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def hydrophobic_patches(seq, w=7, threshold=1.5):
    kd = [KD.get(aa, 0.0) for aa in seq]
    sm = _window(kd, w)
    patches = []
    start = None
    for i, v in enumerate(sm):
        if v > threshold and start is None:
            start = i
        elif v <= threshold and start is not None:
            patches.append({"start": start + 1, "end": i, "peptide": seq[start:i]})
            start = None
    if start is not None:
        patches.append({"start": start + 1, "end": len(seq), "peptide": seq[start:]})
    return patches


def assess(seq):
    seq = "".join(c for c in seq.upper() if c.isalpha())
    return {
        "length": len(seq),
        "aggregation_AGGRESCAN": aggrescan(seq),
        "isoelectric_point": isoelectric_point(seq),
        "hydrophobic_patches": hydrophobic_patches(seq),
        "not_computed_from_sequence": {
            "binding_ddG": "needs a structure + FoldX / Rosetta Flex ddG (mutate the Fv:antigen complex)",
            "thermal_stability_Tm": "needs a sequence->Tm ML predictor; not a closed-form formula",
            "expression_titer": "needs a developability ML predictor; not derivable from sequence alone",
        },
    }


def _read_fasta(path):
    return "".join(line.strip() for line in open(path) if not line.startswith(">"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seq")
    p.add_argument("--fasta")
    args = p.parse_args(argv)
    seq = args.seq or (_read_fasta(args.fasta) if args.fasta else None)
    if not seq:
        p.error("provide --seq or --fasta")
    import json

    print(json.dumps(assess(seq), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
