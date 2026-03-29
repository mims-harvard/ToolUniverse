"""
Sequence Analysis Tool

Residue counting (with live UniProt fetch), GC content, reverse complement,
and basic sequence statistics for DNA/RNA/protein sequences.

Uses UniProt REST API for sequence fetching. No other external dependencies.
"""

import urllib.error
import urllib.request
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


COMPLEMENT = str.maketrans("ATCGatcgNn", "TAGCtagcNn")
DNA_BASES = frozenset("ATCGNatcgn")
RNA_BASES = frozenset("AUCGNaucgn")

_AA_MASS = {
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
_WATER_MASS = 18.01056


def _is_dna(seq: str) -> bool:
    return all(c in DNA_BASES for c in seq) and "U" not in seq.upper()


def _is_rna(seq: str) -> bool:
    return all(c in RNA_BASES for c in seq)


def _fetch_uniprot(accession: str) -> str:
    """Fetch protein sequence from UniProt REST API."""
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.fasta"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            fasta = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"HTTP {e.code} fetching UniProt {accession}: {e.reason}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Network error fetching UniProt {accession}: {e.reason}"
        ) from e

    lines = fasta.strip().splitlines()
    if not lines or not lines[0].startswith(">"):
        raise RuntimeError(f"Unexpected FASTA format for {accession}.")

    seq = "".join(lines[1:]).upper().replace(" ", "")
    if not seq:
        raise RuntimeError(f"Empty sequence returned for {accession}.")
    return seq


@register_tool("SequenceAnalyzeTool")
class SequenceAnalyzeTool(BaseTool):
    """Sequence analysis: residue counting, GC content, reverse complement, stats."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "count_residues": self._count_residues,
            "gc_content": self._gc_content,
            "reverse_complement": self._reverse_complement,
            "stats": self._stats,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Analysis failed: {str(e)}"}

    def _resolve_sequence(self, arguments: Dict[str, Any]) -> str:
        """Get sequence from arguments, fetching from UniProt if needed."""
        seq = arguments.get("sequence")
        uniprot_id = arguments.get("uniprot_id")

        if seq:
            return seq.strip()
        if uniprot_id:
            return _fetch_uniprot(uniprot_id.strip())
        raise ValueError("Provide either 'sequence' or 'uniprot_id'.")

    def _count_residues(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq = self._resolve_sequence(arguments)
        residue = arguments.get("residue")

        if not seq:
            return {"status": "error", "error": "Empty sequence."}
        if not residue or len(residue) != 1:
            return {"status": "error", "error": "residue must be a single character."}

        seq_upper = seq.upper()
        residue_upper = residue.upper()
        count = seq_upper.count(residue_upper)
        fraction = count / len(seq_upper)
        positions = [i + 1 for i, c in enumerate(seq_upper) if c == residue_upper]

        data = {
            "sequence_length": len(seq_upper),
            "residue": residue_upper,
            "count": count,
            "fraction": round(fraction, 4),
            "percent": round(fraction * 100, 2),
            "positions_1based": positions[:50],
            "total_positions": len(positions),
        }
        if arguments.get("uniprot_id"):
            data["uniprot_id"] = arguments["uniprot_id"]
            data["source"] = "UniProt REST API"

        return {"status": "success", "data": data}

    def _gc_content(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq = self._resolve_sequence(arguments).upper()
        if not seq:
            return {"status": "error", "error": "Empty sequence."}

        counts = {b: seq.count(b) for b in "ATCGUN"}
        gc = counts["G"] + counts["C"]
        n = counts["N"]
        total = len(seq)

        if total - n == 0:
            return {"status": "error", "error": "Sequence contains only N bases."}

        gc_frac = gc / (total - n)

        return {
            "status": "success",
            "data": {
                "length": total,
                "gc_count": gc,
                "gc_fraction": round(gc_frac, 4),
                "gc_percent": round(gc_frac * 100, 2),
                "composition": {b: counts[b] for b in "ATCGUN" if counts[b] > 0},
            },
        }

    def _reverse_complement(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq = self._resolve_sequence(arguments).strip()
        if not seq:
            return {"status": "error", "error": "Empty sequence."}
        if not _is_dna(seq):
            return {
                "status": "error",
                "error": "Sequence contains non-DNA characters. Only A/T/C/G/N supported.",
            }

        rc = seq.translate(COMPLEMENT)[::-1]
        return {
            "status": "success",
            "data": {
                "original": seq.upper(),
                "reverse_complement": rc.upper(),
                "length": len(seq),
            },
        }

    def _stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq = self._resolve_sequence(arguments).strip().upper()
        if not seq:
            return {"status": "error", "error": "Empty sequence."}

        length = len(seq)
        composition = {c: seq.count(c) for c in sorted(set(seq))}

        if _is_dna(seq):
            seq_type = "DNA"
            gc = composition.get("G", 0) + composition.get("C", 0)
            n = composition.get("N", 0)
            gc_pct = gc / (length - n) * 100 if length - n > 0 else 0
            extra = {"gc_percent": round(gc_pct, 2)}
        elif _is_rna(seq):
            seq_type = "RNA"
            gc = composition.get("G", 0) + composition.get("C", 0)
            n = composition.get("N", 0)
            gc_pct = gc / (length - n) * 100 if length - n > 0 else 0
            extra = {"gc_percent": round(gc_pct, 2)}
        else:
            seq_type = "Protein"
            mw = _WATER_MASS + sum(_AA_MASS.get(aa, 111.1) for aa in seq)
            extra = {"estimated_mw_da": round(mw, 2)}

        data = {
            "sequence_type": seq_type,
            "length": length,
            "composition": composition,
            **extra,
        }
        if arguments.get("uniprot_id"):
            data["uniprot_id"] = arguments["uniprot_id"]

        return {"status": "success", "data": data}
