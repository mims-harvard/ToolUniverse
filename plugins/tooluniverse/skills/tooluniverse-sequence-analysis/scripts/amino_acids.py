#!/usr/bin/env python3
"""Amino acid and codon reference lookup.

Usage:
  python amino_acids.py --type codon_table
  python amino_acids.py --type amino_acid --name "Cysteine"
  python amino_acids.py --type amino_acid --code C
  python amino_acids.py --type count_codons --sequence "ATGCCC..."
  python amino_acids.py --type wobble --anticodon "GAU"
"""
import argparse
import json
import sys

# ---------------------------------------------------------------------------
# Standard genetic code: codon -> 1-letter AA (or '*' for stop)
# ---------------------------------------------------------------------------
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}

# Names for stop codons
STOP_CODON_NAMES = {"TAA": "Ochre", "TAG": "Amber", "TGA": "Opal (Umber)"}

# Human codon usage frequency (% among synonymous codons for that AA, rounded).
# Source: Codon usage table for Homo sapiens (GenBank CDS, approximate values).
# Rare codons (<= 15% usage) are flagged. Values sum to ~100% within each AA group.
CODON_USAGE_FREQ = {
    # Phe
    "TTT": 0.45, "TTC": 0.55,
    # Leu
    "TTA": 0.07, "TTG": 0.13, "CTT": 0.13, "CTC": 0.20, "CTA": 0.07, "CTG": 0.40,
    # Ile
    "ATT": 0.36, "ATC": 0.48, "ATA": 0.16,
    # Met
    "ATG": 1.00,
    # Val
    "GTT": 0.18, "GTC": 0.24, "GTA": 0.11, "GTG": 0.47,
    # Ser
    "TCT": 0.15, "TCC": 0.22, "TCA": 0.15, "TCG": 0.06, "AGT": 0.15, "AGC": 0.24,
    # Pro
    "CCT": 0.28, "CCC": 0.33, "CCA": 0.27, "CCG": 0.11,
    # Thr
    "ACT": 0.25, "ACC": 0.36, "ACA": 0.28, "ACG": 0.12,
    # Ala
    "GCT": 0.26, "GCC": 0.40, "GCA": 0.23, "GCG": 0.11,
    # Tyr
    "TAT": 0.43, "TAC": 0.57,
    # Stop
    "TAA": 0.28, "TAG": 0.20, "TGA": 0.52,
    # His
    "CAT": 0.41, "CAC": 0.59,
    # Gln
    "CAA": 0.25, "CAG": 0.75,
    # Asn
    "AAT": 0.46, "AAC": 0.54,
    # Lys
    "AAA": 0.42, "AAG": 0.58,
    # Asp
    "GAT": 0.46, "GAC": 0.54,
    # Glu
    "GAA": 0.42, "GAG": 0.58,
    # Cys
    "TGT": 0.45, "TGC": 0.55,
    # Trp
    "TGG": 1.00,
    # Arg
    "CGT": 0.08, "CGC": 0.19, "CGA": 0.11, "CGG": 0.20, "AGA": 0.20, "AGG": 0.20,
    # Gly
    "GGT": 0.16, "GGC": 0.34, "GGA": 0.25, "GGG": 0.25,
}

# ---------------------------------------------------------------------------
# Amino acid properties
# Each entry: name, one_letter, three_letter, mw_da, pKa_side_chain,
#   polarity, charge_ph7, hydrophobicity_index, codons
#
# pKa_side_chain: None if no ionisable side chain
# charge_ph7: "positive", "negative", "neutral"
# hydrophobicity_index: Kyte-Doolittle scale (-4.5 to +4.5)
# polarity: "nonpolar", "polar", "charged_positive", "charged_negative", "aromatic"
# ---------------------------------------------------------------------------
AA_DATA = [
    {
        "name": "Alanine",
        "one_letter": "A",
        "three_letter": "Ala",
        "mw_da": 89.09,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 1.8,
        "backbone_pKa": {"alpha_amino": 9.87, "alpha_carboxyl": 2.35},
        "notes": "Smallest chiral amino acid; beta-branched analog is Val",
    },
    {
        "name": "Arginine",
        "one_letter": "R",
        "three_letter": "Arg",
        "mw_da": 174.20,
        "pKa_side_chain": 12.48,
        "polarity": "charged_positive",
        "charge_ph7": "positive",
        "hydrophobicity_index": -4.5,
        "backbone_pKa": {"alpha_amino": 9.04, "alpha_carboxyl": 2.18},
        "notes": "Guanidinium side chain; fully protonated at physiological pH; involved in H-bonds and salt bridges",
    },
    {
        "name": "Asparagine",
        "one_letter": "N",
        "three_letter": "Asn",
        "mw_da": 132.12,
        "pKa_side_chain": None,
        "polarity": "polar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -3.5,
        "backbone_pKa": {"alpha_amino": 8.80, "alpha_carboxyl": 2.02},
        "notes": "Amide of Asp; N-glycosylation site (Asn-X-Ser/Thr motif)",
    },
    {
        "name": "Aspartate",
        "one_letter": "D",
        "three_letter": "Asp",
        "mw_da": 133.10,
        "pKa_side_chain": 3.86,
        "polarity": "charged_negative",
        "charge_ph7": "negative",
        "hydrophobicity_index": -3.5,
        "backbone_pKa": {"alpha_amino": 9.82, "alpha_carboxyl": 1.99},
        "notes": "Carboxylate side chain; deprotonated (negative) at pH 7; catalytic residue in many enzymes",
    },
    {
        "name": "Cysteine",
        "one_letter": "C",
        "three_letter": "Cys",
        "mw_da": 121.16,
        "pKa_side_chain": 8.18,
        "polarity": "polar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 2.5,
        "backbone_pKa": {"alpha_amino": 10.78, "alpha_carboxyl": 1.92},
        "notes": "Thiol side chain; forms disulfide bonds; ~10% deprotonated at pH 7 (near pKa); metal-binding",
    },
    {
        "name": "Glutamate",
        "one_letter": "E",
        "three_letter": "Glu",
        "mw_da": 147.13,
        "pKa_side_chain": 4.07,
        "polarity": "charged_negative",
        "charge_ph7": "negative",
        "hydrophobicity_index": -3.5,
        "backbone_pKa": {"alpha_amino": 9.67, "alpha_carboxyl": 2.10},
        "notes": "Longer carboxylate than Asp; deprotonated (negative) at pH 7; activates serine proteases",
    },
    {
        "name": "Glutamine",
        "one_letter": "Q",
        "three_letter": "Gln",
        "mw_da": 146.15,
        "pKa_side_chain": None,
        "polarity": "polar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -3.5,
        "backbone_pKa": {"alpha_amino": 9.13, "alpha_carboxyl": 2.17},
        "notes": "Amide of Glu; nitrogen donor in biosynthesis; polyglutamine tracts (CAG repeats) linked to neurodegeneration",
    },
    {
        "name": "Glycine",
        "one_letter": "G",
        "three_letter": "Gly",
        "mw_da": 75.03,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -0.4,
        "backbone_pKa": {"alpha_amino": 9.78, "alpha_carboxyl": 2.35},
        "notes": "Smallest amino acid; only achiral (no side chain); allows tight turns in polypeptides",
    },
    {
        "name": "Histidine",
        "one_letter": "H",
        "three_letter": "His",
        "mw_da": 155.16,
        "pKa_side_chain": 6.00,
        "polarity": "charged_positive",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -3.2,
        "backbone_pKa": {"alpha_amino": 9.33, "alpha_carboxyl": 1.80},
        "notes": "Imidazole pKa ~6; ~50% protonated at pH 7; common catalytic/metal-binding residue; heme ligand in hemoglobin",
    },
    {
        "name": "Isoleucine",
        "one_letter": "I",
        "three_letter": "Ile",
        "mw_da": 131.17,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 4.5,
        "backbone_pKa": {"alpha_amino": 9.76, "alpha_carboxyl": 2.32},
        "notes": "Has two chiral centers; beta-branched; disfavored in alpha-helices",
    },
    {
        "name": "Leucine",
        "one_letter": "L",
        "three_letter": "Leu",
        "mw_da": 131.17,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 3.8,
        "backbone_pKa": {"alpha_amino": 9.74, "alpha_carboxyl": 2.33},
        "notes": "6-codon degeneracy (highest); leucine zipper dimerisation motif",
    },
    {
        "name": "Lysine",
        "one_letter": "K",
        "three_letter": "Lys",
        "mw_da": 146.19,
        "pKa_side_chain": 10.53,
        "polarity": "charged_positive",
        "charge_ph7": "positive",
        "hydrophobicity_index": -3.9,
        "backbone_pKa": {"alpha_amino": 9.18, "alpha_carboxyl": 2.16},
        "notes": "Epsilon-amino group protonated at pH 7; site of ubiquitination, acetylation, methylation, SUMOylation",
    },
    {
        "name": "Methionine",
        "one_letter": "M",
        "three_letter": "Met",
        "mw_da": 149.21,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 1.9,
        "backbone_pKa": {"alpha_amino": 9.21, "alpha_carboxyl": 2.13},
        "notes": "Only 1 codon (ATG); universal start codon; N-terminal Met often cleaved post-translationally",
    },
    {
        "name": "Phenylalanine",
        "one_letter": "F",
        "three_letter": "Phe",
        "mw_da": 165.19,
        "pKa_side_chain": None,
        "polarity": "aromatic",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 2.8,
        "backbone_pKa": {"alpha_amino": 9.24, "alpha_carboxyl": 2.58},
        "notes": "Aromatic ring; UV absorbance ~257 nm; pi-stacking interactions",
    },
    {
        "name": "Proline",
        "one_letter": "P",
        "three_letter": "Pro",
        "mw_da": 115.13,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -1.6,
        "backbone_pKa": {"alpha_amino": 10.64, "alpha_carboxyl": 2.00},
        "notes": "Only amino acid with side chain bonded to backbone nitrogen; introduces kinks; disfavors alpha-helices; abundant in collagen (Hyp form after hydroxylation)",
    },
    {
        "name": "Serine",
        "one_letter": "S",
        "three_letter": "Ser",
        "mw_da": 105.09,
        "pKa_side_chain": 13.0,
        "polarity": "polar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -0.8,
        "backbone_pKa": {"alpha_amino": 9.21, "alpha_carboxyl": 2.19},
        "notes": "Hydroxyl side chain; pKa ~13 (essentially uncharged at pH 7); phosphorylation target (Ser/Thr kinases); catalytic triad in serine proteases; O-glycosylation site",
    },
    {
        "name": "Threonine",
        "one_letter": "T",
        "three_letter": "Thr",
        "mw_da": 119.12,
        "pKa_side_chain": 13.0,
        "polarity": "polar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -0.7,
        "backbone_pKa": {"alpha_amino": 9.10, "alpha_carboxyl": 2.09},
        "notes": "Two chiral centers; pKa ~13 (essentially uncharged at pH 7); phosphorylation target; part of Asn-X-Thr N-glycosylation sequon",
    },
    {
        "name": "Tryptophan",
        "one_letter": "W",
        "three_letter": "Trp",
        "mw_da": 204.23,
        "pKa_side_chain": None,
        "polarity": "aromatic",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -0.9,
        "backbone_pKa": {"alpha_amino": 9.44, "alpha_carboxyl": 2.46},
        "notes": "Only 1 codon (TGG); largest amino acid; strong UV absorbance at 280 nm (used for protein quantification); indole side chain",
    },
    {
        "name": "Tyrosine",
        "one_letter": "Y",
        "three_letter": "Tyr",
        "mw_da": 181.19,
        "pKa_side_chain": 10.07,
        "polarity": "aromatic",
        "charge_ph7": "neutral",
        "hydrophobicity_index": -1.3,
        "backbone_pKa": {"alpha_amino": 9.21, "alpha_carboxyl": 2.20},
        "notes": "Phenol hydroxyl; phosphorylation target (receptor tyrosine kinases); UV absorbance ~274 nm; can be sulphated",
    },
    {
        "name": "Valine",
        "one_letter": "V",
        "three_letter": "Val",
        "mw_da": 117.15,
        "pKa_side_chain": None,
        "polarity": "nonpolar",
        "charge_ph7": "neutral",
        "hydrophobicity_index": 4.2,
        "backbone_pKa": {"alpha_amino": 9.74, "alpha_carboxyl": 2.29},
        "notes": "Beta-branched; disfavors alpha-helices; sickle-cell Glu->Val mutation (E6V in HBB)",
    },
]

# Build lookup indices
_BY_ONE_LETTER = {aa["one_letter"]: aa for aa in AA_DATA}
_BY_THREE_LETTER = {aa["three_letter"].upper(): aa for aa in AA_DATA}
_BY_NAME = {aa["name"].upper(): aa for aa in AA_DATA}

# ---------------------------------------------------------------------------
# Wobble base pairing rules (Crick, 1966)
# Anticodon position 34 (wobble position) — what it pairs with in codon pos 3
# I = Inosine (deaminated adenosine; found in many tRNAs after editing)
# ---------------------------------------------------------------------------
WOBBLE_RULES = {
    "I": {
        "pairs_with_codon_bases": ["U", "C", "A"],
        "note": "Inosine (modified adenosine at anticodon wobble position) pairs with U, C, or A in the codon. This is why a single tRNA with I at position 34 can read three codons.",
    },
    "G": {
        "pairs_with_codon_bases": ["U", "C"],
        "note": "G at anticodon wobble position pairs with U or C in the codon (standard Watson-Crick G:C plus G:U wobble).",
    },
    "U": {
        "pairs_with_codon_bases": ["A", "G"],
        "note": "U at anticodon wobble position pairs with A (standard) or G (wobble). Some organisms use modified U (e.g., xm5U) to restrict or expand pairing.",
    },
    "C": {
        "pairs_with_codon_bases": ["G"],
        "note": "C at anticodon wobble position pairs only with G (standard Watson-Crick; no wobble).",
    },
    "A": {
        "pairs_with_codon_bases": ["U"],
        "note": "Unmodified A at anticodon wobble position is rare in eukaryotes; pairs with U. Usually edited to I post-transcriptionally.",
    },
}


def _reverse_complement_rna(seq):
    """Return the reverse complement of an RNA sequence (U, A, G, C)."""
    comp = {"A": "U", "U": "A", "G": "C", "C": "G"}
    return "".join(comp.get(b, "N") for b in reversed(seq.upper()))


def _dna_to_rna(seq):
    return seq.upper().replace("T", "U")


def _build_degeneracy_table():
    """Return {1-letter AA: [codons]} and degeneracy count."""
    table = {}
    for codon, aa in CODON_TABLE.items():
        table.setdefault(aa, []).append(codon)
    return table


DEGENERACY_TABLE = _build_degeneracy_table()


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------

def handle_codon_table():
    """Print the full codon table grouped by amino acid."""
    result = {}
    for aa in AA_DATA:
        code = aa["one_letter"]
        codons = sorted(DEGENERACY_TABLE.get(code, []))
        result[aa["name"]] = {
            "one_letter": code,
            "three_letter": aa["three_letter"],
            "degeneracy": len(codons),
            "codons": codons,
            "codon_usage_freq": {c: CODON_USAGE_FREQ.get(c) for c in codons},
        }

    # Stop codons
    stop_codons = sorted(DEGENERACY_TABLE.get("*", []))
    result["STOP"] = {
        "one_letter": "*",
        "three_letter": "---",
        "degeneracy": len(stop_codons),
        "codons": stop_codons,
        "stop_codon_names": STOP_CODON_NAMES,
        "codon_usage_freq": {c: CODON_USAGE_FREQ.get(c) for c in stop_codons},
    }

    # Summary stats
    summary = {
        "total_codons": 64,
        "coding_codons": 61,
        "stop_codons": 3,
        "standard_amino_acids": 20,
        "degeneracy_distribution": {},
    }
    for aa_name, info in result.items():
        d = info["degeneracy"]
        summary["degeneracy_distribution"].setdefault(d, []).append(aa_name)

    output = {"codon_table": result, "summary": summary}
    print(json.dumps(output, indent=2))


def handle_amino_acid(name=None, code=None):
    """Look up a single amino acid by name or 1-letter code."""
    aa = None
    if code:
        code = code.upper()
        aa = _BY_ONE_LETTER.get(code)
        if aa is None:
            # Try 3-letter
            aa = _BY_THREE_LETTER.get(code)
        if aa is None:
            print(json.dumps({"error": f"No amino acid found for code '{code}'"}))
            sys.exit(1)
    elif name:
        key = name.strip().upper()
        aa = _BY_NAME.get(key)
        if aa is None:
            # Try 3-letter
            aa = _BY_THREE_LETTER.get(key)
        if aa is None:
            # Try 1-letter
            aa = _BY_ONE_LETTER.get(key)
        if aa is None:
            # Partial match fallback
            matches = [v for k, v in _BY_NAME.items() if key in k]
            if len(matches) == 1:
                aa = matches[0]
            elif len(matches) > 1:
                print(json.dumps({
                    "error": f"Ambiguous name '{name}'",
                    "matches": [m["name"] for m in matches],
                }))
                sys.exit(1)
        if aa is None:
            print(json.dumps({"error": f"No amino acid found for name '{name}'"}))
            sys.exit(1)
    else:
        # No filter — print all amino acids (names + codes only)
        all_aa = [
            {"name": a["name"], "one_letter": a["one_letter"], "three_letter": a["three_letter"]}
            for a in AA_DATA
        ]
        print(json.dumps({"amino_acids": all_aa, "count": len(all_aa)}))
        return

    code = aa["one_letter"]
    codons = sorted(DEGENERACY_TABLE.get(code, []))
    result = dict(aa)
    result["codons"] = codons
    result["degeneracy"] = len(codons)
    result["codon_usage_freq"] = {c: CODON_USAGE_FREQ.get(c) for c in codons}
    rare_codons = [c for c in codons if (CODON_USAGE_FREQ.get(c) or 1.0) <= 0.15]
    result["rare_codons_le15pct"] = rare_codons
    print(json.dumps(result, indent=2))


def handle_count_codons(sequence):
    """Count all codons in a DNA sequence and annotate with AA and rarity."""
    dna = "".join(c for c in sequence.upper() if c in "ATCG")
    if len(dna) < 3:
        print(json.dumps({"error": "Sequence too short (need >= 3 bases)"}))
        sys.exit(1)

    # Trim to multiple of 3 and warn
    remainder = len(dna) % 3
    used_len = len(dna) - remainder
    trimmed = dna[:used_len]

    codon_counts = {}
    for i in range(0, len(trimmed), 3):
        codon = trimmed[i:i + 3]
        codon_counts[codon] = codon_counts.get(codon, 0) + 1

    total_codons = sum(codon_counts.values())
    annotated = {}
    for codon, count in sorted(codon_counts.items(), key=lambda x: -x[1]):
        aa_code = CODON_TABLE.get(codon, "?")
        aa_name = _BY_ONE_LETTER[aa_code]["name"] if aa_code in _BY_ONE_LETTER else (
            "Stop" if aa_code == "*" else "Unknown"
        )
        freq = CODON_USAGE_FREQ.get(codon)
        annotated[codon] = {
            "count": count,
            "fraction_of_sequence": round(count / total_codons, 4),
            "amino_acid_code": aa_code,
            "amino_acid_name": aa_name,
            "human_usage_freq": freq,
            "is_rare_codon": freq is not None and freq <= 0.15,
        }

    # AA composition summary
    aa_composition = {}
    for codon, info in annotated.items():
        aa_code = info["amino_acid_code"]
        aa_composition[aa_code] = aa_composition.get(aa_code, 0) + info["count"]

    output = {
        "input_length_nt": len(dna),
        "used_length_nt": used_len,
        "trimmed_bases": remainder,
        "total_codons": total_codons,
        "codon_counts": annotated,
        "amino_acid_composition": {
            k: {"count": v, "fraction": round(v / total_codons, 4)}
            for k, v in sorted(aa_composition.items(), key=lambda x: -x[1])
        },
        "rare_codons_present": [c for c, d in annotated.items() if d["is_rare_codon"]],
    }
    print(json.dumps(output, indent=2))


def handle_wobble(anticodon):
    """Given an anticodon (5'->3'), determine which codons it recognises."""
    anticodon = anticodon.upper().replace("T", "U")
    if len(anticodon) != 3:
        print(json.dumps({"error": "Anticodon must be exactly 3 bases"}))
        sys.exit(1)

    # tRNA anticodon is read 3'->5', codon is read 5'->3'
    # Anticodon written 5'->3': pos34(wobble), pos35, pos36
    # Codon pos 1,2,3 pair with anticodon pos 36, 35, 34 respectively
    wobble_base = anticodon[0]   # position 34 (wobble position, 5' end of anticodon)
    ac_pos35 = anticodon[1]      # position 35
    ac_pos36 = anticodon[2]      # position 36

    # Standard Watson-Crick for positions 35 and 36 (strict)
    wc_complement = {"A": "U", "U": "A", "G": "C", "C": "G"}
    codon_pos1 = wc_complement.get(ac_pos36, "?")
    codon_pos2 = wc_complement.get(ac_pos35, "?")

    # Wobble pairing for codon position 3 (anticodon position 34)
    wobble_info = WOBBLE_RULES.get(wobble_base)
    if wobble_info is None:
        print(json.dumps({"error": f"Unknown wobble base: {wobble_base}"}))
        sys.exit(1)

    codon_pos3_options = wobble_info["pairs_with_codon_bases"]

    recognised_codons = []
    for cp3 in codon_pos3_options:
        codon_rna = codon_pos1 + codon_pos2 + cp3
        codon_dna = codon_rna.replace("U", "T")
        aa_code = CODON_TABLE.get(codon_dna, "?")
        aa_name = _BY_ONE_LETTER.get(aa_code, {}).get("name", "Stop" if aa_code == "*" else "Unknown")
        recognised_codons.append({
            "codon_rna": codon_rna,
            "codon_dna": codon_dna,
            "codon_position_3": cp3,
            "amino_acid_code": aa_code,
            "amino_acid_name": aa_name,
        })

    # Check if all recognised codons encode the same AA
    aa_set = {c["amino_acid_code"] for c in recognised_codons}
    synonymous = len(aa_set) == 1

    output = {
        "anticodon_5to3": anticodon,
        "anticodon_positions": {
            "pos34_wobble": wobble_base,
            "pos35": ac_pos35,
            "pos36": ac_pos36,
        },
        "codon_positions_decoded": {
            "codon_pos1": codon_pos1,
            "codon_pos2": codon_pos2,
            "codon_pos3_options": codon_pos3_options,
        },
        "wobble_rule": wobble_info,
        "recognised_codons": recognised_codons,
        "synonymous_only": synonymous,
        "amino_acids_encoded": sorted(aa_set),
        "note": (
            "Anticodon is given 5'->3'. Position 34 is the wobble base (5' end of anticodon). "
            "Positions 35 and 36 form strict Watson-Crick pairs. "
            "Codon positions 1,2,3 pair anticodon positions 36,35,34 respectively (antiparallel)."
        ),
    }
    print(json.dumps(output, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Amino acid and codon reference lookup.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python amino_acids.py --type codon_table
  python amino_acids.py --type amino_acid --name "Cysteine"
  python amino_acids.py --type amino_acid --code C
  python amino_acids.py --type amino_acid --code TRP
  python amino_acids.py --type amino_acid             # list all 20
  python amino_acids.py --type count_codons --sequence "ATGCCCAAATTT"
  python amino_acids.py --type wobble --anticodon "GAU"
  python amino_acids.py --type wobble --anticodon "IAU"
        """,
    )
    parser.add_argument("--type", required=True,
                        choices=["codon_table", "amino_acid", "count_codons", "wobble"],
                        help="Query type")
    parser.add_argument("--name", help="Amino acid full name (for --type amino_acid)")
    parser.add_argument("--code", help="1-letter or 3-letter amino acid code (for --type amino_acid)")
    parser.add_argument("--sequence", help="DNA sequence (for --type count_codons)")
    parser.add_argument("--anticodon", help="tRNA anticodon 5'->3' e.g. GAU (for --type wobble)")

    args = parser.parse_args()

    if args.type == "codon_table":
        handle_codon_table()
    elif args.type == "amino_acid":
        handle_amino_acid(name=args.name, code=args.code)
    elif args.type == "count_codons":
        if not args.sequence:
            parser.error("--type count_codons requires --sequence")
        handle_count_codons(args.sequence)
    elif args.type == "wobble":
        if not args.anticodon:
            parser.error("--type wobble requires --anticodon")
        handle_wobble(args.anticodon)


if __name__ == "__main__":
    main()
