"""
DNA Design Tools

Provides local computational tools for DNA sequence analysis and design,
including restriction site detection, ORF finding, GC content calculation,
reverse complement, sequence translation, codon optimization, virtual digest,
primer design, Gibson assembly design, and Golden Gate assembly design.

No external API calls required. Pure Python implementation.
"""

import math
import re
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Standard genetic codon table (NCBI Standard Code 1)
STANDARD_CODON_TABLE = {
    "TTT": "F",
    "TTC": "F",
    "TTA": "L",
    "TTG": "L",
    "CTT": "L",
    "CTC": "L",
    "CTA": "L",
    "CTG": "L",
    "ATT": "I",
    "ATC": "I",
    "ATA": "I",
    "ATG": "M",
    "GTT": "V",
    "GTC": "V",
    "GTA": "V",
    "GTG": "V",
    "TCT": "S",
    "TCC": "S",
    "TCA": "S",
    "TCG": "S",
    "CCT": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACT": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCT": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "TAT": "Y",
    "TAC": "Y",
    "TAA": "*",
    "TAG": "*",
    "CAT": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAT": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAT": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "TGT": "C",
    "TGC": "C",
    "TGA": "*",
    "TGG": "W",
    "CGT": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGT": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGT": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}

COMPLEMENT = str.maketrans("ATGCatgc", "TACGtacg")

# Codon frequency tables: species -> amino_acid -> preferred codon
# Source: Codon Usage Database (highest-frequency codon per amino acid per species)
CODON_FREQ_TABLES = {
    "human": {
        "A": "GCC",
        "R": "AGG",
        "N": "AAC",
        "D": "GAC",
        "C": "TGC",
        "Q": "CAG",
        "E": "GAG",
        "G": "GGC",
        "H": "CAC",
        "I": "ATC",
        "L": "CTG",
        "K": "AAG",
        "M": "ATG",
        "F": "TTC",
        "P": "CCC",
        "S": "AGC",
        "T": "ACC",
        "W": "TGG",
        "Y": "TAC",
        "V": "GTG",
        "*": "TGA",
    },
    "ecoli": {
        "A": "GCG",
        "R": "CGT",
        "N": "AAC",
        "D": "GAT",
        "C": "TGC",
        "Q": "CAG",
        "E": "GAA",
        "G": "GGC",
        "H": "CAC",
        "I": "ATC",
        "L": "CTG",
        "K": "AAA",
        "M": "ATG",
        "F": "TTT",
        "P": "CCG",
        "S": "AGC",
        "T": "ACC",
        "W": "TGG",
        "Y": "TAT",
        "V": "GTG",
        "*": "TAA",
    },
    "mouse": {
        "A": "GCC",
        "R": "AGG",
        "N": "AAC",
        "D": "GAC",
        "C": "TGC",
        "Q": "CAG",
        "E": "GAG",
        "G": "GGC",
        "H": "CAC",
        "I": "ATC",
        "L": "CTG",
        "K": "AAG",
        "M": "ATG",
        "F": "TTC",
        "P": "CCC",
        "S": "AGC",
        "T": "ACC",
        "W": "TGG",
        "Y": "TAC",
        "V": "GTG",
        "*": "TGA",
    },
    "yeast": {
        "A": "GCT",
        "R": "AGA",
        "N": "AAT",
        "D": "GAT",
        "C": "TGT",
        "Q": "CAA",
        "E": "GAA",
        "G": "GGT",
        "H": "CAT",
        "I": "ATT",
        "L": "TTG",
        "K": "AAG",
        "M": "ATG",
        "F": "TTT",
        "P": "CCA",
        "S": "TCT",
        "T": "ACT",
        "W": "TGG",
        "Y": "TAT",
        "V": "GTT",
        "*": "TAA",
    },
}

# Codon adaptation index reference values for each species (relative adaptiveness)
# Simplified: ratio of codon usage frequency to max frequency in synonymous group
CAI_REFERENCE = {
    "human": {
        "GCC": 1.0,
        "GCT": 0.71,
        "GCA": 0.54,
        "GCG": 0.11,
        "AGG": 1.0,
        "AGA": 0.84,
        "CGC": 0.77,
        "CGG": 0.64,
        "CGT": 0.44,
        "CGA": 0.34,
        "AAC": 1.0,
        "AAT": 0.75,
        "GAC": 1.0,
        "GAT": 0.81,
        "TGC": 1.0,
        "TGT": 0.72,
        "CAG": 1.0,
        "CAA": 0.37,
        "GAG": 1.0,
        "GAA": 0.69,
        "GGC": 1.0,
        "GGG": 0.77,
        "GGA": 0.74,
        "GGT": 0.56,
        "CAC": 1.0,
        "CAT": 0.69,
        "ATC": 1.0,
        "ATT": 0.70,
        "ATA": 0.34,
        "CTG": 1.0,
        "CTC": 0.58,
        "TTG": 0.39,
        "CTT": 0.36,
        "CTA": 0.19,
        "TTA": 0.12,
        "AAG": 1.0,
        "AAA": 0.74,
        "ATG": 1.0,
        "TTC": 1.0,
        "TTT": 0.72,
        "CCC": 1.0,
        "CCT": 0.78,
        "CCA": 0.73,
        "CCG": 0.20,
        "AGC": 1.0,
        "TCC": 0.87,
        "TCT": 0.76,
        "AGT": 0.65,
        "TCA": 0.58,
        "TCG": 0.18,
        "ACC": 1.0,
        "ACA": 0.79,
        "ACT": 0.73,
        "ACG": 0.25,
        "TGG": 1.0,
        "TAC": 1.0,
        "TAT": 0.72,
        "GTG": 1.0,
        "GTC": 0.62,
        "GTT": 0.56,
        "GTA": 0.28,
    },
    "ecoli": {
        "GCG": 1.0,
        "GCC": 0.53,
        "GCT": 0.49,
        "GCA": 0.40,
        "CGT": 1.0,
        "CGC": 0.97,
        "CGA": 0.38,
        "CGG": 0.35,
        "AGA": 0.10,
        "AGG": 0.06,
        "AAC": 1.0,
        "AAT": 0.49,
        "GAT": 1.0,
        "GAC": 0.53,
        "TGC": 1.0,
        "TGT": 0.52,
        "CAG": 1.0,
        "CAA": 0.35,
        "GAA": 1.0,
        "GAG": 0.50,
        "GGC": 1.0,
        "GGT": 0.75,
        "GGA": 0.28,
        "GGG": 0.24,
        "CAC": 1.0,
        "CAT": 0.69,
        "ATC": 1.0,
        "ATT": 0.92,
        "ATA": 0.11,
        "CTG": 1.0,
        "TTA": 0.20,
        "TTG": 0.18,
        "CTT": 0.15,
        "CTC": 0.12,
        "CTA": 0.06,
        "AAA": 1.0,
        "AAG": 0.25,
        "ATG": 1.0,
        "TTT": 1.0,
        "TTC": 0.56,
        "CCG": 1.0,
        "CCA": 0.29,
        "CCT": 0.24,
        "CCC": 0.16,
        "AGC": 1.0,
        "TCT": 0.85,
        "TCC": 0.66,
        "TCA": 0.58,
        "TCG": 0.54,
        "AGT": 0.42,
        "ACC": 1.0,
        "ACT": 0.69,
        "ACA": 0.40,
        "ACG": 0.37,
        "TGG": 1.0,
        "TAT": 1.0,
        "TAC": 0.57,
        "GTG": 1.0,
        "GTT": 0.68,
        "GTC": 0.38,
        "GTA": 0.33,
    },
    "mouse": {
        "GCC": 1.0,
        "GCT": 0.73,
        "GCA": 0.51,
        "GCG": 0.10,
        "AGG": 1.0,
        "AGA": 0.83,
        "CGC": 0.74,
        "CGG": 0.63,
        "CGT": 0.42,
        "CGA": 0.32,
        "AAC": 1.0,
        "AAT": 0.73,
        "GAC": 1.0,
        "GAT": 0.80,
        "TGC": 1.0,
        "TGT": 0.70,
        "CAG": 1.0,
        "CAA": 0.36,
        "GAG": 1.0,
        "GAA": 0.67,
        "GGC": 1.0,
        "GGG": 0.75,
        "GGA": 0.72,
        "GGT": 0.54,
        "CAC": 1.0,
        "CAT": 0.67,
        "ATC": 1.0,
        "ATT": 0.68,
        "ATA": 0.32,
        "CTG": 1.0,
        "CTC": 0.56,
        "TTG": 0.38,
        "CTT": 0.34,
        "CTA": 0.18,
        "TTA": 0.11,
        "AAG": 1.0,
        "AAA": 0.72,
        "ATG": 1.0,
        "TTC": 1.0,
        "TTT": 0.70,
        "CCC": 1.0,
        "CCT": 0.76,
        "CCA": 0.71,
        "CCG": 0.18,
        "AGC": 1.0,
        "TCC": 0.85,
        "TCT": 0.74,
        "AGT": 0.63,
        "TCA": 0.56,
        "TCG": 0.17,
        "ACC": 1.0,
        "ACA": 0.77,
        "ACT": 0.71,
        "ACG": 0.23,
        "TGG": 1.0,
        "TAC": 1.0,
        "TAT": 0.70,
        "GTG": 1.0,
        "GTC": 0.60,
        "GTT": 0.54,
        "GTA": 0.26,
    },
    "yeast": {
        "GCT": 1.0,
        "GCC": 0.62,
        "GCA": 0.55,
        "GCG": 0.12,
        "AGA": 1.0,
        "AGG": 0.34,
        "CGT": 0.25,
        "CGC": 0.10,
        "CGA": 0.09,
        "CGG": 0.06,
        "AAT": 1.0,
        "AAC": 0.75,
        "GAT": 1.0,
        "GAC": 0.65,
        "TGT": 1.0,
        "TGC": 0.77,
        "CAA": 1.0,
        "CAG": 0.69,
        "GAA": 1.0,
        "GAG": 0.69,
        "GGT": 1.0,
        "GGA": 0.62,
        "GGG": 0.21,
        "GGC": 0.20,
        "CAT": 1.0,
        "CAC": 0.64,
        "ATT": 1.0,
        "ATC": 0.71,
        "ATA": 0.27,
        "TTG": 1.0,
        "TTA": 0.50,
        "CTT": 0.23,
        "CTC": 0.07,
        "CTG": 0.06,
        "CTA": 0.06,
        "AAG": 1.0,
        "AAA": 0.79,
        "ATG": 1.0,
        "TTT": 1.0,
        "TTC": 0.80,
        "CCA": 1.0,
        "CCT": 0.62,
        "CCC": 0.34,
        "CCG": 0.16,
        "TCT": 1.0,
        "AGT": 0.78,
        "TCA": 0.74,
        "TCC": 0.62,
        "AGC": 0.27,
        "TCG": 0.23,
        "ACT": 1.0,
        "ACA": 0.78,
        "ACC": 0.60,
        "ACG": 0.22,
        "TGG": 1.0,
        "TAT": 1.0,
        "TAC": 0.76,
        "GTT": 1.0,
        "GTC": 0.54,
        "GTG": 0.46,
        "GTA": 0.40,
    },
}

# SantaLucia 1998 nearest-neighbor parameters: dinucleotide -> (dH kcal/mol, dS cal/mol/K)
NN_PARAMS = {
    "AA": (-7.9, -22.2),
    "AT": (-7.2, -20.4),
    "TA": (-7.2, -21.3),
    "CA": (-8.5, -22.7),
    "GT": (-8.4, -22.4),
    "CT": (-7.8, -21.0),
    "GA": (-8.2, -22.2),
    "CG": (-10.6, -27.2),
    "GC": (-9.8, -24.4),
    "GG": (-8.0, -19.9),
}

# NEB common restriction enzymes: enzyme name -> recognition sequence
NEB_ENZYMES = {
    "EcoRI": "GAATTC",
    "BamHI": "GGATCC",
    "HindIII": "AAGCTT",
    "NcoI": "CCATGG",
    "NdeI": "CATATG",
    "XhoI": "CTCGAG",
    "XbaI": "TCTAGA",
    "SalI": "GTCGAC",
    "SmaI": "CCCGGG",
    "KpnI": "GGTACC",
    "SacI": "GAGCTC",
    "ClaI": "ATCGAT",
    "SpeI": "ACTAGT",
    "NotI": "GCGGCCGC",
    "PstI": "CTGCAG",
    "EcoRV": "GATATC",
    "NheI": "GCTAGC",
    "MluI": "ACGCGT",
    "ApaI": "GGGCCC",
    "SphI": "GCATGC",
    "BglII": "AGATCT",
    "AgeI": "ACCGGT",
    "AscI": "GGCGCGCC",
    "PacI": "TTAATTAA",
    "SfiI": "GGCCNNNNNGGCC",
}


@register_tool("DNATool")
class DNATool(BaseTool):
    """
    Local DNA sequence analysis and design tools.

    No external API calls. Provides:
    - Restriction site detection (NEB enzyme library)
    - Open reading frame (ORF) finding
    - GC content calculation
    - Reverse complement generation
    - DNA to protein translation
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DNA analysis tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "find_restriction_sites": self._find_restriction_sites,
            "find_orfs": self._find_orfs,
            "calculate_gc_content": self._calculate_gc_content,
            "reverse_complement": self._reverse_complement,
            "translate_sequence": self._translate_sequence,
            "codon_optimize": self._codon_optimize,
            "virtual_digest": self._virtual_digest,
            "primer_design": self._primer_design,
            "gibson_design": self._gibson_design,
            "golden_gate_design": self._golden_gate_design,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}",
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except Exception as e:
            return {"status": "error", "error": f"Operation failed: {str(e)}"}

    def _validate_dna_sequence(self, seq: str) -> Optional[str]:
        """Validate DNA sequence, returns error message or None if valid."""
        valid_chars = set("ATGCNatgcn")
        invalid = set(seq) - valid_chars
        if invalid:
            return f"Invalid DNA characters: {invalid}. Only A, T, G, C, N allowed."
        return None

    def _find_restriction_sites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find restriction enzyme recognition sites in a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        enzymes_requested = arguments.get("enzymes")
        if enzymes_requested:
            if isinstance(enzymes_requested, str):
                enzymes_requested = [enzymes_requested]
            enzyme_dict = {
                name: seq
                for name, seq in NEB_ENZYMES.items()
                if name in enzymes_requested
            }
            not_found = [e for e in enzymes_requested if e not in NEB_ENZYMES]
            if not_found:
                return {
                    "status": "error",
                    "error": f"Unknown enzymes: {not_found}. Available: {sorted(NEB_ENZYMES.keys())}",
                }
        else:
            enzyme_dict = NEB_ENZYMES

        results = {}
        for enzyme_name, recognition_seq in enzyme_dict.items():
            if "N" in recognition_seq:
                pattern = recognition_seq.replace("N", "[ATGC]")
                positions = [
                    m.start() + 1 for m in re.finditer(f"(?={pattern})", sequence)
                ]
            else:
                positions = []
                start = 0
                while True:
                    pos = sequence.find(recognition_seq, start)
                    if pos == -1:
                        break
                    positions.append(pos + 1)  # 1-based
                    start = pos + 1

            if positions:
                results[enzyme_name] = {
                    "recognition_sequence": recognition_seq,
                    "cut_sites": positions,
                    "num_cuts": len(positions),
                }

        return {
            "status": "success",
            "data": {
                "sequence_length": len(sequence),
                "enzymes_with_sites": results,
                "enzymes_cutting": sorted(results.keys()),
                "num_enzymes_cutting": len(results),
            },
        }

    def _find_orfs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find open reading frames (ORFs) in a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        min_length = arguments.get("min_length", 100)  # minimum nt length
        strand = arguments.get("strand", "both")  # "forward", "reverse", "both"

        _STOP_SET = {"TAA", "TAG", "TGA"}

        def find_orfs_in_sequence(seq: str, is_reverse: bool = False) -> List[Dict]:
            """Scan all three reading frames using a state-machine (open/closed)."""
            orfs = []
            seq_len = len(seq)
            strand_label = "-" if is_reverse else "+"

            for frame_offset in (0, 1, 2):
                orf_open = False
                orf_start_idx = 0

                pos = frame_offset
                while pos + 3 <= seq_len:
                    codon = seq[pos : pos + 3]
                    if not orf_open:
                        if codon == "ATG":
                            orf_open = True
                            orf_start_idx = pos
                    else:
                        if codon in _STOP_SET:
                            orf_nt_len = pos + 3 - orf_start_idx
                            if orf_nt_len >= min_length:
                                if is_reverse:
                                    coord_start = seq_len - (pos + 3) + 1
                                    coord_end = seq_len - orf_start_idx
                                else:
                                    coord_start = orf_start_idx + 1  # 1-based
                                    coord_end = pos + 3
                                orfs.append(
                                    {
                                        "start": coord_start,
                                        "end": coord_end,
                                        "length_nt": orf_nt_len,
                                        "length_aa": orf_nt_len // 3 - 1,
                                        "frame": frame_offset + 1,
                                        "strand": strand_label,
                                        "sequence": seq[orf_start_idx : pos + 3],
                                    }
                                )
                            orf_open = False
                    pos += 3
            return orfs

        all_orfs = []

        if strand in ("forward", "both"):
            all_orfs.extend(find_orfs_in_sequence(sequence, is_reverse=False))

        if strand in ("reverse", "both"):
            rev_comp = sequence.translate(COMPLEMENT)[::-1]
            all_orfs.extend(find_orfs_in_sequence(rev_comp, is_reverse=True))

        all_orfs.sort(key=lambda x: x["length_nt"], reverse=True)

        return {
            "status": "success",
            "data": {
                "sequence_length": len(sequence),
                "min_length_nt": min_length,
                "num_orfs_found": len(all_orfs),
                "orfs": all_orfs[:50],
            },
        }

    def _calculate_gc_content(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate GC content and nucleotide composition of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        total = len(sequence)
        if total == 0:
            return {"status": "error", "error": "Empty sequence"}

        counts = {
            "A": sequence.count("A"),
            "T": sequence.count("T"),
            "G": sequence.count("G"),
            "C": sequence.count("C"),
            "N": sequence.count("N"),
        }

        gc_count = counts["G"] + counts["C"]
        at_count = counts["A"] + counts["T"]
        effective_total = total - counts["N"]

        gc_content = (gc_count / effective_total * 100) if effective_total > 0 else 0

        return {
            "status": "success",
            "data": {
                "gc_content_percent": round(gc_content, 2),
                "at_content_percent": round(
                    (at_count / effective_total * 100) if effective_total > 0 else 0, 2
                ),
                "nucleotide_counts": counts,
                "sequence_length": total,
                "effective_length": effective_total,
                "interpretation": (
                    "High GC"
                    if gc_content > 60
                    else "Low GC"
                    if gc_content < 40
                    else "Normal GC"
                ),
            },
        }

    def _reverse_complement(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the reverse complement of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        complement_map = str.maketrans("ATGCNatgcn", "TACGNtacgn")
        rev_comp = sequence.translate(complement_map)[::-1]

        return {
            "status": "success",
            "data": {
                "original": sequence,
                "reverse_complement": rev_comp,
                "length": len(sequence),
            },
        }

    def _translate_sequence(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a DNA sequence to protein using the standard codon table."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        codon_table_name = arguments.get("codon_table", "standard")
        if codon_table_name != "standard":
            return {
                "status": "error",
                "error": "Only 'standard' codon table is currently supported",
            }

        if len(sequence) % 3 != 0:
            trimmed_len = len(sequence) - (len(sequence) % 3)
            sequence_trimmed = sequence[:trimmed_len]
            warning = f"Sequence length {len(sequence)} is not divisible by 3; trimmed to {trimmed_len} nt"
        else:
            sequence_trimmed = sequence
            warning = None

        protein = []
        stop_positions = []
        for i in range(0, len(sequence_trimmed), 3):
            codon = sequence_trimmed[i : i + 3]
            aa = STANDARD_CODON_TABLE.get(codon, "X")
            if aa == "*":
                stop_positions.append(i // 3 + 1)
                protein.append("*")
            else:
                protein.append(aa)

        protein_seq = "".join(protein)

        if "*" in protein_seq:
            first_stop = protein_seq.index("*")
            protein_seq_no_stop = protein_seq[:first_stop]
        else:
            protein_seq_no_stop = protein_seq

        result = {
            "status": "success",
            "data": {
                "dna_sequence": sequence,
                "protein_sequence": protein_seq_no_stop,
                "full_translation": protein_seq,
                "protein_length_aa": len(protein_seq_no_stop),
                "stop_codons_found": len(stop_positions),
                "stop_codon_positions": stop_positions,
                "codon_table": codon_table_name,
            },
        }
        if warning:
            result["data"]["warning"] = warning

        return result

    def _codon_optimize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Codon-optimize an amino acid sequence for expression in a target species."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().strip()
        species = (arguments.get("species") or "human").lower()

        if species not in CODON_FREQ_TABLES:
            return {
                "status": "error",
                "error": f"Unknown species: {species}. Available: {sorted(CODON_FREQ_TABLES.keys())}",
            }

        codon_table = CODON_FREQ_TABLES[species]
        cai_table = CAI_REFERENCE[species]

        valid_aa = set("ACDEFGHIKLMNPQRSTVWY*")
        invalid = set(sequence) - valid_aa
        if invalid:
            return {
                "status": "error",
                "error": f"Invalid amino acid characters: {invalid}. Use single-letter codes.",
            }

        dna_codons = []
        cai_values = []
        for aa in sequence:
            if aa == "*":
                codon = codon_table.get("*", "TAA")
            else:
                codon = codon_table.get(aa)
                if codon is None:
                    return {
                        "status": "error",
                        "error": f"No codon found for amino acid: {aa}",
                    }
            dna_codons.append(codon)
            cai_values.append(cai_table.get(codon, 1.0))

        optimized_dna = "".join(dna_codons)
        length_bp = len(optimized_dna)

        gc = sum(1 for b in optimized_dna if b in "GC")
        gc_content = round(gc / length_bp * 100, 2) if length_bp > 0 else 0.0

        if cai_values:
            log_sum = sum(math.log(v) for v in cai_values if v > 0)
            cai = round(math.exp(log_sum / len(cai_values)), 4)
        else:
            cai = 0.0

        return {
            "status": "success",
            "data": {
                "optimized_dna": optimized_dna,
                "gc_content": gc_content,
                "cai": cai,
                "length_bp": length_bp,
            },
        }

    def _virtual_digest(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a virtual restriction digest of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        enzymes_requested = arguments.get("enzymes")
        circular = bool(arguments.get("circular", False))

        if enzymes_requested:
            if isinstance(enzymes_requested, str):
                enzymes_requested = [enzymes_requested]
            not_found = [e for e in enzymes_requested if e not in NEB_ENZYMES]
            if not_found:
                return {
                    "status": "error",
                    "error": f"Unknown enzymes: {not_found}. Available: {sorted(NEB_ENZYMES.keys())}",
                }
            enzyme_dict = {name: NEB_ENZYMES[name] for name in enzymes_requested}
        else:
            enzyme_dict = NEB_ENZYMES

        cut_sites_list = []
        enzymes_used = []
        for enzyme_name, recognition_seq in enzyme_dict.items():
            if "N" in recognition_seq:
                pattern = recognition_seq.replace("N", "[ATGC]")
                positions = [m.start() for m in re.finditer(f"(?={pattern})", sequence)]
            else:
                positions = []
                start = 0
                while True:
                    pos = sequence.find(recognition_seq, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1

            for pos in positions:
                cut_pos = pos + len(recognition_seq)
                cut_sites_list.append({"enzyme": enzyme_name, "position": cut_pos})

            if positions:
                enzymes_used.append(enzyme_name)

        cut_sites_list.sort(key=lambda x: x["position"])
        seq_len = len(sequence)
        fragments = []

        if not cut_sites_list:
            fragments.append(
                {
                    "sequence": sequence,
                    "length": seq_len,
                    "start": 0,
                    "end": seq_len,
                }
            )
        else:
            cut_positions = sorted(set(cs["position"] for cs in cut_sites_list))

            if circular:
                boundaries = cut_positions
                for i in range(len(boundaries)):
                    start = boundaries[i]
                    end = boundaries[(i + 1) % len(boundaries)]
                    if end > start:
                        frag_seq = sequence[start:end]
                    else:
                        frag_seq = sequence[start:] + sequence[:end]
                    fragments.append(
                        {
                            "sequence": frag_seq,
                            "length": len(frag_seq),
                            "start": start,
                            "end": end,
                        }
                    )
            else:
                starts = [0] + cut_positions
                ends = cut_positions + [seq_len]
                for s, e in zip(starts, ends):
                    frag_seq = sequence[s:e]
                    if frag_seq:
                        fragments.append(
                            {
                                "sequence": frag_seq,
                                "length": len(frag_seq),
                                "start": s,
                                "end": e,
                            }
                        )

        return {
            "status": "success",
            "data": {
                "fragments": fragments,
                "n_fragments": len(fragments),
                "enzymes_used": sorted(enzymes_used),
                "cut_sites": cut_sites_list,
            },
        }

    def _calc_tm_nn(self, primer: str) -> float:
        """Calculate melting temperature using SantaLucia 1998 nearest-neighbor model."""
        seq = primer.upper()
        n = len(seq)
        if n < 2:
            return 0.0

        dH = 0.0  # kcal/mol
        dS = 0.0  # cal/mol/K

        # Initiation parameters (SantaLucia 1998)
        dH += 0.2
        dS += -5.7

        for i in range(n - 1):
            dinuc = seq[i : i + 2]
            params = NN_PARAMS.get(dinuc)
            if params is None:
                rev_dinuc = dinuc.translate(COMPLEMENT)[::-1]
                params = NN_PARAMS.get(rev_dinuc)
            if params:
                dH += params[0]
                dS += params[1]

        # Convert: Tm = dH*1000 / (dS + R*ln(CT/4)) - 273.15
        # R = 1.987 cal/mol/K, CT = 250e-9 M (250 nM typical)
        R = 1.987
        CT = 250e-9
        dS_total = dS + R * math.log(CT / 4)
        if dS_total == 0:
            return 0.0
        tm = (dH * 1000) / dS_total - 273.15
        return round(tm, 1)

    def _primer_design(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design PCR primers for a target region using nearest-neighbor Tm calculation."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        seq_len = len(sequence)
        target_start = arguments.get("target_start")
        target_end = arguments.get("target_end")
        tm_target = float(arguments.get("tm_target") or 60.0)
        product_size_min = int(arguments.get("product_size_min") or 100)
        product_size_max = int(arguments.get("product_size_max") or 1000)

        if target_start is None:
            target_start = 0
        if target_end is None:
            target_end = seq_len

        target_start = max(0, int(target_start))
        target_end = min(seq_len, int(target_end))

        if target_end - target_start < product_size_min:
            return {
                "status": "error",
                "error": f"Target region ({target_end - target_start} bp) is smaller than product_size_min ({product_size_min} bp)",
            }

        fwd_search_start = max(0, target_start - 50)
        fwd_search_end = min(seq_len - 18, target_start + 50)

        rev_search_start = max(18, target_end - 50)
        rev_search_end = min(seq_len, target_end + 50)

        complement_map = str.maketrans("ATGCNatgcn", "TACGNtacgn")

        def has_3prime_repeat(seq: str, max_repeat: int = 3) -> bool:
            """Check if 3' end has too many identical bases."""
            if len(seq) < max_repeat + 1:
                return False
            tail = seq[-max_repeat:]
            return len(set(tail)) == 1

        def gc_content(seq: str) -> float:
            gc = sum(1 for b in seq if b in "GC")
            return gc / len(seq) * 100 if len(seq) > 0 else 0

        def score_primer(primer: str, tm: float) -> float:
            """Lower is better."""
            return abs(tm - tm_target)

        best_fwd = None
        best_fwd_score = float("inf")

        for start in range(fwd_search_start, fwd_search_end + 1):
            for length in range(18, 26):
                end = start + length
                if end > seq_len:
                    break
                primer = sequence[start:end]
                gc = gc_content(primer)
                if gc < 40 or gc > 60:
                    continue
                if has_3prime_repeat(primer):
                    continue
                tm = self._calc_tm_nn(primer)
                score = score_primer(primer, tm)
                if score < best_fwd_score:
                    best_fwd_score = score
                    best_fwd = {
                        "sequence": primer,
                        "tm": tm,
                        "gc_content": round(gc, 1),
                        "length": length,
                        "start": start,
                    }

        if not best_fwd:
            return {
                "status": "error",
                "error": "Could not design a suitable forward primer in the specified region",
            }

        best_rev = None
        best_rev_score = float("inf")

        for end in range(rev_search_end, rev_search_start - 1, -1):
            for length in range(18, 26):
                start = end - length
                if start < 0:
                    break
                primer_template = sequence[start:end]
                # Reverse primer is reverse complement of template
                rev_primer = primer_template.translate(complement_map)[::-1]
                gc = gc_content(rev_primer)
                if gc < 40 or gc > 60:
                    continue
                if has_3prime_repeat(rev_primer):
                    continue
                tm = self._calc_tm_nn(rev_primer)
                score = score_primer(rev_primer, tm)
                if score < best_rev_score:
                    best_rev_score = score
                    best_rev = {
                        "sequence": rev_primer,
                        "tm": tm,
                        "gc_content": round(gc, 1),
                        "length": length,
                        "end": end,
                    }

        if not best_rev:
            return {
                "status": "error",
                "error": "Could not design a suitable reverse primer in the specified region",
            }

        product_size = best_rev["end"] - best_fwd["start"]
        if product_size < product_size_min or product_size > product_size_max:
            return {
                "status": "error",
                "error": f"Designed product size ({product_size} bp) is outside the range [{product_size_min}, {product_size_max}] bp",
            }

        return {
            "status": "success",
            "data": {
                "forward_primer": best_fwd,
                "reverse_primer": best_rev,
                "product_size": product_size,
            },
        }

    def _gibson_design(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design Gibson Assembly overlaps for a set of DNA fragments."""
        fragments = arguments.get("fragments")
        if not fragments or not isinstance(fragments, list) or len(fragments) < 2:
            return {
                "status": "error",
                "error": "fragments must be a list of at least 2 DNA sequences",
            }

        overlap_length = int(arguments.get("overlap_length") or 20)
        if overlap_length < 1:
            return {"status": "error", "error": "overlap_length must be at least 1"}

        for i, frag in enumerate(fragments):
            frag_upper = frag.upper().replace(" ", "").replace("\n", "")
            err = self._validate_dna_sequence(frag_upper)
            if err:
                return {"status": "error", "error": f"Fragment {i + 1}: {err}"}
            if len(frag_upper) <= overlap_length:
                return {
                    "status": "error",
                    "error": f"Fragment {i + 1} (length {len(frag_upper)}) must be longer than overlap_length ({overlap_length})",
                }

        fragments_clean = [
            f.upper().replace(" ", "").replace("\n", "") for f in fragments
        ]
        n = len(fragments_clean)
        assembly_fragments = []

        for i, frag in enumerate(fragments_clean):
            prev_frag = fragments_clean[(i - 1) % n]
            next_frag = fragments_clean[(i + 1) % n]

            left_overlap = prev_frag[-overlap_length:]
            right_overlap = next_frag[:overlap_length]
            with_overlaps = left_overlap + frag + right_overlap

            assembly_fragments.append(
                {
                    "name": f"Fragment_{i + 1}",
                    "original_sequence": frag,
                    "with_overlaps": with_overlaps,
                    "left_overlap": left_overlap,
                    "right_overlap": right_overlap,
                }
            )

        return {
            "status": "success",
            "data": {
                "assembly_fragments": assembly_fragments,
                "n_fragments": n,
                "overlap_length": overlap_length,
            },
        }

    def _golden_gate_design(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Design Golden Gate Assembly parts with BsaI or BbsI overhangs."""
        parts = arguments.get("parts")
        if not parts or not isinstance(parts, list) or len(parts) < 2:
            return {
                "status": "error",
                "error": "parts must be a list of at least 2 DNA sequences",
            }

        enzyme = (arguments.get("enzyme") or "BsaI").upper()
        if enzyme not in ("BSAI", "BBSI"):
            return {"status": "error", "error": "enzyme must be 'BsaI' or 'BbsI'"}

        enzyme_display = "BsaI" if enzyme == "BSAI" else "BbsI"

        for i, part in enumerate(parts):
            part_upper = part.upper().replace(" ", "").replace("\n", "")
            err = self._validate_dna_sequence(part_upper)
            if err:
                return {"status": "error", "error": f"Part {i + 1}: {err}"}

        parts_clean = [p.upper().replace(" ", "").replace("\n", "") for p in parts]
        n_parts = len(parts_clean)

        # BsaI: recognition GGTCTC(1), cuts 1 nt away on top, 5 nt away on bottom
        # Creating: GGTCTCN[4bp overhang] -- part -- NGAGACC (reverse complement BsaI site)
        # BbsI: recognition GAAGAC(2), cuts 2 nt away on top, 6 nt away on bottom
        # Creating: GAAGACNN[4bp overhang] -- part -- NNGTCTTC

        complement_map = str.maketrans("ATGC", "TACG")

        def rev_comp(seq: str) -> str:
            return seq.translate(complement_map)[::-1]

        # Precomputed non-palindromic 4-mers (overhang != rev_comp(overhang))
        candidate_overhangs = [
            "AAAC",
            "AAAG",
            "AAAT",
            "AACG",
            "AACT",
            "AAGC",
            "AAGT",
            "AATC",
            "AATG",
            "ACAG",
            "ACAT",
            "ACCG",
            "ACCT",
            "ACGA",
            "ACGC",
            "ACGG",
            "ACGT",
            "ACTA",
            "ACTC",
            "ACTG",
            "AGAC",
            "AGAG",
            "AGAT",
            "AGCA",
            "AGCC",
            "AGCG",
            "AGCT",
            "AGGA",
            "AGGC",
            "AGGG",
            "AGGT",
            "AGTA",
            "AGTC",
            "AGTG",
            "ATAC",
            "ATAG",
            "ATCA",
            "ATCC",
            "ATCG",
            "ATGA",
            "ATGC",
            "ATGG",
            "ATGT",
            "ATTA",
            "ATTC",
            "ATTG",
        ]
        non_palindromic = [oh for oh in candidate_overhangs if oh != rev_comp(oh)]

        if len(non_palindromic) < n_parts + 1:
            return {
                "status": "error",
                "error": f"Cannot generate enough unique overhangs for {n_parts} parts",
            }

        overhangs = non_palindromic[: n_parts + 1]

        if enzyme == "BSAI":
            # BsaI site: GGTCTCN where N is 1 bp spacer before the overhang
            # Forward site: GGTCTCA[overhang]
            # Reverse site (at end of part): rev_comp([overhang]TGAGACC) = GGTCTCA[rev_comp(overhang)]
            fwd_site_prefix = "GGTCTCA"  # BsaI recognition + A spacer
        else:
            # BbsI site: GAAGACNN where NN is 2 bp spacer
            fwd_site_prefix = "GAAGACAA"

        parts_with_overhangs = []
        for i, part in enumerate(parts_clean):
            left_oh = overhangs[i]
            right_oh = overhangs[i + 1]

            rev_right_oh = rev_comp(right_oh)
            full_sequence = (
                fwd_site_prefix
                + left_oh
                + part
                + rev_right_oh
                + rev_comp(fwd_site_prefix)
            )

            parts_with_overhangs.append(
                {
                    "name": f"Part_{i + 1}",
                    "sequence": part,
                    "left_overhang": left_oh,
                    "right_overhang": right_oh,
                    "full_sequence": full_sequence,
                }
            )

        protocol_note = (
            f"Digest with {enzyme_display} and T4 ligase. "
            f"Cycle 25-30 times: 37°C 1 min (digest) / 16°C 1 min (ligate). "
            f"Final: 50°C 5 min, 80°C 10 min. "
            f"Overhangs are 4 bp non-palindromic sequences ensuring directional assembly."
        )

        return {
            "status": "success",
            "data": {
                "parts_with_overhangs": parts_with_overhangs,
                "overhangs": overhangs,
                "enzyme": enzyme_display,
                "protocol_note": protocol_note,
            },
        }
