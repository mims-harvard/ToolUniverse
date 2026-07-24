#!/usr/bin/env python3
"""Compute dN/dS (Ka/Ks) between two coding sequences (Nei-Gojobori method).

The comparative-genomics skill uses dN/dS to distinguish positive selection
(dN/dS > 1) from purifying selection (dN/dS << 1) and relaxed/neutral evolution
(dN/dS ~ 1), but ToolUniverse has no tool that computes it. This self-contained
script implements the Nei-Gojobori (1986) estimator with Jukes-Cantor correction
— no external dependencies.

Workflow it fits into:
  1. ensembl_get_homology(...) -> 1:1 ortholog IDs
  2. EnsemblSeq_get_id_sequence(..., type="cds") -> the two coding sequences
  3. codon-align them (orthologous CDS are usually alignable directly; for
     divergent pairs align the protein then back-translate), then run this.

Usage:
    python dnds.py CDS1.fasta CDS2.fasta          # two single-record FASTA files
    python dnds.py --seq1 ATG... --seq2 ATG...     # inline sequences
Inputs must be in-frame and codon-aligned (equal length, multiple of 3).
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys

BASES = "TCAG"
CODONS = [a + b + c for a in BASES for b in BASES for c in BASES]
# Standard genetic code (NCBI table 1).
_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON_TABLE = dict(zip(CODONS, _AA))


def _syn_nonsyn_sites(codon):
    """Synonymous (s) and non-synonymous (n) site counts for one codon (s+n=3)."""
    aa = CODON_TABLE.get(codon)
    if aa is None or aa == "*":
        return 0.0, 0.0
    s = 0.0
    for pos in range(3):
        syn = 0
        for base in BASES:
            if base == codon[pos]:
                continue
            mut = codon[:pos] + base + codon[pos + 1 :]
            maa = CODON_TABLE.get(mut)
            if maa is not None and maa != "*" and maa == aa:
                syn += 1
        s += syn / 3.0
    return s, 3.0 - s


def _path_diffs(c1, c2):
    """Avg synonymous/non-synonymous differences between two codons over all
    shortest mutational pathways (Nei-Gojobori)."""
    diffs = [i for i in range(3) if c1[i] != c2[i]]
    if not diffs:
        return 0.0, 0.0
    sd_total = nd_total = 0.0
    paths = 0
    for order in itertools.permutations(diffs):
        cur = c1
        ok = True
        sd = nd = 0.0
        for pos in order:
            nxt = cur[:pos] + c2[pos] + cur[pos + 1 :]
            a1, a2 = CODON_TABLE.get(cur), CODON_TABLE.get(nxt)
            if a1 == "*" or a2 == "*" or a1 is None or a2 is None:
                ok = False
                break
            if a1 == a2:
                sd += 1
            else:
                nd += 1
            cur = nxt
        if ok:
            sd_total += sd
            nd_total += nd
            paths += 1
    if paths == 0:
        return 0.0, float(len(diffs))
    return sd_total / paths, nd_total / paths


def _jukes_cantor(p):
    """JC69 correction; returns None if uncorrectable (p too large)."""
    if p < 0:
        return 0.0
    val = 1.0 - (4.0 / 3.0) * p
    if val <= 0:
        return None
    return -0.75 * math.log(val)


def dnds(seq1: str, seq2: str) -> dict:
    seq1 = seq1.upper().replace("U", "T")
    seq2 = seq2.upper().replace("U", "T")
    n = min(len(seq1), len(seq2))
    n -= n % 3
    if n == 0:
        raise ValueError("sequences too short / not codon length")
    S = N = Sd = Nd = 0.0
    compared = 0
    for i in range(0, n, 3):
        c1, c2 = seq1[i : i + 3], seq2[i : i + 3]
        if "-" in c1 or "-" in c2 or len(c1) < 3:
            continue
        s1, n1 = _syn_nonsyn_sites(c1)
        s2, n2 = _syn_nonsyn_sites(c2)
        S += (s1 + s2) / 2.0
        N += (n1 + n2) / 2.0
        sd, nd = _path_diffs(c1, c2)
        Sd += sd
        Nd += nd
        compared += 1

    def _z(x):  # normalise -0.0 -> 0.0
        return 0.0 if (x is not None and x == 0) else x

    pS = _z(Sd / S if S else 0.0)
    pN = _z(Nd / N if N else 0.0)
    dS = _z(_jukes_cantor(pS))
    dN = _z(_jukes_cantor(pN))
    omega = (dN / dS) if (dN is not None and dS not in (None, 0.0)) else None
    interp = "undetermined"
    if omega is not None:
        if omega > 1.25:
            interp = "positive (diversifying) selection (dN/dS > 1)"
        elif omega < 0.5:
            interp = "purifying selection / functional constraint (dN/dS << 1)"
        else:
            interp = "near-neutral / relaxed selection (dN/dS ~ 1)"
    return {
        "codons_compared": compared,
        "S_sites": round(S, 2),
        "N_sites": round(N, 2),
        "Sd": round(Sd, 2),
        "Nd": round(Nd, 2),
        "pS": round(pS, 4),
        "pN": round(pN, 4),
        "dS": None if dS is None else round(dS, 4),
        "dN": None if dN is None else round(dN, 4),
        "dN_dS": None if omega is None else round(omega, 4),
        "interpretation": interp,
    }


def _read_fasta(path: str) -> str:
    seq = []
    for line in open(path):
        if not line.startswith(">"):
            seq.append(line.strip())
    return "".join(seq)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("fasta1", nargs="?")
    p.add_argument("fasta2", nargs="?")
    p.add_argument("--seq1")
    p.add_argument("--seq2")
    args = p.parse_args(argv)
    s1 = args.seq1 or (_read_fasta(args.fasta1) if args.fasta1 else None)
    s2 = args.seq2 or (_read_fasta(args.fasta2) if args.fasta2 else None)
    if not s1 or not s2:
        p.error("provide two FASTA files or --seq1/--seq2")
    import json

    print(json.dumps(dnds(s1, s2), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
