"""
Comprehensive Examples for 4 Scientific APIs

This module demonstrates tools from:
1. BioModels - Systems biology computational models
2. HCA (Human Cell Atlas) - Single-cell data
3. IEDB (Immune Epitope Database) - Immunology data
4. Pathway Commons - Biological pathway interactions

All these tools were discovered as complete implementations needing tests/examples.

Author: ToolUniverse
Date: February 2026
"""

from tooluniverse import ToolUniverse


def example_1_biomodels_search():
    """
    Example 1: Search BioModels for systems biology models
    
    BioModels database contains computational models of biological processes
    in SBML and other formats, used for simulation and analysis.
    """
    print("\n" + "="*80)
    print("Example 1: Search BioModels for Computational Models")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search for glycolysis models
    result = tu.tools.biomodels_search(**{
        "query": "glycolysis",
        "limit": 3
    })
    
    if result["status"] == "success" and "data" in result:
        matches = result["data"].get("matches", [])
        print(f"\n✅ Found {result.get('count', 0)} glycolysis models")
        
        if matches:
            print("\nTop results:")
            for i, model in enumerate(matches[:3], 1):
                print(f"\n{i}. {model.get('name', 'N/A')}")
                print(f"   ID: {model.get('id', 'N/A')}")
                print(f"   Format: {model.get('format', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_2_biomodels_get_and_download():
    """
    Example 2: Get BioModels metadata and download information
    
    Retrieve detailed information about a specific model and get download URLs.
    """
    print("\n" + "="*80)
    print("Example 2: BioModels - Get Model Details and Files")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    model_id = "BIOMD0000000469"
    
    # Get model metadata
    result = tu.tools.BioModels_get_model(**{"model_id": model_id})
    
    if result["status"] == "success" and "data" in result:
        model = result["data"]
        print(f"\n✅ Model: {model.get('name', 'N/A')}")
        print(f"   Format: {model.get('format', 'N/A')}")
        print(f"   Created: {model.get('created', 'N/A')}")
        
        # List available files
        files_result = tu.tools.BioModels_list_files(**{"model_id": model_id})
        if files_result["status"] == "success":
            print(f"\n   Files available: {files_result.get('count', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_3_hca_search_projects():
    """
    Example 3: Search Human Cell Atlas projects by organ
    
    HCA contains single-cell RNA-seq data from various organs and diseases.
    Find projects filtering by organ or disease.
    """
    print("\n" + "="*80)
    print("Example 3: Human Cell Atlas - Search Projects by Organ")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search for heart projects
    result = tu.tools.hca_search_projects(**{
        "action": "search_projects",
        "organ": "heart",
        "limit": 3
    })
    
    if "projects" in result and not result.get("error"):
        print(f"\n✅ Found {result.get('total_hits', 0)} heart projects")
        
        for i, project in enumerate(result["projects"][:3], 1):
            print(f"\n{i}. {project.get('projectTitle', 'N/A')}")
            print(f"   ID: {project.get('entryId', 'N/A')}")
            print(f"   Organs: {project.get('organ', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_4_hca_get_files():
    """
    Example 4: Get downloadable files from HCA project
    
    Retrieve file manifest with download URLs for a specific project.
    """
    print("\n" + "="*80)
    print("Example 4: HCA - Get Project File Manifest")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Using example project ID
    project_id = "7027adc6-c9c9-46f3-84ee-9badc3a4f53b"
    
    result = tu.tools.hca_get_file_manifest(**{
        "action": "get_file_manifest",
        "project_id": project_id,
        "limit": 5
    })
    
    if "files" in result and not result.get("error"):
        print(f"\n✅ Found {result.get('total_files', 0)} total files")
        print(f"   Showing first {len(result['files'])} files:")
        
        for i, file in enumerate(result["files"][:5], 1):
            print(f"\n{i}. {file.get('name', 'N/A')}")
            print(f"   Format: {file.get('format', 'N/A')}")
            print(f"   Size: {file.get('size', 0)} bytes")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_5_iedb_search_epitopes():
    """
    Example 5: Search IEDB for epitopes
    
    IEDB contains immune epitope data for vaccine design and immunology research.
    Search for epitopes with various filters.
    """
    print("\n" + "="*80)
    print("Example 5: IEDB - Search Epitopes")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search epitopes
    result = tu.tools.iedb_search_epitopes(**{"limit": 5})
    
    if result["status"] == "success" and "data" in result:
        epitopes = result["data"]
        print(f"\n✅ Found {len(epitopes)} epitopes")
        
        for i, epitope in enumerate(epitopes[:3], 1):
            print(f"\n{i}. Epitope ID: {epitope.get('epitope_id', 'N/A')}")
            print(f"   Sequence: {epitope.get('linear_sequence', 'N/A')[:50]}")
            print(f"   Type: {epitope.get('structure_type', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_6_iedb_search_antigens():
    """
    Example 6: Search IEDB for antigens and MHC data
    
    Find antigens and MHC binding information useful for immunology research.
    """
    print("\n" + "="*80)
    print("Example 6: IEDB - Search Antigens and MHC")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search antigens
    antigen_result = tu.tools.iedb_search_antigens(**{"limit": 3})
    
    if antigen_result["status"] == "success":
        print(f"\n✅ Antigens found: {len(antigen_result.get('data', []))}")
    
    # Search MHC binding data
    mhc_result = tu.tools.iedb_search_mhc(**{"limit": 3})
    
    if mhc_result["status"] == "success":
        print(f"✅ MHC entries found: {len(mhc_result.get('data', []))}")


def example_7_pathway_commons_search():
    """
    Example 7: Search Pathway Commons for biological pathways
    
    Pathway Commons aggregates pathway data from multiple sources
    (Reactome, KEGG, PANTHER, etc.) for comprehensive pathway analysis.
    """
    print("\n" + "="*80)
    print("Example 7: Pathway Commons - Search Pathways")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Search for apoptosis pathways
    result = tu.tools.pc_search_pathways(**{
        "action": "search_pathways",
        "keyword": "apoptosis",
        "limit": 5
    })
    
    if "pathways" in result and not result.get("error"):
        print(f"\n✅ Found {result.get('total_hits', 0)} apoptosis pathways")
        
        for i, pathway in enumerate(result["pathways"][:3], 1):
            print(f"\n{i}. {pathway.get('name', 'N/A')}")
            print(f"   Source: {pathway.get('source', 'N/A')}")
            print(f"   Organism: {pathway.get('organism', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_8_pathway_commons_interactions():
    """
    Example 8: Get gene interaction network from Pathway Commons
    
    Retrieve interaction networks for specific genes in SIF format,
    showing relationships like controls, binds, or participates with.
    """
    print("\n" + "="*80)
    print("Example 8: Pathway Commons - Gene Interaction Network")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Get interactions for TP53 and MDM2
    result = tu.tools.pc_get_interactions(**{
        "action": "get_interaction_graph",
        "gene_list": ["TP53", "MDM2"]
    })
    
    if "interactions" in result and not result.get("error"):
        print(f"\n✅ Found {len(result['interactions'])} interactions")
        print(f"   Format: {result.get('format', 'N/A')}")
        
        print("\nInteractions:")
        for i, interaction in enumerate(result["interactions"][:10], 1):
            print(f"{i}. {interaction.get('source', 'N/A')} "
                  f"--[{interaction.get('relation', 'N/A')}]--> "
                  f"{interaction.get('target', 'N/A')}")
    else:
        print(f"❌ Error: {result.get('error', 'Unknown')}")


def example_9_cross_database_workflow():
    """
    Example 9: Cross-database workflow combining multiple tools
    
    Demonstrate using multiple APIs together for comprehensive analysis:
    1. Search pathways in Pathway Commons
    2. Find computational models in BioModels
    3. Look up immune data in IEDB
    """
    print("\n" + "="*80)
    print("Example 9: Cross-Database Workflow")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    keyword = "p53"
    
    print(f"\nSearching for '{keyword}' across databases...")
    
    # 1. Pathway Commons
    pc_result = tu.tools.pc_search_pathways(**{
        "action": "search_pathways",
        "keyword": keyword,
        "limit": 2
    })
    if "pathways" in pc_result:
        print(f"\n✅ Pathway Commons: {pc_result.get('total_hits', 0)} pathways")
    
    # 2. BioModels
    bm_result = tu.tools.biomodels_search(**{
        "query": keyword,
        "limit": 2
    })
    if bm_result["status"] == "success":
        print(f"✅ BioModels: {bm_result.get('count', 0)} models")
    
    # 3. IEDB (search epitopes)
    iedb_result = tu.tools.iedb_search_epitopes(**{"limit": 2})
    if iedb_result["status"] == "success":
        print(f"✅ IEDB: {len(iedb_result.get('data', []))} epitopes")
    
    print("\nCross-database search complete!")


def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("4 SCIENTIFIC APIs - COMPREHENSIVE USAGE EXAMPLES")
    print("="*80)
    print("\nDemonstrating:")
    print("• BioModels - Systems biology computational models")
    print("• HCA - Human Cell Atlas single-cell data")
    print("• IEDB - Immune Epitope Database")
    print("• Pathway Commons - Biological pathway networks")
    
    # Run examples
    example_1_biomodels_search()
    example_2_biomodels_get_and_download()
    example_3_hca_search_projects()
    example_4_hca_get_files()
    example_5_iedb_search_epitopes()
    example_6_iedb_search_antigens()
    example_7_pathway_commons_search()
    example_8_pathway_commons_interactions()
    example_9_cross_database_workflow()
    
    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80)
    print("\n📚 Resources:")
    print("- BioModels: https://www.ebi.ac.uk/biomodels/")
    print("- HCA: https://data.humancellatlas.org/")
    print("- IEDB: https://www.iedb.org/")
    print("- Pathway Commons: https://www.pathwaycommons.org/")
    print("\n💡 Tips:")
    print("- BioModels: Great for finding validated computational models")
    print("- HCA: Filter by organ/disease for targeted single-cell data")
    print("- IEDB: Essential for vaccine design and immunology research")
    print("- Pathway Commons: Aggregates pathways from multiple sources")


if __name__ == "__main__":
    main()
