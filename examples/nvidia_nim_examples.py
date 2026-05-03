#!/usr/bin/env python3
"""
NVIDIA NIM Healthcare APIs Examples for ToolUniverse

This file demonstrates how to use NVIDIA NIM Healthcare APIs through ToolUniverse
for protein structure prediction, molecular docking, protein design, genomics,
and medical imaging tasks.

Prerequisites:
    1. Set NVIDIA_API_KEY environment variable:
       export NVIDIA_API_KEY="nvapi-your-key-here"
       
    2. Get your API key from: https://build.nvidia.com
    
    3. Note: Rate limit is 40 requests per minute (RPM)

Usage:
    python examples/nvidia_nim_examples.py

Available Tools (16 total):
    Structure Prediction:
        - NvidiaNIM_alphafold2        - DeepMind AlphaFold2 (async, ~5-15min)
        - NvidiaNIM_alphafold2_multimer - Multi-chain complexes (async)
        - NvidiaNIM_esmfold           - Fast single-seq prediction (sync)
        - NvidiaNIM_openfold2         - OpenFold2 (async)
        - NvidiaNIM_openfold3         - OpenFold3 for molecules (async)
        - NvidiaNIM_boltz2            - Boltz2 prediction (async)
    
    Protein Design:
        - NvidiaNIM_proteinmpnn       - Inverse folding (sync)
        - NvidiaNIM_rfdiffusion       - De novo backbone design (async)
    
    Molecular Tools:
        - NvidiaNIM_diffdock          - Molecular docking (async)
        - NvidiaNIM_genmol            - Molecule generation (sync)
        - NvidiaNIM_molmim            - Molecular optimization (sync)
    
    Genomics:
        - NvidiaNIM_evo2              - DNA sequence generation (sync)
        - NvidiaNIM_msa_search        - MSA with mmseqs2 (async)
        - NvidiaNIM_esm2_650m         - Protein embeddings (sync)
    
    Medical Imaging:
        - NvidiaNIM_maisi             - Medical image generation (async)
        - NvidiaNIM_vista3d           - 3D image segmentation (async)
"""

import os
import sys
import time


def check_api_key():
    """Check if NVIDIA API key is set."""
    key = os.environ.get("NVIDIA_API_KEY")
    if not key:
        print("ERROR: NVIDIA_API_KEY environment variable not set.")
        print("Get your key from: https://build.nvidia.com")
        print("Set it with: export NVIDIA_API_KEY='nvapi-your-key-here'")
        return False
    return True


def example_esmfold_structure_prediction():
    """
    Example 1: ESMFold - Fast Protein Structure Prediction
    
    ESMFold predicts protein structure from sequence alone (no MSA required).
    This is the fastest option, completing in seconds.
    """
    print("\n" + "=" * 60)
    print("Example 1: ESMFold Structure Prediction")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    # Short test sequence (human hemoglobin alpha chain, truncated)
    sequence = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH"
    
    print(f"Input sequence ({len(sequence)} residues):")
    print(f"  {sequence[:40]}...")
    print("\nCalling NvidiaNIM_esmfold...")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_esmfold",
        "arguments": {"sequence": sequence}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        print(f"Format: {result.get('format', 'unknown')}")
        if "structure" in result:
            pdb_lines = result["structure"].split("\n")
            print(f"PDB output: {len(pdb_lines)} lines")
            # Show first few ATOM lines
            atom_lines = [l for l in pdb_lines if l.startswith("ATOM")][:3]
            for line in atom_lines:
                print(f"  {line}")
            print("  ...")
    
    return result


def example_alphafold2_structure_prediction():
    """
    Example 2: AlphaFold2 - High-Accuracy Structure Prediction
    
    AlphaFold2 uses MSA (multiple sequence alignment) for higher accuracy.
    This is an async operation that can take 5-15 minutes.
    """
    print("\n" + "=" * 60)
    print("Example 2: AlphaFold2 Structure Prediction (Async)")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    # Short sequence for faster processing
    sequence = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH"
    
    print(f"Input sequence ({len(sequence)} residues):")
    print(f"  {sequence[:40]}...")
    print("\nCalling NvidiaNIM_alphafold2 (this may take several minutes)...")
    print("Parameters: algorithm=mmseqs2, databases=[small_bfd]")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_alphafold2",
        "arguments": {
            "sequence": sequence,
            "algorithm": "mmseqs2",
            "databases": ["small_bfd"],
            "e_value": 0.0001,
            "iterations": 1,
            "relax_prediction": False,
            "skip_template_search": True
        }
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result:
            print(f"Response data type: {type(result['data'])}")
    
    return result


def example_esm2_embedding():
    """
    Example 3: ESM2-650M - Protein Sequence Embedding
    
    ESM2 generates vector embeddings that capture protein properties.
    Useful for similarity search, clustering, and ML applications.
    """
    print("\n" + "=" * 60)
    print("Example 3: ESM2-650M Protein Embedding")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    sequence = "MVLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTKTYFPHFDLSH"
    
    print(f"Input sequence ({len(sequence)} residues):")
    print(f"  {sequence[:40]}...")
    print("\nCalling NvidiaNIM_esm2_650m...")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_esm2_650m",
        "arguments": {"sequence": sequence}
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result and "embeddings" in result["data"]:
            embeddings = result["data"]["embeddings"]
            print(f"Embedding dimensions: {len(embeddings[0]) if embeddings else 'N/A'}")
    
    return result


def example_evo2_dna_generation():
    """
    Example 4: Evo2-40B - DNA Sequence Generation
    
    Evo2 generates DNA sequences using a large language model.
    Can be used for sequence completion, design, etc.
    """
    print("\n" + "=" * 60)
    print("Example 4: Evo2-40B DNA Generation")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    # Input DNA prompt
    prompt_sequence = "ACTGACTGACTGACTG"
    
    print(f"Input DNA prompt: {prompt_sequence}")
    print("\nCalling NvidiaNIM_evo2...")
    print("Parameters: num_tokens=16, top_k=1, temperature=1.0")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_evo2",
        "arguments": {
            "sequence": prompt_sequence,
            "num_tokens": 16,
            "top_k": 1,
            "temperature": 1.0
        }
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result:
            print(f"Generated sequence: {result['data'].get('text', 'N/A')}")
    
    return result


def example_proteinmpnn_design():
    """
    Example 5: ProteinMPNN - Inverse Folding
    
    ProteinMPNN designs amino acid sequences that fold into a given 3D structure.
    Input is a PDB structure, output is optimized sequences.
    """
    print("\n" + "=" * 60)
    print("Example 5: ProteinMPNN Inverse Folding")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    # Minimal PDB structure for demonstration
    # In practice, use a real PDB file
    pdb_structure = """HEADER    TEST STRUCTURE
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00 20.00           C
ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00 20.00           O
ATOM      5  N   GLY A   2       3.326   1.547   0.000  1.00 20.00           N
ATOM      6  CA  GLY A   2       3.950   2.861   0.000  1.00 20.00           C
ATOM      7  C   GLY A   2       5.467   2.768   0.000  1.00 20.00           C
ATOM      8  O   GLY A   2       6.050   1.680   0.000  1.00 20.00           O
END"""
    
    print("Input: PDB structure (minimal test structure)")
    print("\nCalling NvidiaNIM_proteinmpnn...")
    print("Parameters: num_seq_per_target=3, sampling_temp=0.1")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_proteinmpnn",
        "arguments": {
            "structure": pdb_structure,
            "num_seq_per_target": 3,
            "sampling_temp": 0.1,
            "seed": 42
        }
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result or "sequences" in result:
            print("Designed sequences generated successfully")
    
    return result


def example_genmol_molecule_generation():
    """
    Example 6: GenMol - Generate Novel Molecules
    
    GenMol generates novel drug-like molecules with specified properties.
    Can optimize for desired characteristics like QED, logP, etc.
    """
    print("\n" + "=" * 60)
    print("Example 6: GenMol Molecule Generation")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    print("Generating molecules optimized for drug-likeness (QED)...")
    print("\nCalling NvidiaNIM_genmol...")
    print("Parameters: algorithm=CMA-ES, num_molecules=5, scoring=QED")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_genmol",
        "arguments": {
            "algorithm": "CMA-ES",
            "num_molecules": 5,
            "scoring_function": "QED",
            "iterations": 100,
            "seed": 42
        }
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result and "molecules" in result["data"]:
            molecules = result["data"]["molecules"]
            print(f"Generated {len(molecules)} molecules:")
            for i, mol in enumerate(molecules[:3]):
                print(f"  {i+1}. {mol.get('smiles', 'N/A')[:50]}...")
    
    return result


def example_diffdock_docking():
    """
    Example 7: DiffDock - Molecular Docking
    
    DiffDock predicts how small molecules bind to protein targets.
    Useful for drug discovery and lead optimization.
    """
    print("\n" + "=" * 60)
    print("Example 7: DiffDock Molecular Docking (Async)")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    # Example: Aspirin SMILES
    ligand_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    
    # Minimal protein structure
    protein_pdb = """HEADER    TEST PROTEIN FOR DOCKING
ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00 20.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00 20.00           C
END"""
    
    print(f"Ligand SMILES: {ligand_smiles}")
    print("Protein: Minimal test structure")
    print("\nCalling NvidiaNIM_diffdock (this may take a few minutes)...")
    
    result = tu.run_one_function({
        "name": "NvidiaNIM_diffdock",
        "arguments": {
            "ligand": ligand_smiles,
            "ligand_file_type": "smi",
            "protein": protein_pdb,
            "num_poses": 5,
            "time_divisions": 20,
            "steps": 18
        }
    })
    
    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'No details')}")
    else:
        print(f"Status: {result.get('status')}")
        if "data" in result:
            print("Docking poses generated successfully")
    
    return result


def example_list_all_tools():
    """List all available NVIDIA NIM tools."""
    print("\n" + "=" * 60)
    print("Available NVIDIA NIM Healthcare Tools")
    print("=" * 60)
    
    from tooluniverse import ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()
    
    nvidia_tools = [
        tool for tool in tu.all_tools 
        if isinstance(tool, dict) and tool.get("name", "").startswith("NvidiaNIM_")
    ]
    
    print(f"\nFound {len(nvidia_tools)} NVIDIA NIM tools:\n")
    
    for tool in sorted(nvidia_tools, key=lambda x: x.get("name", "")):
        name = tool.get("name", "Unknown")
        desc = tool.get("description", "No description")[:80]
        fields = tool.get("fields", {})
        async_marker = " [ASYNC]" if fields.get("async_expected") else ""
        print(f"  {name}{async_marker}")
        print(f"    {desc}...")
        print()


def main():
    """Run selected examples."""
    print("=" * 60)
    print("NVIDIA NIM Healthcare APIs - ToolUniverse Examples")
    print("=" * 60)
    
    if not check_api_key():
        sys.exit(1)
    
    # List all available tools
    example_list_all_tools()
    
    # Run quick examples (synchronous, fast)
    print("\n" + "#" * 60)
    print("Running Quick Examples (Synchronous Operations)")
    print("#" * 60)
    
    try:
        # These are synchronous and should complete quickly
        example_esmfold_structure_prediction()
        time.sleep(1.5)  # Rate limit: 40 RPM = 1.5s minimum between requests
        
        example_esm2_embedding()
        time.sleep(1.5)
        
        example_evo2_dna_generation()
        
    except Exception as e:
        print(f"\nError during examples: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Examples Complete!")
    print("=" * 60)
    print("\nNote: Async operations (AlphaFold2, DiffDock, etc.) are available")
    print("but not run by default as they can take 5-30+ minutes.")
    print("\nTo run async examples, uncomment the corresponding function calls.")


if __name__ == "__main__":
    main()
