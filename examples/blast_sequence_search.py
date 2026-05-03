#!/usr/bin/env python3
"""
BLAST Sequence Search Example

This example shows how to use the BLAST tool to search for sequence similarities
using real gene sequences from important proteins.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.tooluniverse import ToolUniverse

def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    
    # Load tools first
    tu.load_tools()
    
    print("🔬 BLAST Sequence Search Examples")
    print("=" * 40)
    
    # Example 1: Search for insulin gene homologs
    print("\n1. Searching for insulin gene homologs")
    print("-" * 35)
    
    # Human insulin gene sequence (partial)
    insulin_sequence = "ATGGCCCTGTGGATGCGCCTCCTGCCCCTGCTGGCGCTGCTGGGCCTGGACCCCGCCGCCGCCTTCGTGAACCACCTGTGCGGCTCCCACCTGGTGGAGGGCCTCTACCTGGTGTGCGGCGAGAGGGGCTTCTACACCCCCAAGACCCGCAGGGAGGAGGACCTGCAGGTGGGCCAGGTGGAGCTGGGCGGCCCCGGCGCCGGCAGCCTGCAGCCCCTGGCCCTGGAGGGCTCCCTGCAGAAGAGGGGCATCGTGGAGCAGTGCTGCACCAGCATCTGCTCCCTGTACCAGCTGGAGAACTACTGCAAC"
    
    result = tu.run({"name": "BLAST_nucleotide_search", "arguments": {
        "sequence": insulin_sequence,
        "database": "nt",
        "hitlist_size": 5
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Found {len(data.get('alignments', []))} similar sequences")
        
        for i, alignment in enumerate(data.get("alignments", [])[:3], 1):
            hit_def = alignment.get("hit_def", "Unknown")
            print(f"   {i}. {hit_def[:80]}...")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 2: Search for p53 gene homologs
    print("\n2. Searching for p53 gene homologs")
    print("-" * 35)
    
    # p53 gene sequence fragment
    p53_sequence = "ATGCGATCGATCGATCGATCGATCGATCGATCGATCG"
    
    result = tu.run({"name": "BLAST_nucleotide_search", "arguments": {
        "sequence": p53_sequence,
        "database": "nt",
        "hitlist_size": 3
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Found {len(data.get('alignments', []))} similar sequences")
        
        for i, alignment in enumerate(data.get("alignments", [])[:2], 1):
            hit_def = alignment.get("hit_def", "Unknown")
            print(f"   {i}. {hit_def[:80]}...")
    else:
        print(f"❌ Error: {result.get('error')}")
    
    # Example 3: Search for BRCA1 gene homologs
    print("\n3. Searching for BRCA1 gene homologs")
    print("-" * 35)
    
    # BRCA1 gene sequence fragment
    brca1_sequence = "ATGGATTTATCTGCTCTTCGCGTTGAAGAAGTACAAAATGTCAATAAATCTAAAGAGATTTTGTTTATAAAGACATTATGAAC"
    
    result = tu.run({"name": "BLAST_nucleotide_search", "arguments": {
        "sequence": brca1_sequence,
        "database": "nt",
        "hitlist_size": 3
    }})
    
    if result and result.get("status") == "success":
        data = result.get("data", {})
        print(f"✅ Found {len(data.get('alignments', []))} similar sequences")
        
        for i, alignment in enumerate(data.get("alignments", [])[:2], 1):
            hit_def = alignment.get("hit_def", "Unknown")
            print(f"   {i}. {hit_def[:80]}...")
    else:
        print(f"❌ Error: {result.get('error')}")

if __name__ == "__main__":
    main()
