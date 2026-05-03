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

# Enzyme-specific cut offset (0-based, from start of recognition sequence)
# Represents where the phosphodiester bond is cleaved on the top strand.
# E.g., EcoRI: G^AATTC → cut after position 1 → offset = 1
# EcoRV: GAT^ATC → blunt, offset = 3
# KpnI: GGTAC^C → 3' overhang, offset = 5
NEB_CUT_OFFSETS: Dict[str, int] = {
    "EcoRI": 1,  # G^AATTC  (4-base 5' overhang)
    "BamHI": 1,  # G^GATCC  (4-base 5' overhang)
    "HindIII": 1,  # A^AGCTT  (4-base 5' overhang)
    "NcoI": 1,  # C^CATGG  (4-base 5' overhang)
    "NdeI": 2,  # CA^TATG  (4-base 5' overhang)
    "XhoI": 1,  # C^TCGAG  (4-base 5' overhang)
    "XbaI": 1,  # T^CTAGA  (4-base 5' overhang)
    "SalI": 1,  # G^TCGAC  (4-base 5' overhang)
    "SmaI": 3,  # CCC^GGG  (blunt)
    "KpnI": 5,  # GGTAC^C  (4-base 3' overhang)
    "SacI": 5,  # GAGCT^C  (4-base 3' overhang)
    "ClaI": 2,  # AT^CGAT  (4-base 5' overhang, partial methylation sensitivity)
    "SpeI": 1,  # A^CTAGT  (4-base 5' overhang)
    "NotI": 2,  # GC^GGCCGC (4-base 5' overhang)
    "PstI": 5,  # CTGCA^G  (4-base 3' overhang)
    "EcoRV": 3,  # GAT^ATC  (blunt)
    "NheI": 1,  # G^CTAGC  (4-base 5' overhang)
    "MluI": 1,  # A^CGCGT  (4-base 5' overhang)
    "ApaI": 5,  # GGGCC^C  (4-base 3' overhang)
    "SphI": 5,  # GCATG^C  (4-base 3' overhang)
    "BglII": 1,  # A^GATCT  (4-base 5' overhang)
    "AgeI": 1,  # A^CCGGT  (4-base 5' overhang)
    "AscI": 2,  # GG^CGCGCC (4-base 5' overhang)
    "PacI": 5,  # TTAAT^TAA (2-base 3' overhang)
    "SfiI": 8,  # GGCCNNNN^NGGCC (3-base 3' overhang)
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
        # Strip whitespace before checking emptiness — a whitespace-only input
        # is truthy but produces an empty sequence after cleaning.
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        enzymes_requested = arguments.get("enzymes")
        # Support circular DNA: search a doubled sequence to catch sites that
        # span the origin of the molecule.
        circular = bool(arguments.get("circular", False))

        # Use `is not None` instead of truthiness: an empty list [] is explicitly
        # "no enzymes requested" and must not silently fall through to all enzymes.
        if enzymes_requested is not None:
            if isinstance(enzymes_requested, str):
                enzymes_requested = [enzymes_requested]
            if not enzymes_requested:
                return {
                    "status": "error",
                    "error": (
                        "enzymes list is empty. Provide at least one enzyme name, "
                        f"or omit the parameter to search all available enzymes: "
                        f"{sorted(NEB_ENZYMES.keys())}"
                    ),
                }
            # Case-insensitive normalization: enzyme names like "ecori", "ECORI",
            # or "EcoRi" are silently mapped to the canonical form "EcoRI".
            _neb_lower = {name.lower(): name for name in NEB_ENZYMES}
            normalized_requested = []
            unknown_enzymes = []
            for e in enzymes_requested:
                if e in NEB_ENZYMES:
                    normalized_requested.append(e)
                elif e.lower() in _neb_lower:
                    normalized_requested.append(_neb_lower[e.lower()])
                else:
                    unknown_enzymes.append(e)
            # Previously the whole call failed when ANY enzyme was unknown,
            # discarding results for valid enzymes.  Now: proceed with recognized enzymes
            # and report unknown ones in a warning.  Only fail if ALL are unknown.
            if unknown_enzymes and not normalized_requested:
                return {
                    "status": "error",
                    "error": f"Unknown enzymes: {unknown_enzymes}. Available: {sorted(NEB_ENZYMES.keys())}",
                }
            enzyme_dict = {name: NEB_ENZYMES[name] for name in normalized_requested}
        else:
            enzyme_dict = NEB_ENZYMES
            unknown_enzymes = []

        seq_len = len(sequence)
        # For circular DNA, search the doubled sequence to detect sites that
        # wrap around the origin. Only positions 0..seq_len-1 are collected
        # (positions ≥ seq_len are duplicates of non-wrapping sites).
        search_seq = (sequence + sequence) if circular else sequence

        results = {}
        for enzyme_name, recognition_seq in enzyme_dict.items():
            if "N" in recognition_seq:
                pattern = recognition_seq.replace("N", "[ATGC]")
                if circular:
                    positions = [
                        m.start() + 1
                        for m in re.finditer(f"(?={pattern})", search_seq)
                        if m.start() < seq_len
                    ]
                else:
                    positions = [
                        m.start() + 1 for m in re.finditer(f"(?={pattern})", search_seq)
                    ]
            else:
                positions = []
                start = 0
                while True:
                    pos = search_seq.find(recognition_seq, start)
                    if pos == -1:
                        break
                    if circular and pos >= seq_len:
                        break  # stop at duplicates
                    positions.append(pos + 1)  # 1-based
                    start = pos + 1

            cut_off = NEB_CUT_OFFSETS.get(enzyme_name, len(recognition_seq) // 2)
            if positions:
                # `cut_sites` reports 1-based recognition sequence start
                # positions, NOT the actual phosphodiester bond cleavage positions.
                # For enzymes like KpnI (GGTAC^C, cut_offset=5), the difference is 4 bp.
                # Add `cleavage_positions` (1-based) so callers can determine the exact
                # cut site without having to look up enzyme-specific offsets.
                cleavage_pos = sorted(
                    set(((p - 1 + cut_off) % seq_len) + 1 for p in positions)
                )
                results[enzyme_name] = {
                    "recognition_sequence": recognition_seq,
                    "cut_sites": positions,  # 1-based recognition site START positions
                    "cleavage_positions": cleavage_pos,  # 1-based actual CUT positions
                    "num_cuts": len(positions),
                }
            elif enzymes_requested:
                # Explicitly requested enzymes that find 0 sites were
                # previously absent from enzymes_with_sites entirely.  A caller
                # doing results["enzymes_with_sites"]["EcoRI"] would get a KeyError
                # with no way to distinguish "not requested" from "0 sites found."
                # Only applies when user specified an enzyme list; all-enzyme scans
                # (enzymes=None) skip this to avoid 100+ empty entries.
                results[enzyme_name] = {
                    "recognition_sequence": recognition_seq,
                    "cut_sites": [],
                    "cleavage_positions": [],
                    "num_cuts": 0,
                }

        data = {
            "sequence_length": seq_len,
            "enzymes_with_sites": results,
            "enzymes_cutting": sorted(
                k for k, v in results.items() if v["num_cuts"] > 0
            ),
            "num_enzymes_cutting": sum(
                1 for v in results.values() if v["num_cuts"] > 0
            ),
        }
        if unknown_enzymes:
            data["unknown_enzymes_warning"] = (
                f"The following enzyme name(s) were not recognized and were skipped: "
                f"{unknown_enzymes}. Check spelling or see available enzymes in the "
                "enzyme_list operation."
            )
        if circular:
            data["circular"] = True

        return {
            "status": "success",
            "data": data,
        }

    def _find_orfs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find open reading frames (ORFs) in a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        min_length = arguments.get("min_length", 100)  # minimum nt length
        try:
            min_length = int(min_length)
        except (ValueError, TypeError):
            return {
                "status": "error",
                "error": "min_length must be a non-negative integer",
            }
        if min_length < 0:
            return {
                "status": "error",
                "error": f"min_length ({min_length}) must be non-negative. "
                "A negative minimum length is biologically meaningless.",
            }
        strand = arguments.get("strand", "both")  # "forward", "reverse", "both"

        # Validate strand parameter: case-sensitive match required.
        # An invalid value (e.g., "BOTH", "Forward") silently returns 0 ORFs.
        _valid_strands = ("forward", "reverse", "both")
        if strand not in _valid_strands:
            return {
                "status": "error",
                "error": (
                    f"Invalid strand value '{strand}'. "
                    "Must be 'forward', 'reverse', or 'both' (case-sensitive)."
                ),
            }

        _STOP_SET = {"TAA", "TAG", "TGA"}

        def find_orfs_in_sequence(seq: str, is_reverse: bool = False):
            """Scan all three reading frames using a state-machine (open/closed).

            Note: Uses a greedy open/close state machine — opens at the first ATG
            in each frame and closes at the first in-frame stop codon. Nested ORFs
            (ATG codons embedded within an already-open reading frame) are not
            detected; only the outermost ORF starting at the earliest ATG is
            reported per reading frame.

            Returns: (closed_orfs, open_orf_starts)
              - closed_orfs: list of ORFs that have an in-frame stop codon
              - open_orf_starts: list of (frame, start_1based) for ORFs with no stop
            """
            orfs = []
            open_starts = []
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
                                # For minus-strand ORFs, report the reading frame at the 5'
                                # end of the ORF in plus-strand coordinates (GFF convention).
                                # The 5' end on the minus strand is coord_end (the highest
                                # plus-strand coordinate, where the ATG resides).
                                # frame = (coord_end - 1) % 3 + 1 (1-based).
                                # For plus-strand ORFs, frame_offset + 1 equals
                                # (coord_start - 1) % 3 + 1, which is already correct.
                                _orf_frame = (
                                    (coord_end - 1) % 3 + 1
                                    if is_reverse
                                    else frame_offset + 1
                                )
                                orf_entry = {
                                    "start": coord_start,
                                    "end": coord_end,
                                    "length_nt": orf_nt_len,
                                    "length_aa": orf_nt_len // 3 - 1,
                                    "frame": _orf_frame,
                                    "strand": strand_label,
                                    "sequence": seq[orf_start_idx : pos + 3],
                                }
                                if is_reverse:
                                    # For minus-strand ORFs, `start` and `end`
                                    # are 1-based plus-strand coordinates (standard GFF/GTF
                                    # convention: start < end, strand='-').
                                    # `original_seq[start-1:end]` gives the PLUS-strand
                                    # region, NOT the ORF.  The ORF is its reverse complement.
                                    # The `sequence` field already contains the correct ORF
                                    # (read 5'→3' on the minus strand).
                                    orf_entry["coordinate_note"] = (
                                        "Coordinates (start, end) are 1-based plus-strand "
                                        "positions (GFF convention). To extract the ORF from "
                                        "the original sequence: reverse_complement(seq[start-1:end]). "
                                        "The 'sequence' field already contains the ORF."
                                    )
                                orfs.append(orf_entry)
                            orf_open = False
                    pos += 3

                # After exhausting all codons in this frame: if orf_open is still
                # True, the ORF started but never encountered an in-frame stop codon.
                # This is a truncated/open ORF — record it so callers are informed.
                if orf_open:
                    partial_len = seq_len - orf_start_idx
                    if partial_len >= min_length:
                        if is_reverse:
                            # Was `seq_len - orf_start_idx` which is the
                            # GFF END (highest plus-strand coordinate = last base of ATG).
                            # Convention for closed minus-strand ORFs uses
                            # coord_start = GFF start (lower bound, consistent with GFF).
                            # The GFF start of the ATG is:
                            #   seq_len - (orf_start_idx + 3) + 1 = seq_len - orf_start_idx - 2
                            open_coord = (
                                seq_len - orf_start_idx - 2
                            )  # 1-based GFF start
                        else:
                            open_coord = orf_start_idx + 1  # 1-based start
                        # For minus-strand open ORFs, derive the GFF-convention reading
                        # frame from the ATG's highest plus-strand coordinate:
                        #   atg_coord_end = seq_len - orf_start_idx
                        #   frame = (atg_coord_end - 1) % 3 + 1
                        # This is identical to (seq_len - orf_start_idx - 1) % 3 + 1.
                        _open_frame = (
                            (seq_len - orf_start_idx - 1) % 3 + 1
                            if is_reverse
                            else frame_offset + 1
                        )
                        open_starts.append(
                            {
                                "frame": _open_frame,
                                "strand": strand_label,
                                "start": open_coord,
                                "partial_length_nt": partial_len,
                            }
                        )
            return orfs, open_starts

        all_orfs = []
        all_open_starts = []

        if strand in ("forward", "both"):
            closed, opens = find_orfs_in_sequence(sequence, is_reverse=False)
            all_orfs.extend(closed)
            all_open_starts.extend(opens)

        if strand in ("reverse", "both"):
            rev_comp = sequence.translate(COMPLEMENT)[::-1]
            closed, opens = find_orfs_in_sequence(rev_comp, is_reverse=True)
            all_orfs.extend(closed)
            all_open_starts.extend(opens)

        all_orfs.sort(key=lambda x: x["length_nt"], reverse=True)

        total_found = len(all_orfs)
        displayed = all_orfs[:50]

        data = {
            "sequence_length": len(sequence),
            "min_length_nt": min_length,
            "num_orfs_found": total_found,
            "orfs": displayed,
        }
        # Warn when the result list is truncated: num_orfs_found > 50 but only
        # 50 entries are returned, which would appear as missing results.
        if total_found > 50:
            data["results_truncated"] = True
            data["results_truncated_note"] = (
                f"Only the 50 longest ORFs are shown out of {total_found} found. "
                "num_orfs_found reflects the full count."
            )
        # Warn about open ORFs (no in-frame stop codon before end of sequence).
        # These are common in partial transcripts, incomplete assemblies, or
        # CDS sequences deliberately lacking a stop codon.
        if all_open_starts:
            data["open_orfs_warning"] = (
                f"{len(all_open_starts)} open ORF(s) detected "
                f"(ATG with no in-frame stop codon before end of sequence): "
                + ", ".join(
                    f"frame {o['frame']} strand {o['strand']} at position {o['start']} "
                    f"({o['partial_length_nt']} nt partial)"
                    for o in all_open_starts
                )
                + ". These may be truncated sequences or CDSs lacking a stop codon."
            )

        return {"status": "success", "data": data}

    def _calculate_gc_content(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate GC content and nucleotide composition of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
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

        # When effective_length == 0 (all-N sequence), GC content is undefined —
        # reporting "Low GC" (gc_content == 0) is scientifically incorrect.
        if effective_total == 0:
            interpretation = "Undefined (no ATGC bases)"
        elif gc_content > 60:
            interpretation = "High GC"
        elif gc_content < 40:
            interpretation = "Low GC"
        else:
            interpretation = "Normal GC"

        # For all-N sequences, gc_content_percent is scientifically
        # undefined (not zero). Return None so callers are not misled into thinking
        # the sequence has 0% GC (i.e., is AT-rich).
        gc_pct = None if effective_total == 0 else round(gc_content, 2)
        at_pct = (
            None if effective_total == 0 else round(at_count / effective_total * 100, 2)
        )

        return {
            "status": "success",
            "data": {
                "gc_content_percent": gc_pct,
                "at_content_percent": at_pct,
                "nucleotide_counts": counts,
                "sequence_length": total,
                "effective_length": effective_total,
                "interpretation": interpretation,
            },
        }

    def _reverse_complement(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generate the reverse complement of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
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
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
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
            # Sequences shorter than 3 nt trim to 0 nt and produce a
            # success response with an empty protein.  Fail explicitly instead.
            if trimmed_len == 0:
                return {
                    "status": "error",
                    "error": (
                        f"Sequence length {len(sequence)} is too short to contain a "
                        "complete codon. At least 3 nucleotides are required for translation."
                    ),
                }
            sequence_trimmed = sequence[:trimmed_len]
            warning = f"Sequence length {len(sequence)} is not divisible by 3; trimmed to {trimmed_len} nt"
        else:
            sequence_trimmed = sequence
            warning = None

        # Warn when the sequence does not start with ATG.
        # A non-ATG start is unusual for a canonical CDS and may indicate a
        # partial sequence, mis-framing, or non-coding input.  Report a warning
        # rather than silently returning a protein starting with a non-Met residue.
        non_atg_warning = None
        if len(sequence_trimmed) >= 3 and sequence_trimmed[:3] != "ATG":
            first_codon = sequence_trimmed[:3]
            first_aa = STANDARD_CODON_TABLE.get(first_codon, "X")
            if first_aa == "*":
                # First codon is a stop → protein will be empty.
                # Emit a dedicated warning so callers are not silently given "".
                non_atg_warning = (
                    f"First codon '{first_codon}' is a stop codon; the protein_sequence "
                    "field will be empty. The sequence may be reversed, mis-framed, "
                    "or contain a premature stop at position 1."
                )
            else:
                non_atg_warning = (
                    f"Sequence does not start with ATG (start codon); "
                    f"first codon is '{first_codon}' ({first_aa}). "
                    "This is unusual for a canonical CDS. The protein may be "
                    "incorrect if the input is a partial or mis-framed sequence."
                )

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

        premature_stop_warning = None
        if "*" in protein_seq:
            first_stop = protein_seq.index("*")
            protein_seq_no_stop = protein_seq[:first_stop]
            # When sequence starts with ATG but has an internal stop codon
            # (not at the last codon position), warn that the stop is premature.
            # Previously, only non-ATG starts triggered a warning; ATG starts with
            # an internal stop were silently returned with post-stop codons visible
            # in full_translation but no explanation of the truncation.
            n_total_codons = len(sequence_trimmed) // 3
            first_stop_codon_pos = first_stop + 1  # 1-based
            # `and non_atg_warning is None` silently suppressed
            # premature_stop_warning whenever the start codon was non-ATG — even for
            # genuine internal stop codons (e.g. a GTG-start CDS with a nonsense
            # mutation).  Both warnings can coexist: the non_atg warning flags the
            # start; the premature_stop warns that translation terminates early.
            if first_stop_codon_pos < n_total_codons:
                premature_stop_warning = (
                    f"Premature stop codon at position {first_stop_codon_pos} "
                    f"(of {n_total_codons} codons). Translation terminates at "
                    f"'{sequence_trimmed[(first_stop) * 3 : (first_stop) * 3 + 3]}'. "
                    "Downstream codons are shown in full_translation but are not "
                    "translated. This may indicate mis-framing, a nonsense mutation, "
                    "or an incorrect sequence."
                )
            # Stop_codons_found and stop_codon_positions previously counted
            # ALL stop codons in the full scan, including those after the first stop.
            # Biologically, the ribosome terminates at the first stop; downstream stop
            # codons are irrelevant.  Truncate to only the first stop codon.
            stop_positions_reported = stop_positions[:1]
        else:
            protein_seq_no_stop = protein_seq
            stop_positions_reported = []

        # Check for ambiguous 'X' residues in the translated
        # protein.  STANDARD_CODON_TABLE.get(codon, 'X') silently returns 'X' for
        # any codon not in the table (e.g. NNN, NAA, ANT, etc.).  No warning was
        # issued, so callers received a protein with unknown residues without any
        # indication of which positions are ambiguous.
        ambiguous_codon_warning = None
        _x_positions = [
            i + 1  # 1-based codon position
            for i, aa in enumerate(protein_seq_no_stop)
            if aa == "X"
        ]
        if _x_positions:
            _ambig_codons = [
                sequence_trimmed[(p - 1) * 3 : (p - 1) * 3 + 3] for p in _x_positions
            ]
            ambiguous_codon_warning = (
                f"Ambiguous codon(s) at position(s) {_x_positions} "
                f"(codons: {_ambig_codons}) translated to 'X' (unknown amino acid). "
                "These positions contain IUPAC ambiguity bases (N, R, Y, etc.) or "
                "non-standard nucleotides not in the codon table. "
                "The protein sequence may be incomplete or incorrect at these positions."
            )

        result = {
            "status": "success",
            "data": {
                "dna_sequence": sequence_trimmed,
                "protein_sequence": protein_seq_no_stop,
                "full_translation": protein_seq,
                "protein_length_aa": len(protein_seq_no_stop),
                "stop_codons_found": len(stop_positions_reported),
                "stop_codon_positions": stop_positions_reported,
                "codon_table": codon_table_name,
            },
        }
        if warning:
            result["data"]["warning"] = warning
        if non_atg_warning:
            result["data"]["non_atg_start_warning"] = non_atg_warning
        if premature_stop_warning:
            result["data"]["premature_stop_warning"] = premature_stop_warning
        if ambiguous_codon_warning:
            result["data"]["ambiguous_codon_warning"] = ambiguous_codon_warning

        return result

    def _codon_optimize(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Codon-optimize an amino acid sequence for expression in a target species."""
        sequence = arguments.get("sequence", "")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().strip()
        # Re-check after stripping: a whitespace-only sequence passes the initial
        # `if not sequence:` guard (non-empty string is truthy) but becomes empty
        # after strip(), producing a success response with an empty DNA sequence.
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is empty or contains only whitespace. Provide a valid amino acid sequence.",
            }
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

        # The single-letter amino acid codes A, T, G, C are
        # identical to DNA nucleotide characters.  A user who mistakenly passes a DNA CDS
        # (e.g., 'ATGAAATTT' = coding sequence for Met-Lys-Phe) instead of a protein
        # sequence ('MKF') will get a silent success: the 9 nucleotides are treated as 9
        # amino acids, producing a 27 bp "optimized" sequence that is completely wrong.
        # Detect the pattern: sequence consists only of A/T/G/C, is divisible by 3, and
        # starts with ATG (canonical Met start) — all hallmarks of a DNA CDS input.
        _dna_only = set(sequence) <= set("ATGC")
        _looks_like_cds = (
            _dna_only
            and len(sequence) % 3 == 0
            and sequence.startswith("ATG")
            and len(sequence) >= 9  # at least 3 codons to avoid false positives
        )
        _dna_aa_warning = None
        if _looks_like_cds:
            _dna_aa_warning = (
                f"Input sequence '{sequence[:20]}{'...' if len(sequence) > 20 else ''}' "
                "consists only of A, T, G, C characters and starts with ATG — this looks "
                "like a DNA CDS rather than a protein sequence. "
                "codon_optimize expects single-letter amino acid codes (e.g., 'MKF'). "
                "If you have a DNA CDS, use DNA_translate_sequence first to get the "
                "protein sequence, then pass that to codon_optimize."
            )

        # Validate stop codon placement: * is only allowed as the final residue.
        # An internal stop codon (*) would produce a truncated, non-functional protein.
        stop_positions = [i for i, aa in enumerate(sequence) if aa == "*"]
        if stop_positions:
            internal_stops = [p for p in stop_positions if p != len(sequence) - 1]
            if internal_stops:
                return {
                    "status": "error",
                    "error": (
                        f"Internal stop codon(s) (*) at position(s) "
                        f"{[p + 1 for p in internal_stops]} (1-indexed). "
                        "Stop codons are only permitted at the terminal position of the sequence."
                    ),
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
            # Exclude stop codons from CAI: CAI is defined only for sense codons.
            # Stop codons are not present in CAI reference tables; including them
            # with a default value of 1.0 would inflate the score.
            if aa != "*":
                cai_values.append(cai_table.get(codon, 1.0))

        optimized_dna = "".join(dna_codons)
        length_bp = len(optimized_dna)

        gc = sum(1 for b in optimized_dna if b in "GC")
        gc_content = round(gc / length_bp * 100, 2) if length_bp > 0 else 0.0

        if cai_values:
            log_sum = sum(math.log(v) for v in cai_values if v > 0)
            cai = round(math.exp(log_sum / len(cai_values)), 4)
        else:
            # CAI = 0.0 is misleading for stop-codon-only sequences.
            # CAI is defined only for sense codons; a sequence with no sense codons
            # (e.g., a single "*") has an undefined CAI, not a CAI of 0.
            cai = None

        result_data = {
            "optimized_dna": optimized_dna,
            "gc_content": gc_content,
            "cai": cai,
            # Add explanatory note clarifying why CAI is always 1.0.
            # This tool selects the single highest-frequency codon for every amino
            # acid, which by definition has a CAI reference value of 1.0.  The
            # resulting sequence always achieves the maximum CAI possible.  To
            # compare your original sequence against the optimized one, calculate
            # the CAI of the original sequence using an external tool (e.g., the
            # OPTIMIZER web server or CAI2 Python package).
            "cai_note": (
                "CAI = 1.0 is expected: this tool selects the highest-frequency "
                f"codon for each amino acid in {species}. To assess how much "
                "your original sequence differed, compute its CAI independently."
            )
            if cai is not None
            else None,
            "length_bp": length_bp,
        }
        # Add warning when input looks like a DNA CDS rather than protein.
        if _dna_aa_warning:
            result_data["dna_input_warning"] = _dna_aa_warning
        return {"status": "success", "data": result_data}

    def _virtual_digest(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Perform a virtual restriction digest of a DNA sequence."""
        sequence = arguments.get("sequence", "")
        if not sequence or not sequence.strip():
            return {"status": "error", "error": "sequence is required"}

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        enzymes_requested = arguments.get("enzymes")
        circular = bool(arguments.get("circular", False))

        # Use `is not None` instead of truthiness: an empty list [] must not
        # silently fall through to using all NEB enzymes.
        if enzymes_requested is not None:
            if isinstance(enzymes_requested, str):
                enzymes_requested = [enzymes_requested]
            if not enzymes_requested:
                return {
                    "status": "error",
                    "error": (
                        "enzymes list is empty. Provide at least one enzyme name, "
                        f"or omit the parameter to digest with all available enzymes: "
                        f"{sorted(NEB_ENZYMES.keys())}"
                    ),
                }
            # Case-insensitive normalization: "ecori" → "EcoRI", etc.
            _neb_lower = {name.lower(): name for name in NEB_ENZYMES}
            normalized_requested = []
            unknown_enzymes = []
            for e in enzymes_requested:
                if e in NEB_ENZYMES:
                    normalized_requested.append(e)
                elif e.lower() in _neb_lower:
                    normalized_requested.append(_neb_lower[e.lower()])
                else:
                    unknown_enzymes.append(e)
            # Same as _find_restriction_sites — proceed with valid enzymes.
            if unknown_enzymes and not normalized_requested:
                return {
                    "status": "error",
                    "error": f"Unknown enzymes: {unknown_enzymes}. Available: {sorted(NEB_ENZYMES.keys())}",
                }
            enzyme_dict = {name: NEB_ENZYMES[name] for name in normalized_requested}
        else:
            enzyme_dict = NEB_ENZYMES
            unknown_enzymes = []

        # Search a doubled sequence for circular DNA to detect recognition
        # sites that straddle the origin.  This mirrors the logic in _find_restriction_sites.
        # For linear DNA, search_seq == sequence and all positions are valid.
        # For circular DNA, we search the doubled sequence but only keep positions
        # where pos < seq_len (sites that START within the original sequence).  Cut
        # positions ≥ seq_len are wrapped back into [0, seq_len) via modulo so that the
        # fragment-building code (which always works in [0, seq_len]) remains correct.
        seq_len = len(sequence)  # must be defined before search_seq loop below
        search_seq = (sequence + sequence) if circular else sequence
        cut_sites_list = []
        enzymes_used = []
        for enzyme_name, recognition_seq in enzyme_dict.items():
            if "N" in recognition_seq:
                pattern = recognition_seq.replace("N", "[ATGC]")
                positions = [
                    m.start()
                    for m in re.finditer(f"(?={pattern})", search_seq)
                    if m.start() < seq_len
                ]
            else:
                positions = []
                start = 0
                while True:
                    pos = search_seq.find(recognition_seq, start)
                    if pos == -1 or pos >= seq_len:
                        break
                    positions.append(pos)
                    start = pos + 1

            # Use enzyme-specific cut offset; default to midpoint if unknown
            cut_offset = NEB_CUT_OFFSETS.get(enzyme_name, len(recognition_seq) // 2)
            for pos in positions:
                cut_pos = (pos + cut_offset) % seq_len  # wrap into [0, seq_len)
                cut_sites_list.append({"enzyme": enzyme_name, "position": cut_pos})

            if positions:
                enzymes_used.append(enzyme_name)

        cut_sites_list.sort(key=lambda x: x["position"])
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
                        wrap = False
                    else:
                        # When start >= end the fragment spans the circular
                        # origin.  This includes the single-cut case (start == end)
                        # where the single fragment is the full circular sequence.
                        # is_wrap_around=True tells the caller that coordinates are
                        # non-contiguous in linear notation (start..end_of_sequence
                        # + beginning_of_sequence..end).
                        frag_seq = sequence[start:] + sequence[:end]
                        wrap = True
                    frag_entry = {
                        "sequence": frag_seq,
                        "length": len(frag_seq),
                        "start": start,
                        "end": end,
                        "is_wrap_around": wrap,
                    }
                    if wrap:
                        # For wrap-around fragments (is_wrap_around=True),
                        # seq[start:end] is NOT a valid Python slice because end <= start.
                        # When start==end (single-cut: e.g., cut at position 0), seq[0:0]
                        # returns an empty string. The correct extraction is always:
                        #   seq[start:] + seq[:end]
                        # which the `sequence` field already contains.  Add a note so
                        # callers know to use sequence directly or the prescribed slice.
                        frag_entry["coordinate_note"] = (
                            f"For this wrap-around fragment use: "
                            f"seq[{start}:] + seq[:{end}] (not seq[{start}:{end}]). "
                            "The `sequence` field contains the pre-extracted fragment."
                        )
                    fragments.append(frag_entry)
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
        """Calculate melting temperature using SantaLucia 1998 nearest-neighbor model.

        Uses terminal-specific initiation parameters (SantaLucia 1998, Table 2):
          GC terminal: dH = +0.1 kcal/mol, dS = -2.8 cal/mol/K (per end)
          AT terminal: dH = +2.3 kcal/mol, dS = +4.1 cal/mol/K (per end)
        Applied to both the 5' and 3' terminal base pairs.

        Requires a fully-resolved sequence (no ambiguous bases).  N-containing
        dinucleotides are absent from NN_PARAMS; silently skipping them
        underestimates dH/dS and produces an erroneously low Tm.
        Returns 0.0 for sequences containing N (same sentinel as length < 2).
        """
        seq = primer.upper()
        n = len(seq)
        if n < 2:
            return 0.0

        # Ambiguous bases: thermodynamic parameters are undefined for N-containing
        # dinucleotides.  Return 0.0 to signal failure rather than silently computing
        # a drastically underestimated Tm from only the N-free portion of the sequence.
        if "N" in seq:
            return 0.0

        dH = 0.0  # kcal/mol
        dS = 0.0  # cal/mol/K

        # Terminal-specific initiation corrections (SantaLucia 1998, Table 2)
        # Applied once for each end (5' terminal and 3' terminal base pair)
        for terminal_base in (seq[0], seq[-1]):
            if terminal_base in "GC":
                dH += 0.1
                dS += -2.8
            else:  # A or T terminal
                dH += 2.3
                dS += 4.1

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

        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\t", "")
        error = self._validate_dna_sequence(sequence)
        if error:
            return {"status": "error", "error": error}

        seq_len = len(sequence)
        target_start = arguments.get("target_start")
        target_end = arguments.get("target_end")
        # Use explicit None checks: Python's `x or default` treats 0 as falsy,
        # silently replacing a user-supplied 0 with the default value.
        _tm_raw = arguments.get("tm_target")
        tm_target = float(_tm_raw if _tm_raw is not None else 60.0)
        _psmin_raw = arguments.get("product_size_min")
        product_size_min = int(_psmin_raw if _psmin_raw is not None else 100)
        _psmax_raw = arguments.get("product_size_max")
        product_size_max = int(_psmax_raw if _psmax_raw is not None else 1000)
        # GC filter bounds in percentage (0–100). Previously hardcoded as 40–60;
        # now read from arguments so callers can override (e.g., gc_min=55, gc_max=70
        # for high-GC amplicons).
        gc_min_pct = (
            float(arguments["gc_min"]) if arguments.get("gc_min") is not None else 40.0
        )
        gc_max_pct = (
            float(arguments["gc_max"]) if arguments.get("gc_max") is not None else 60.0
        )
        # Validate GC bounds: must be in [0, 100] and gc_min ≤ gc_max.
        if not (0 <= gc_min_pct <= 100) or not (0 <= gc_max_pct <= 100):
            return {
                "status": "error",
                "error": (
                    f"gc_min ({gc_min_pct}) and gc_max ({gc_max_pct}) must be in "
                    "[0, 100] (percentage units)."
                ),
            }
        if gc_min_pct > gc_max_pct:
            return {
                "status": "error",
                "error": (f"gc_min ({gc_min_pct}) must be ≤ gc_max ({gc_max_pct})."),
            }

        # Validate product size constraints upfront to give a clear error message.
        # Without this check, the user gets a confusing "Designed product size (N)
        # is outside the range [min, max]" message when min > max.
        if product_size_min > product_size_max:
            return {
                "status": "error",
                "error": (
                    f"product_size_min ({product_size_min}) must be <= "
                    f"product_size_max ({product_size_max})."
                ),
            }

        # Target_start beyond the sequence silently clamps target_end to
        # seq_len and produces a confusing "Target region (-N bp) is smaller than
        # product_size_min" error.  Detect and report out-of-bounds target_start early.
        if target_start is not None and int(target_start) >= seq_len:
            return {
                "status": "error",
                "error": (
                    f"target_start ({int(target_start)}) is at or beyond the sequence "
                    f"length ({seq_len} bp). target_start must be a 0-based index less "
                    "than the sequence length."
                ),
            }

        # Validate target coordinates before clamping: if target_start > target_end,
        # the region size becomes negative and produces a confusing error downstream.
        if target_start is not None and target_end is not None:
            t_start_raw = int(target_start)
            t_end_raw = int(target_end)
            if t_start_raw > t_end_raw:
                return {
                    "status": "error",
                    "error": (
                        f"target_start ({t_start_raw}) must be less than or equal to "
                        f"target_end ({t_end_raw})."
                    ),
                }

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
                # Skip primers containing N bases: NN thermodynamic parameters
                # are undefined for ambiguous bases, causing underestimated Tm.
                if "N" in primer:
                    continue
                gc = gc_content(primer)
                if gc < gc_min_pct or gc > gc_max_pct:
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
                # Skip if the template (or its complement) contains N bases
                if "N" in rev_primer:
                    continue
                gc = gc_content(rev_primer)
                if gc < gc_min_pct or gc > gc_max_pct:
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

        # Reject primers that overlap on the template: the forward primer ends at
        # fwd.start + fwd.length, and the reverse primer starts at rev.end - rev.length.
        # If fwd.end > rev.start, both primers anneal to the same (or overlapping)
        # template region, making PCR amplification impossible (primer dimers).
        fwd_end = best_fwd["start"] + best_fwd["length"]
        rev_start = best_rev["end"] - best_rev["length"]
        if fwd_end > rev_start:
            return {
                "status": "error",
                "error": (
                    f"Could not design a non-overlapping primer pair for the specified region. "
                    f"The best forward primer ends at position {fwd_end} but the best reverse "
                    f"primer starts at position {rev_start}, causing overlap. "
                    "Try increasing product_size_min, widening the target region, or using a longer sequence."
                ),
            }

        if product_size < product_size_min or product_size > product_size_max:
            return {
                "status": "error",
                "error": f"Designed product size ({product_size} bp) is outside the range [{product_size_min}, {product_size_max}] bp",
            }

        # Verify the product actually spans the requested target region.
        # Primer search windows are centered ±50 bp around target_start/target_end, so
        # when the target falls near a sequence boundary the best primers may sit
        # entirely before (or after) the target, producing a valid product that misses
        # the declared target. Detect and report instead of silently returning wrong coords.
        #
        # Skip the coverage check when the user requested full-sequence
        # amplification (target_start == 0 and target_end == seq_len).  In that case
        # the boundary conditions (fwd.start ≤ 0 and rev.end ≥ seq_len) can never both
        # be satisfied simultaneously — no primer can start before position 0 or end
        # after the last base.  Any valid primer pair covering the majority of the
        # sequence is acceptable for full-sequence amplification.
        is_full_sequence = target_start == 0 and target_end == seq_len
        if not is_full_sequence and (
            best_fwd["start"] > target_start or best_rev["end"] < target_end
        ):
            return {
                "status": "error",
                "error": (
                    f"Could not design a primer pair that fully spans the target region "
                    f"[{target_start}, {target_end}]. "
                    f"Best candidate product [{best_fwd['start']}, {best_rev['end']}] "
                    f"does not cover the target. "
                    "Try widening the target region, relaxing primer constraints, or using a longer sequence."
                ),
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

        circular = bool(arguments.get("circular", True))
        # Explicit None check: `int(0 or 20)` = 20, silently ignoring user-supplied 0.
        _ol_raw = arguments.get("overlap_length")
        overlap_length = int(_ol_raw if _ol_raw is not None else 20)
        if overlap_length < 1:
            return {"status": "error", "error": "overlap_length must be at least 1"}

        for i, frag in enumerate(fragments):
            frag_upper = (
                frag.upper().replace(" ", "").replace("\n", "").replace("\t", "")
            )
            err = self._validate_dna_sequence(frag_upper)
            if err:
                return {"status": "error", "error": f"Fragment {i + 1}: {err}"}
            if len(frag_upper) <= overlap_length:
                return {
                    "status": "error",
                    "error": f"Fragment {i + 1} (length {len(frag_upper)}) must be longer than overlap_length ({overlap_length})",
                }

        fragments_clean = [
            f.upper().replace(" ", "").replace("\n", "").replace("\t", "")
            for f in fragments
        ]
        n = len(fragments_clean)
        assembly_fragments = []

        for i, frag in enumerate(fragments_clean):
            # For circular assemblies every fragment has a successor; for linear
            # assemblies the last fragment is the terminus and has no right overlap
            # (adding one would produce incorrect PCR products).
            is_last_linear = (not circular) and (i == n - 1)

            if is_last_linear:
                next_frag = None
            else:
                next_frag = fragments_clean[(i + 1) % n]

            # Overlap convention: the overlap at each junction is the first
            # overlap_length bases of the RIGHT fragment (next_frag).
            # - left_overlap: first N bases of this fragment — shared with the
            #   previous fragment's right overlap; no extra left primer tail needed.
            # - right_overlap: first N bases of the next fragment — added to this
            #   fragment's PCR product via the right primer 5'-tail.
            # Consistency check: Fragment i's right_overlap == Fragment i+1's
            #   left_overlap (both equal next_frag[:overlap_length]). ✓
            left_overlap = frag[:overlap_length]
            if next_frag is not None:
                right_overlap = next_frag[:overlap_length]
                # PCR product = this fragment's body + right primer overhang tail
                with_overlaps = frag + right_overlap
            else:
                # Linear terminus: no right primer tail
                right_overlap = ""
                with_overlaps = frag

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
                "topology": "circular" if circular else "linear",
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
            part_upper = (
                part.upper().replace(" ", "").replace("\n", "").replace("\t", "")
            )
            if len(part_upper) == 0:
                return {
                    "status": "error",
                    "error": f"Part {i + 1} is empty. All parts must contain at least one nucleotide.",
                }
            err = self._validate_dna_sequence(part_upper)
            if err:
                return {"status": "error", "error": f"Part {i + 1}: {err}"}

        parts_clean = [
            p.upper().replace(" ", "").replace("\n", "").replace("\t", "")
            for p in parts
        ]
        n_parts = len(parts_clean)

        # Check for internal recognition sites in part sequences.
        # During assembly, the restriction enzyme cuts every recognition site in the
        # reaction — including any site inside an insert — producing incorrect fragments.
        if enzyme == "BSAI":
            rec_seqs = [("GGTCTC", "forward"), ("GAGACC", "reverse complement")]
        else:
            rec_seqs = [("GAAGAC", "forward"), ("GTCTTC", "reverse complement")]

        internal_site_errors = []
        for i, part in enumerate(parts_clean):
            for rec_seq, direction in rec_seqs:
                if rec_seq in part:
                    internal_site_errors.append(
                        f"Part {i + 1} contains an internal {enzyme_display} "
                        f"recognition site ({rec_seq}, {direction} strand) at position "
                        f"{part.index(rec_seq)}. The enzyme will cut within this insert "
                        "during assembly, producing incorrect fragments."
                    )
        if internal_site_errors:
            return {
                "status": "error",
                "error": (
                    f"Golden Gate design failed — internal {enzyme_display} sites "
                    f"detected in {len(internal_site_errors)} location(s). "
                    "Remove or mutate these sites before assembly: "
                    + " | ".join(internal_site_errors)
                ),
            }

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
        # Filter to non-palindromic, non-RC-complement overhangs.
        # Two conditions must hold for safe Golden Gate assembly:
        #   (1) oh != rev_comp(oh)  — palindromic overhangs self-ligate
        #   (2) no two selected overhangs are RC complements of each other
        #       — if oh_A == rev_comp(oh_B), junction A can mis-ligate to
        #         junction B, producing incorrect assembly products
        rc_free_overhangs: List[str] = []
        used_set: set = set()
        for oh in candidate_overhangs:
            if oh in used_set:
                # This overhang's reverse complement was already selected —
                # adding it would introduce an RC-complement pair.
                continue
            rc_oh = rev_comp(oh)
            if oh == rc_oh:
                continue  # palindrome — self-ligates, skip
            rc_free_overhangs.append(oh)
            used_set.add(oh)
            used_set.add(rc_oh)  # block the RC from being used

        if len(rc_free_overhangs) < n_parts + 1:
            # Report the actual maximum supported by the built-in overhang
            # library so the user understands the constraint, not just an opaque failure.
            max_parts = len(rc_free_overhangs) - 1
            return {
                "status": "error",
                "error": (
                    f"Cannot generate enough unique non-RC-paired overhangs for "
                    f"{n_parts} parts. The built-in 4-bp overhang library supports a "
                    f"maximum of {max_parts} parts. For larger assemblies, consider "
                    "hierarchical (two-step) cloning or providing a custom extended "
                    "overhang set."
                ),
            }

        overhangs = rc_free_overhangs[: n_parts + 1]

        if enzyme == "BSAI":
            # BsaI site: GGTCTCN where N is 1 bp spacer before the overhang
            # Forward site: GGTCTCA[overhang]
            # Reverse site (at end of part): rev_comp([overhang]TGAGACC) = GGTCTCA[rev_comp(overhang)]
            fwd_site_prefix = "GGTCTCA"  # BsaI recognition + A spacer
        else:
            # BbsI site: GAAGACNN where NN is 2 bp spacer
            fwd_site_prefix = "GAAGACAA"

        # Compute the recognition sequences and their lengths once.
        rec_seq_len = len(rec_seqs[0][0])  # all rec seqs same length (6 for BsaI/BbsI)
        overlap_len = (
            rec_seq_len - 1
        )  # = 5; a site can span up to 5 chars of part boundary

        # Pre-check all junctions BEFORE building full_sequences, so errors are
        # reported before any partial results are emitted.
        junction_errors = []
        for i, part in enumerate(parts_clean):
            left_oh = overhangs[i]
            right_oh = overhangs[i + 1]
            rev_right_oh = rev_comp(right_oh)

            # Left junction: last overlap_len chars of left_oh + first overlap_len
            # chars of part. The selected overhangs are 4 bp; overlap_len = 5 means
            # we need all 4 chars of left_oh + first 1 char of part.
            left_junction = left_oh[-overlap_len:] + part[:overlap_len]
            # Right junction: last overlap_len chars of part + first overlap_len
            # chars of rev_right_oh (which is rev_comp(right_oh)).
            right_junction = part[-overlap_len:] + rev_right_oh[:overlap_len]

            for rec_seq, direction in rec_seqs:
                if rec_seq in left_junction:
                    pos = left_junction.find(rec_seq)
                    junction_errors.append(
                        f"Part {i + 1}: an unintended {enzyme_display} recognition "
                        f"site ({rec_seq}, {direction}) is created at the left junction "
                        f"between overhang '{left_oh}' and the part sequence "
                        f"(window: '{left_junction}', site at offset {pos}). "
                        "Modify the first few nucleotides of the part sequence to "
                        "eliminate this unintended site."
                    )
                if rec_seq in right_junction:
                    pos = right_junction.find(rec_seq)
                    # Report position relative to the part sequence end
                    part_chars = min(overlap_len, len(part))
                    junction_errors.append(
                        f"Part {i + 1}: an unintended {enzyme_display} recognition "
                        f"site ({rec_seq}, {direction}) is created at the right junction "
                        f"between the part sequence and the reverse complement of overhang "
                        f"'{right_oh}' (rc='{rev_right_oh}', window: '{right_junction}', "
                        f"site at offset {pos}). Modify the last {part_chars} nucleotides "
                        "of the part sequence to eliminate this unintended site."
                    )

        if junction_errors:
            return {
                "status": "error",
                "error": (
                    f"Golden Gate design failed — unintended {enzyme_display} recognition "
                    f"site(s) created at part/overhang junction(s). This would cause the "
                    f"enzyme to cut within the assembled product, destroying the construct. "
                    f"Fix {len(junction_errors)} issue(s): "
                    + " | ".join(junction_errors)
                ),
            }

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
