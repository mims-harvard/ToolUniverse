#!/usr/bin/env python3
"""Sequence analysis utilities: residue counting, GC content, reverse complement, basic stats.

Usage:
  python sequence_tools.py --type count_residues --sequence "ACDEFGCCC" --residue C
  python sequence_tools.py --type count_region --accession P24046 --start 318 --end 440 --residue C
  python sequence_tools.py --type gc_content --sequence "ATGCGATCG"
  python sequence_tools.py --type reverse_complement --sequence "ATGCGATCG"
  python sequence_tools.py --type stats --sequence "ATGCGATCG"
"""
import argparse
import sys
import urllib.request
import urllib.error
import json


# ---------------------------------------------------------------------------
# Core sequence functions
# ---------------------------------------------------------------------------

COMPLEMENT = str.maketrans("ATCGatcgNn", "TAGCtagcNn")

DNA_BASES = frozenset("ATCGNatcgn")
RNA_BASES = frozenset("AUCGNaucgn")
AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWYacdefghiklmnpqrstvwy")


def is_dna(seq: str) -> bool:
    return all(c in DNA_BASES for c in seq) and "U" not in seq.upper()


def is_rna(seq: str) -> bool:
    return all(c in RNA_BASES for c in seq)


def reverse_complement(seq: str) -> dict:
    """Return the reverse complement of a DNA sequence.

    Args:
        seq: DNA sequence (IUPAC alphabet; N allowed).

    Returns:
        dict with original, reverse_complement, and length.
    """
    seq = seq.strip()
    if not seq:
        return {"error": "Empty sequence provided."}
    if not is_dna(seq):
        return {
            "error": (
                "Sequence contains non-DNA characters. "
                "reverse_complement only supports DNA (A/T/C/G/N)."
            )
        }
    rc = seq.translate(COMPLEMENT)[::-1]
    return {
        "original": seq.upper(),
        "reverse_complement": rc.upper(),
        "length": len(seq),
    }


def gc_content(seq: str) -> dict:
    """Calculate GC content of a DNA or RNA sequence.

    Args:
        seq: Nucleotide sequence.

    Returns:
        dict with gc_count, at_count, gc_fraction, gc_percent, length, and composition.
    """
    seq = seq.strip().upper()
    if not seq:
        return {"error": "Empty sequence provided."}

    counts = {b: seq.count(b) for b in "ATCGUN"}
    g = counts["G"]
    c = counts["C"]
    a = counts["A"]
    t = counts["T"]
    u = counts["U"]
    n = counts["N"]
    total = len(seq)
    gc = g + c
    at = a + t + u

    if total - n == 0:
        return {"error": "Sequence contains only ambiguous (N) bases."}

    gc_frac = gc / (total - n)

    return {
        "length": total,
        "gc_count": gc,
        "at_count": at,
        "n_count": n,
        "gc_fraction": round(gc_frac, 4),
        "gc_percent": round(gc_frac * 100, 2),
        "composition": {b: counts[b] for b in "ATCGUN" if counts[b] > 0},
        "interpretation": _gc_interpretation(gc_frac * 100),
    }


def _gc_interpretation(gc_pct: float) -> str:
    if gc_pct < 40:
        return f"GC={gc_pct:.1f}%: AT-rich sequence."
    if gc_pct > 60:
        return f"GC={gc_pct:.1f}%: GC-rich sequence."
    return f"GC={gc_pct:.1f}%: Typical GC content."


def count_residues(seq: str, residue: str) -> dict:
    """Count occurrences of a residue (amino acid or nucleotide) in a sequence.

    Args:
        seq:     Full sequence string.
        residue: Single character to count (case-insensitive).

    Returns:
        dict with count, fraction, length, and positions (1-based).
    """
    seq = seq.strip()
    if not seq:
        return {"error": "Empty sequence provided."}
    if len(residue) != 1:
        return {"error": f"residue must be a single character, got '{residue}'."}

    residue_upper = residue.upper()
    seq_upper = seq.upper()
    count = seq_upper.count(residue_upper)
    positions = [i + 1 for i, c in enumerate(seq_upper) if c == residue_upper]
    fraction = count / len(seq) if seq else 0.0

    return {
        "sequence_length": len(seq),
        "residue": residue_upper,
        "count": count,
        "fraction": round(fraction, 4),
        "percent": round(fraction * 100, 2),
        "positions_1based": positions[:50],  # cap to avoid huge output
        "positions_shown": min(len(positions), 50),
        "total_positions": len(positions),
    }


def count_residues_in_region(seq: str, start: int, end: int, residue: str) -> dict:
    """Count a residue within a specific region of a sequence.

    Args:
        seq:     Full sequence string (1-based indexing used for start/end).
        start:   1-based start position (inclusive).
        end:     1-based end position (inclusive).
        residue: Single character to count.

    Returns:
        dict with count and region details.
    """
    seq = seq.strip()
    if not seq:
        return {"error": "Empty sequence provided."}
    if len(residue) != 1:
        return {"error": f"residue must be a single character, got '{residue}'."}
    if start < 1 or end > len(seq) or start > end:
        return {
            "error": (
                f"Region [{start}, {end}] is invalid for sequence of length {len(seq)}. "
                "Use 1-based coordinates."
            )
        }

    region_seq = seq[start - 1 : end]  # convert 1-based to 0-based slice
    result = count_residues(region_seq, residue)
    result["region_start"] = start
    result["region_end"] = end
    result["region_length"] = len(region_seq)
    result["full_sequence_length"] = len(seq)
    result["region_sequence_preview"] = region_seq[:60] + ("..." if len(region_seq) > 60 else "")
    return result


def sequence_stats(seq: str) -> dict:
    """Compute basic statistics for a DNA, RNA, or protein sequence.

    Args:
        seq: Any biological sequence string.

    Returns:
        dict with length, composition, sequence type, and molecular weight estimate.
    """
    seq = seq.strip()
    if not seq:
        return {"error": "Empty sequence provided."}

    seq_upper = seq.upper()
    length = len(seq_upper)
    unique_chars = sorted(set(seq_upper))
    composition = {c: seq_upper.count(c) for c in unique_chars}

    # Detect sequence type
    if is_dna(seq_upper):
        seq_type = "DNA"
        gc = composition.get("G", 0) + composition.get("C", 0)
        n = composition.get("N", 0)
        gc_pct = gc / (length - n) * 100 if length - n > 0 else 0
        extra = {"gc_percent": round(gc_pct, 2)}
    elif is_rna(seq_upper):
        seq_type = "RNA"
        gc = composition.get("G", 0) + composition.get("C", 0)
        n = composition.get("N", 0)
        gc_pct = gc / (length - n) * 100 if length - n > 0 else 0
        extra = {"gc_percent": round(gc_pct, 2)}
    else:
        seq_type = "Protein"
        mw = _estimate_protein_mw(seq_upper)
        extra = {"estimated_mw_da": mw}

    return {
        "sequence_type": seq_type,
        "length": length,
        "composition": composition,
        **extra,
        "sequence_preview": seq[:80] + ("..." if length > 80 else ""),
    }


# Average residue masses (monoisotopic, Da), standard 20 amino acids
_AA_MASS = {
    "A": 71.03711, "R": 156.10111, "N": 114.04293, "D": 115.02694,
    "C": 103.00919, "E": 129.04259, "Q": 128.05858, "G": 57.02146,
    "H": 137.05891, "I": 113.08406, "L": 113.08406, "K": 128.09496,
    "M": 131.04049, "F": 147.06841, "P": 97.05276,  "S": 87.03203,
    "T": 101.04768, "W": 186.07931, "Y": 163.06333, "V": 99.06841,
}
_WATER_MASS = 18.01056


def _estimate_protein_mw(seq: str) -> float:
    """Estimate molecular weight in Daltons (monoisotopic, residue sum + water)."""
    mass = _WATER_MASS + sum(_AA_MASS.get(aa, 111.1) for aa in seq)
    return round(mass, 2)


# ---------------------------------------------------------------------------
# UniProt sequence fetching
# ---------------------------------------------------------------------------

def fetch_uniprot_sequence(accession: str) -> str:
    """Fetch protein sequence from UniProt REST API.

    Args:
        accession: UniProt accession (e.g., P24046).

    Returns:
        Protein sequence string (uppercase, no header).

    Raises:
        RuntimeError on HTTP or parsing error.
    """
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.fasta"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            fasta = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} fetching UniProt {accession}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error fetching UniProt {accession}: {e.reason}") from e

    lines = fasta.strip().splitlines()
    if not lines or not lines[0].startswith(">"):
        raise RuntimeError(f"Unexpected FASTA format for {accession}.")

    seq = "".join(lines[1:]).upper().replace(" ", "")
    if not seq:
        raise RuntimeError(f"Empty sequence returned for {accession}.")
    return seq


def count_region_from_accession(accession: str, start: int, end: int, residue: str) -> dict:
    """Fetch sequence from UniProt and count a residue in a region.

    Args:
        accession: UniProt accession.
        start:     1-based start (inclusive).
        end:       1-based end (inclusive).
        residue:   Single-character residue to count.

    Returns:
        dict with count, region details, and accession info.
    """
    try:
        seq = fetch_uniprot_sequence(accession)
    except RuntimeError as exc:
        return {"error": str(exc)}

    result = count_residues_in_region(seq, start, end, residue)
    result["accession"] = accession
    result["source"] = "UniProt REST API"
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Sequence analysis: residue counting, GC content, reverse complement, stats.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--type",
        required=True,
        choices=["count_residues", "count_region", "gc_content", "reverse_complement", "stats"],
        help="Analysis type.",
    )
    p.add_argument("--sequence", type=str, default=None, help="Sequence string (DNA/RNA/protein).")
    p.add_argument("--residue", type=str, default=None, help="[count_residues/count_region] Residue to count.")
    p.add_argument("--accession", type=str, default=None, help="[count_region] UniProt accession.")
    p.add_argument("--start", type=int, default=None, help="[count_region] 1-based start position.")
    p.add_argument("--end", type=int, default=None, help="[count_region] 1-based end position.")
    return p


def _print_result(result: dict) -> None:
    if "error" in result:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)
    for key, value in result.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        elif isinstance(value, list) and len(value) > 20:
            print(f"  {key}: [{value[0]}, {value[1]}, ..., {value[-1]}] ({len(value)} items)")
        else:
            print(f"  {key}: {value}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    calc_type = args.type

    if calc_type == "count_residues":
        if args.sequence is None:
            parser.error("--type count_residues requires --sequence")
        if args.residue is None:
            parser.error("--type count_residues requires --residue")
        result = count_residues(args.sequence, args.residue)

    elif calc_type == "count_region":
        if args.residue is None:
            parser.error("--type count_region requires --residue")
        if args.accession is not None:
            if args.start is None or args.end is None:
                parser.error("--type count_region with --accession requires --start and --end")
            result = count_region_from_accession(args.accession, args.start, args.end, args.residue)
        elif args.sequence is not None:
            if args.start is None or args.end is None:
                parser.error("--type count_region requires --start and --end")
            result = count_residues_in_region(args.sequence, args.start, args.end, args.residue)
        else:
            parser.error("--type count_region requires --sequence or --accession")

    elif calc_type == "gc_content":
        if args.sequence is None:
            parser.error("--type gc_content requires --sequence")
        result = gc_content(args.sequence)

    elif calc_type == "reverse_complement":
        if args.sequence is None:
            parser.error("--type reverse_complement requires --sequence")
        result = reverse_complement(args.sequence)

    elif calc_type == "stats":
        if args.sequence is None:
            parser.error("--type stats requires --sequence")
        result = sequence_stats(args.sequence)

    else:
        parser.error(f"Unknown type: {calc_type}")

    print(f"\n=== sequence_tools: {calc_type.upper()} ===")
    _print_result(result)


if __name__ == "__main__":
    main()
