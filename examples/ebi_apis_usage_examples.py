"""
EBI APIs Usage Examples

This file provides clear, practical examples for using the newly implemented
EBI API tools in ToolUniverse. Each example demonstrates a common use case
with explanations.
"""

from tooluniverse import ToolUniverse


def example_ebi_search():
    """Example: Using EBI Search API for cross-domain searches"""
    print("\n" + "="*80)
    print("EXAMPLE: EBI Search API - Unified Search Across EBI Resources")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Search for a gene across Ensembl
    print("\n1. Search for BRCA1 gene in Ensembl:")
    result = tu.run_one_function({
        "name": "ebi_search_domain",
        "arguments": {
            "domain": "ensembl",
            "query": "BRCA1",
            "size": 5
        }
    })
    if result.get("status") == "success":
        entries = result.get("data", [])
        print(f"   Found {len(entries)} results")
        if entries:
            print(f"   First result ID: {entries[0].get('id', 'N/A')}")
    
    # Example 2: List available domains
    print("\n2. List available EBI Search domains:")
    result = tu.run_one_function({
        "name": "ebi_list_domains",
        "arguments": {}
    })
    if result.get("status") == "success":
        domains = result.get("data", {}).get("domains", [])
        print(f"   Available domains: {len(domains)}")
        print(f"   Sample domains: {[d.get('id') for d in domains[:5]]}")
    
    # Example 3: Get domain information
    print("\n3. Get information about UniProt domain:")
    result = tu.run_one_function({
        "name": "ebi_get_domain_info",
        "arguments": {
            "domain": "uniprot"
        }
    })
    if result.get("status") == "success":
        print("   Domain info retrieved successfully")


def example_metabolights():
    """Example: Using MetaboLights for metabolomics data"""
    print("\n" + "="*80)
    print("EXAMPLE: MetaboLights - Metabolomics Experiments")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Search for cancer-related studies
    print("\n1. Search for cancer metabolomics studies:")
    result = tu.run_one_function({
        "name": "metabolights_search_studies",
        "arguments": {
            "query": "cancer",
            "size": 10
        }
    })
    if result.get("status") == "success":
        study_ids = result.get("data", {}).get("content", [])
        print(f"   Found {len(study_ids)} studies")
        if study_ids:
            print(f"   Sample study IDs: {study_ids[:5]}")
    
    # Example 2: Get detailed study information
    print("\n2. Get detailed information for a study:")
    result = tu.run_one_function({
        "name": "metabolights_get_study",
        "arguments": {
            "study_id": "MTBLS1"
        }
    })
    if result.get("status") == "success":
        print("   Study details retrieved successfully")
    
    # Example 3: Get study files
    print("\n3. Get files associated with a study:")
    result = tu.run_one_function({
        "name": "metabolights_get_study_files",
        "arguments": {
            "study_id": "MTBLS1"
        }
    })
    if result.get("status") == "success":
        files = result.get("data", [])
        print(f"   Found {len(files)} files")


def example_proteins_api():
    """Example: Using Proteins API for protein annotations"""
    print("\n" + "="*80)
    print("EXAMPLE: Proteins API - Comprehensive Protein Data")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Get protein information
    print("\n1. Get comprehensive protein information:")
    result = tu.run_one_function({
        "name": "proteins_api_get_protein",
        "arguments": {
            "accession": "P05067"  # APP protein
        }
    })
    if result.get("status") == "success":
        print("   Protein data retrieved successfully")
    
    # Example 2: Get variant information
    print("\n2. Get variant data for a protein:")
    result = tu.run_one_function({
        "name": "proteins_api_get_variants",
        "arguments": {
            "accession": "P04637"  # p53
        }
    })
    if result.get("status") == "success":
        variants = result.get("data", [])
        print(f"   Found {len(variants)} variants")
    
    # Example 3: Search proteins
    print("\n3. Search for proteins by name:")
    result = tu.run_one_function({
        "name": "proteins_api_search",
        "arguments": {
            "query": "BRCA1",
            "size": 5
        }
    })
    if result.get("status") == "success":
        print("   Search completed successfully")


def example_dbfetch():
    """Example: Using Dbfetch for database entry retrieval"""
    print("\n" + "="*80)
    print("EXAMPLE: Dbfetch - Multi-Database Entry Retrieval")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Fetch UniProt entry in FASTA format
    print("\n1. Fetch UniProt entry in FASTA format:")
    result = tu.run_one_function({
        "name": "dbfetch_fetch_entry",
        "arguments": {
            "db": "uniprotkb",
            "id": "P05067",
            "format": "fasta"
        }
    })
    if result.get("status") == "success":
        sequence = result.get("data", "")
        if sequence:
            lines = sequence.split("\n")[:3]
            print(f"   Sequence preview: {lines[0]}")
            print(f"   Sequence length: {len(sequence)} characters")
    
    # Example 2: List available databases
    print("\n2. List available databases:")
    result = tu.run_one_function({
        "name": "dbfetch_list_databases",
        "arguments": {}
    })
    if result.get("status") == "success":
        print("   Database list retrieved")
    
    # Example 3: Fetch PDB entry
    print("\n3. Fetch PDB entry in XML format:")
    result = tu.run_one_function({
        "name": "dbfetch_fetch_entry",
        "arguments": {
            "db": "pdb",
            "id": "1A2B",
            "format": "xml"
        }
    })
    if result.get("status") == "success":
        print("   PDB entry retrieved successfully")


def example_pdbe_api():
    """Example: Using PDBe API for structure information"""
    print("\n" + "="*80)
    print("EXAMPLE: PDBe API - Protein Structure Metadata")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Get structure summary
    print("\n1. Get PDB entry summary:")
    result = tu.run_one_function({
        "name": "pdbe_get_entry_summary",
        "arguments": {
            "pdb_id": "1CRN"
        }
    })
    if result.get("status") == "success":
        print("   Structure summary retrieved")
    
    # Example 2: Get quality metrics
    print("\n2. Get structure quality metrics:")
    result = tu.run_one_function({
        "name": "pdbe_get_entry_quality",
        "arguments": {
            "pdb_id": "1CRN"
        }
    })
    if result.get("status") == "success":
        print("   Quality metrics retrieved")
    
    # Example 3: Get publications
    print("\n3. Get associated publications:")
    result = tu.run_one_function({
        "name": "pdbe_get_entry_publications",
        "arguments": {
            "pdb_id": "1CRN"
        }
    })
    if result.get("status") == "success":
        print("   Publications retrieved")


def example_ena_browser():
    """Example: Using ENA Browser for sequence retrieval"""
    print("\n" + "="*80)
    print("EXAMPLE: ENA Browser - Nucleotide Sequence Retrieval")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Get FASTA sequence
    print("\n1. Get nucleotide sequence in FASTA format:")
    result = tu.run_one_function({
        "name": "ena_get_sequence_fasta",
        "arguments": {
            "accession": "U00096"  # E. coli genome
        }
    })
    if result.get("status") == "success":
        sequence = result.get("data", "")
        if sequence:
            lines = sequence.split("\n")[:2]
            print(f"   Header: {lines[0]}")
            print(f"   Sequence length: {len(sequence)} characters")
    
    # Example 2: Get entry metadata
    print("\n2. Get entry metadata:")
    result = tu.run_one_function({
        "name": "ena_get_entry",
        "arguments": {
            "accession": "U00096"
        }
    })
    if result.get("status") == "success":
        print("   Entry metadata retrieved")
    
    # Example 3: Get version history
    print("\n3. Get version history:")
    result = tu.run_one_function({
        "name": "ena_get_entry_history",
        "arguments": {
            "accession": "U00096"
        }
    })
    if result.get("status") == "success":
        history = result.get("data", [])
        print(f"   Found {len(history)} versions")


def example_arrayexpress():
    """Example: Using ArrayExpress for gene expression data"""
    print("\n" + "="*80)
    print("EXAMPLE: ArrayExpress - Functional Genomics Data")
    print("="*80)
    
    tu = ToolUniverse()
    
    # Example 1: Search experiments
    print("\n1. Search for cancer-related experiments:")
    result = tu.run_one_function({
        "name": "arrayexpress_search_experiments",
        "arguments": {
            "keywords": "cancer",
            "species": "Homo sapiens",
            "limit": 5
        }
    })
    if result.get("status") == "success":
        print("   Search completed successfully")
    
    # Example 2: Get experiment details
    print("\n2. Get experiment details:")
    print("   (Note: Use an experiment ID from search results)")
    result = tu.run_one_function({
        "name": "arrayexpress_get_experiment",
        "arguments": {
            "experiment_id": "E-MTAB-1234"
        }
    })
    if result.get("status") == "success":
        print("   Experiment details retrieved")


def main():
    """Run all examples"""
    print("="*80)
    print("EBI API TOOLS - USAGE EXAMPLES")
    print("="*80)
    print("\nThis file demonstrates practical usage of EBI API tools.")
    print("Each example shows a common use case with clear explanations.\n")
    
    try:
        example_ebi_search()
        example_metabolights()
        example_proteins_api()
        example_dbfetch()
        example_pdbe_api()
        example_ena_browser()
        example_arrayexpress()
        
        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETED")
        print("="*80)
        print("\nFor more information, see:")
        print("- EBI_API_GAP_ANALYSIS_REPORT.md")
        print("- EBI_APIS_IMPLEMENTATION_SUMMARY.md")
        
    except Exception as e:
        print(f"\n✗ Examples failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
