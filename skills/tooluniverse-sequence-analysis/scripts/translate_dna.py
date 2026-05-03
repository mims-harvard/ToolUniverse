#!/usr/bin/env python3
"""Translate a DNA sequence to protein in all 3 reading frames.
Usage: python translate_dna.py <DNA_SEQUENCE>
Picks the frame with the longest ORF (no internal stop codons).
"""
import sys

CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}

def translate(dna, frame=0):
    """Translate DNA from given frame (0, 1, or 2)."""
    protein = []
    for i in range(frame, len(dna) - 2, 3):
        codon = dna[i:i+3].upper()
        aa = CODON_TABLE.get(codon, '?')
        protein.append(aa)
    return ''.join(protein)

def longest_orf(protein):
    """Find longest stretch without a stop codon."""
    segments = protein.split('*')
    return max(segments, key=len) if segments else protein

def main():
    if len(sys.argv) < 2:
        print("Usage: python translate_dna.py <DNA_SEQUENCE>")
        sys.exit(1)

    dna = ''.join(c for c in sys.argv[1].upper() if c in 'ATCG')
    print(f"Input: {len(dna)} bases")

    best_frame = 0
    best_protein = ""
    best_orf_len = 0

    for frame in range(3):
        protein = translate(dna, frame)
        orf = longest_orf(protein)
        print(f"\nFrame +{frame+1}: {protein}")
        print(f"  Longest ORF: {orf} ({len(orf)} aa)")
        if len(orf) > best_orf_len:
            best_orf_len = len(orf)
            best_protein = orf
            best_frame = frame

    print(f"\n=== BEST: Frame +{best_frame+1}, {best_orf_len} aa ===")
    print(f"Protein: {best_protein}")

if __name__ == '__main__':
    main()
