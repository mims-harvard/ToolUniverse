#!/usr/bin/env python3
"""
Example: Proper ID conversion and usage for ToolUniverse tools

This demonstrates how to:
1. Convert Ensembl protein IDs to UniProt accessions
2. Use the correct ID types with different APIs
3. Handle ID mapping properly
"""
from tooluniverse import ToolUniverse

def demonstrate_id_conversion():
    """Show how to properly convert between ID types"""
    
    print("="*80)
    print("Proper ID Conversion and Usage Examples")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Example 1: Convert Ensembl protein ID to UniProt accession for AlphaFold
    print("\n1. Converting Ensembl protein ID to UniProt for AlphaFold")
    print("-"*80)
    
    ensembl_protein_id = "ENSP00000314484"
    gene_name = "MEIOB"
    
    print(f"Given: Ensembl Protein ID = {ensembl_protein_id}")
    print(f"Goal: Get AlphaFold structure for {gene_name}")
    
    # Method 1: Direct UniProt search by gene name
    print("\nMethod 1: Search UniProt by gene name")
    result = tu.run({
        "name": "UniProt_search",
        "arguments": {
            "query": f"gene:{gene_name} AND organism_id:9606",  # Human
            "limit": 1
        }
    })
    
    if isinstance(result, dict):
        # Check different possible result formats
        entries = result.get('data', {}).get('results', []) if result.get('data') else result.get('results', [])
        if entries:
            uniprot_id = entries[0].get('primaryAccession') or entries[0].get('accession')
            print(f"✓ Found UniProt accession: {uniprot_id}")
            
            # Now use with AlphaFold
            print(f"\nQuerying AlphaFold with UniProt accession: {uniprot_id}")
            result = tu.run({
                "name": "alphafold_get_summary",
                "arguments": {
                    "qualifier": uniprot_id
                }
            })
            
            if isinstance(result, dict) and result.get('data'):
                print("✓ Success! AlphaFold returned data:")
                data = result.get('data', {})
                print(f"  - Model Count: {data.get('modelCount', 'N/A')}")
                print(f"  - Structure URL: {data.get('modelUrl', 'N/A')[:60]}...")
            else:
                print(f"✗ Error: {result.get('error') if isinstance(result, dict) else result}")
        else:
            print("✗ No entries found")
    else:
        print(f"✗ Search failed: {result}")
    
    # Example 2: Get protein sequence from Ensembl using correct ID type
    print("\n2. Getting Ensembl sequence with correct ID type")
    print("-"*80)
    
    # Use gene ID (not protein ID) for sequence retrieval
    gene_id = "ENSG00000162039"
    print(f"Using Gene ID: {gene_id}")
    
    result = tu.run({
        "name": "ensembl_get_sequence",
        "arguments": {
            "sequence_id": gene_id,
            "type": "genomic"
        }
    })
    
    if isinstance(result, dict) and result.get('status') == 'success':
        data = result.get('data', [])
        if isinstance(data, list) and data:
            print(f"✓ Success! Got sequence data:")
            print(f"  - Sequence ID: {data[0].get('id')}")
            print(f"  - Length: {data[0].get('length')} bp")
            print(f"  - Description: {data[0].get('desc', '')[:60]}...")
        else:
            print(f"  No sequence data")
    else:
        print(f"✗ Error: {result.get('error') if isinstance(result, dict) else result}")
    
    # Example 3: ID mapping from Ensembl to UniProt
    print("\n3. Using ID mapping tool")
    print("-"*80)
    
    print(f"Converting Ensembl Gene ID to UniProt: {gene_id}")
    result = tu.run({
        "name": "UniProt_id_mapping",
        "arguments": {
            "from_db": "Ensembl",
            "to_db": "UniProtKB",
            "ids": gene_id
        }
    })
    
    if isinstance(result, dict) and result.get('status') == 'success':
        data = result.get('data', {}).get('results', [])
        if data:
            print("✓ Mapping results:")
            for mapping in data:
                print(f"  {mapping.get('from')} -> {mapping.get('to')}")
        else:
            print("  No mappings found")
    else:
        print(f"✗ Error: {result.get('error') if isinstance(result, dict) else result}")
    
    print("\n" + "="*80)
    print("Examples complete!")
    print("="*80)

if __name__ == "__main__":
    demonstrate_id_conversion()

