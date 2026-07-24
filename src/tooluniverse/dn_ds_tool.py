"""
dN/dS (Ka/Ks) selection analysis between two coding sequences for ToolUniverse.

Local-compute, deterministic Nei-Gojobori (1986) estimator with Jukes-Cantor
correction — the standard way to tell positive/diversifying selection (dN/dS > 1)
from purifying selection (dN/dS << 1) and near-neutral evolution (dN/dS ~ 1).
Pure Python (no dependencies), no network, no API key.

General by construction: it takes any two in-frame, codon-aligned coding
sequences (inline or single-record FASTA files) — any organisms, any genes. The
method (per-codon synonymous/non-synonymous site counting + pathway-averaged
differences + JC69 correction) is ported verbatim from the comparative-genomics
skill's validated implementation.
"""

import itertools
import math
import os
from typing import Any, Dict, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASES = "TCAG"
_CODONS = [a + b + c for a in _BASES for b in _BASES for c in _BASES]
# Standard genetic code (NCBI table 1).
_AA = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
_CODON_TABLE = dict(zip(_CODONS, _AA))


def _err(msg: str) -> Dict[str, Any]:
    return {"status": "error", "error": msg}


def _ok(data: Dict[str, Any], **metadata) -> Dict[str, Any]:
    meta = {"engine": "nei_gojobori_1986", "correction": "jukes_cantor"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


def _syn_nonsyn_sites(codon: str):
    """Synonymous (s) and non-synonymous (n) site counts for one codon (s+n=3)."""
    aa = _CODON_TABLE.get(codon)
    if aa is None or aa == "*":
        return 0.0, 0.0
    s = 0.0
    for pos in range(3):
        syn = 0
        for base in _BASES:
            if base == codon[pos]:
                continue
            mut = codon[:pos] + base + codon[pos + 1 :]
            maa = _CODON_TABLE.get(mut)
            if maa is not None and maa != "*" and maa == aa:
                syn += 1
        s += syn / 3.0
    return s, 3.0 - s


def _path_diffs(c1: str, c2: str):
    """Avg synonymous/non-synonymous differences over all shortest mutational
    pathways between two codons (Nei-Gojobori)."""
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
            a1, a2 = _CODON_TABLE.get(cur), _CODON_TABLE.get(nxt)
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


def _jukes_cantor(p: float) -> Optional[float]:
    """JC69 correction; returns None if uncorrectable (p too large)."""
    if p < 0:
        return 0.0
    val = 1.0 - (4.0 / 3.0) * p
    if val <= 0:
        return None
    return -0.75 * math.log(val)


def _compute_dnds(seq1: str, seq2: str) -> Any:
    """Nei-Gojobori dN/dS. Returns a result dict, or an error dict."""
    seq1 = seq1.upper().replace("U", "T")
    seq2 = seq2.upper().replace("U", "T")
    n = min(len(seq1), len(seq2))
    n -= n % 3
    if n == 0:
        return _err(
            "sequences too short or not codon-length (need >= 3 aligned bases)."
        )

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

    if compared == 0:
        return _err("no comparable codons (all gapped or stop codons).")

    def _z(x):  # normalise -0.0 -> 0.0
        return 0.0 if (x is not None and x == 0) else x

    pS = _z(Sd / S if S else 0.0)
    pN = _z(Nd / N if N else 0.0)
    dS = _z(_jukes_cantor(pS))
    dN = _z(_jukes_cantor(pN))
    omega = (dN / dS) if (dN is not None and dS not in (None, 0.0)) else None

    interp = "undetermined (dS is 0 or saturated)"
    if omega is not None:
        if omega > 1.25:
            interp = "positive (diversifying) selection (dN/dS > 1)"
        elif omega < 0.5:
            interp = "purifying selection / functional constraint (dN/dS << 1)"
        else:
            interp = "near-neutral / relaxed selection (dN/dS ~ 1)"

    return {
        "dN_dS": None if omega is None else round(omega, 4),
        "dN": None if dN is None else round(dN, 4),
        "dS": None if dS is None else round(dS, 4),
        "pN": round(pN, 4),
        "pS": round(pS, 4),
        "N_sites": round(N, 2),
        "S_sites": round(S, 2),
        "Nd": round(Nd, 2),
        "Sd": round(Sd, 2),
        "codons_compared": compared,
        "interpretation": interp,
    }


def _read_fasta(path: str) -> Any:
    """Read the single sequence from a FASTA file (concatenating record lines)."""
    path = os.path.expanduser(str(path).strip())
    if not os.path.isfile(path):
        return _err(f"FASTA not found: {path}")
    try:
        seq = []
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith(">"):
                    seq.append(line)
        if not seq:
            return _err(f"no sequence found in {path}")
        return "".join(seq)
    except Exception as e:  # pragma: no cover - defensive
        return _err(f"failed to read FASTA {path}: {e}")


@register_tool("DnDsTool")
class DnDsTool(BaseTool):
    """Nei-Gojobori dN/dS (Ka/Ks) between two coding sequences."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq1 = arguments.get("seq1")
        seq2 = arguments.get("seq2")
        fasta1_path = arguments.get("fasta1_path")
        fasta2_path = arguments.get("fasta2_path")
        if fasta1_path or fasta2_path:
            if not (fasta1_path and fasta2_path):
                return _err("Provide both 'fasta1_path' and 'fasta2_path'.")
            seq1 = _read_fasta(fasta1_path)
            if isinstance(seq1, dict):
                return seq1
            seq2 = _read_fasta(fasta2_path)
            if isinstance(seq2, dict):
                return seq2
        if not seq1 or not seq2:
            return _err(
                "Provide two coding sequences: 'seq1' & 'seq2' (inline), or "
                "'fasta1_path' & 'fasta2_path'. Must be in-frame and codon-aligned."
            )
        valid = set("ACGTU-")
        for label, s in (("seq1", seq1), ("seq2", seq2)):
            if set(str(s).upper()) - valid:
                return _err(f"{label} contains non-nucleotide characters.")
        result = _compute_dnds(str(seq1), str(seq2))
        if result.get("status") == "error":
            return result
        return _ok(result)
