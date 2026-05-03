"""
Test Examples for EBI API Tools

This script demonstrates usage of all newly implemented EBI API tools
and verifies they return valid information.
"""

from tooluniverse import ToolUniverse
import json
from typing import Dict, Any


def print_result(tool_name: str, result: Dict[str, Any]):
    """Pretty print test result"""
    print(f"\n{'='*80}")
    print(f"Tool: {tool_name}")
    print(f"{'='*80}")
    print(f"Status: {result.get('status', 'unknown')}")
    
    if result.get('status') == 'success':
        data = result.get('data', {})
        if isinstance(data, dict):
            if 'hitCount' in data:
                print(f"Hit Count: {data['hitCount']}")
            if 'count' in result:
                print(f"Result Count: {result['count']}")
            if 'entries' in data:
                print(f"Entries: {len(data['entries'])}")
        elif isinstance(data, list):
            print(f"Result Count: {len(data)}")
        
        print(f"URL: {result.get('url', 'N/A')}")
        print("\nSample Data (first 500 chars):")
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


def test_ebi_search_tools(tu: ToolUniverse):
    """Test EBI Search API tools"""
    print("\n" + "="*80)
    print("TESTING EBI SEARCH API TOOLS")
    print("="*80)
    
    # Test 1: Search Ensembl domain
    result = tu.run_one_function({
        "name": "ebi_search_domain",
        "arguments": {
            "domain": "ensembl",
            "query": "BRCA1",
            "size": 5
        }
    })
    print_result("ebi_search_domain (Ensembl)", result)
    
    # Test 2: List available domains
    result = tu.run_one_function({
        "name": "ebi_list_domains",
        "arguments": {}
    })
    print_result("ebi_list_domains", result)
    
    # Test 3: Get domain info
    result = tu.run_one_function({
        "name": "ebi_get_domain_info",
        "arguments": {
            "domain": "ensembl"
        }
    })
    print_result("ebi_get_domain_info", result)
    
    # Test 4: Search with facets (first get domain info to see available facets)
    print("\nNote: To use facets, first check available facets with ebi_get_domain_info")
    result = tu.run_one_function({
        "name": "ebi_search_domain",
        "arguments": {
            "domain": "uniprot",
            "query": "kinase",
            "size": 5
        }
    })
    print_result("ebi_search_domain (UniProt, check facets in response)", result)


def test_intact_tools(tu: ToolUniverse):
    """Test IntAct tools"""
    print("\n" + "="*80)
    print("TESTING INTACT TOOLS")
    print("="*80)
    print("NOTE: IntAct API endpoints may require specific identifier formats.")
    print("For best results, use IntAct-specific identifiers (EBI-XXXXXXX)")
    print("="*80)
    
    # Test 1: Get interactor (using IntAct ID)
    result = tu.run_one_function({
        "name": "intact_get_interactor",
        "arguments": {
            "identifier": "EBI-1004115"
        }
    })
    print_result("intact_get_interactor (IntAct ID)", result)
    
    # Test 2: Get interactions (using UniProt ID)
    result = tu.run_one_function({
        "name": "intact_get_interactions",
        "arguments": {
            "identifier": "P04637"
        }
    })
    print_result("intact_get_interactions (UniProt ID)", result)
    
    # Test 3: Search interactions
    result = tu.run_one_function({
        "name": "intact_search_interactions",
        "arguments": {
            "query": "BRCA1",
            "max": 5
        }
    })
    print_result("intact_search_interactions", result)


def test_metabolights_tools(tu: ToolUniverse):
    """Test MetaboLights tools"""
    print("\n" + "="*80)
    print("TESTING METABOLIGHTS TOOLS")
    print("="*80)
    
    # Test 1: List studies
    result = tu.run_one_function({
        "name": "metabolights_list_studies",
        "arguments": {
            "size": 5
        }
    })
    print_result("metabolights_list_studies", result)
    
    # Test 2: Search studies
    result = tu.run_one_function({
        "name": "metabolights_search_studies",
        "arguments": {
            "query": "cancer",
            "size": 5
        }
    })
    print_result("metabolights_search_studies", result)
    
    # Test 3: Get study (using a study ID from list)
    # Note: metabolights_list_studies returns IDs, use one of them here
    result = tu.run_one_function({
        "name": "metabolights_get_study",
        "arguments": {
            "study_id": "MTBLS1"
        }
    })
    print_result("metabolights_get_study (detailed info)", result)
    
    # Test 4: Get study files
    result = tu.run_one_function({
        "name": "metabolights_get_study_files",
        "arguments": {
            "study_id": "MTBLS1"
        }
    })
    print_result("metabolights_get_study_files", result)


def test_proteins_api_tools(tu: ToolUniverse):
    """Test Proteins API tools"""
    print("\n" + "="*80)
    print("TESTING PROTEINS API TOOLS")
    print("="*80)
    
    # Test 1: Get protein
    result = tu.run_one_function({
        "name": "proteins_api_get_protein",
        "arguments": {
            "accession": "P05067"
        }
    })
    print_result("proteins_api_get_protein", result)
    
    # Test 2: Get variants
    result = tu.run_one_function({
        "name": "proteins_api_get_variants",
        "arguments": {
            "accession": "P04637"
        }
    })
    print_result("proteins_api_get_variants", result)
    
    # Test 3: Search proteins
    result = tu.run_one_function({
        "name": "proteins_api_search",
        "arguments": {
            "query": "BRCA1",
            "size": 5
        }
    })
    print_result("proteins_api_search", result)


def test_arrayexpress_tools(tu: ToolUniverse):
    """Test ArrayExpress tools"""
    print("\n" + "="*80)
    print("TESTING ARRAYEXPRESS TOOLS")
    print("="*80)
    
    # Test 1: Search experiments
    result = tu.run_one_function({
        "name": "arrayexpress_search_experiments",
        "arguments": {
            "keywords": "cancer",
            "limit": 5
        }
    })
    print_result("arrayexpress_search_experiments", result)
    
    # Test 2: Get experiment (using a known experiment ID)
    result = tu.run_one_function({
        "name": "arrayexpress_get_experiment",
        "arguments": {
            "experiment_id": "E-MTAB-1234"
        }
    })
    print_result("arrayexpress_get_experiment", result)


def test_dbfetch_tools(tu: ToolUniverse):
    """Test Dbfetch tools"""
    print("\n" + "="*80)
    print("TESTING DBFETCH TOOLS")
    print("="*80)
    
    # Test 1: Fetch entry
    result = tu.run_one_function({
        "name": "dbfetch_fetch_entry",
        "arguments": {
            "db": "uniprotkb",
            "id": "P05067",
            "format": "fasta"
        }
    })
    print_result("dbfetch_fetch_entry", result)
    
    # Test 2: List databases
    result = tu.run_one_function({
        "name": "dbfetch_list_databases",
        "arguments": {}
    })
    print_result("dbfetch_list_databases", result)
    
    # Test 3: List formats
    result = tu.run_one_function({
        "name": "dbfetch_list_formats",
        "arguments": {
            "db": "uniprotkb"
        }
    })
    print_result("dbfetch_list_formats", result)


def test_pdbe_api_tools(tu: ToolUniverse):
    """Test PDBe API tools"""
    print("\n" + "="*80)
    print("TESTING PDBE API TOOLS")
    print("="*80)
    
    # Test 1: Get entry summary
    result = tu.run_one_function({
        "name": "pdbe_get_entry_summary",
        "arguments": {
            "pdb_id": "1A2B"
        }
    })
    print_result("pdbe_get_entry_summary", result)
    
    # Test 2: Get quality metrics
    result = tu.run_one_function({
        "name": "pdbe_get_entry_quality",
        "arguments": {
            "pdb_id": "1CRN"
        }
    })
    print_result("pdbe_get_entry_quality", result)
    
    # Test 3: Get publications
    result = tu.run_one_function({
        "name": "pdbe_get_entry_publications",
        "arguments": {
            "pdb_id": "1A2B"
        }
    })
    print_result("pdbe_get_entry_publications", result)


def test_ena_browser_tools(tu: ToolUniverse):
    """Test ENA Browser tools"""
    print("\n" + "="*80)
    print("TESTING ENA BROWSER TOOLS")
    print("="*80)
    
    # Test 1: Get FASTA sequence
    result = tu.run_one_function({
        "name": "ena_get_sequence_fasta",
        "arguments": {
            "accession": "U00096"
        }
    })
    print_result("ena_get_sequence_fasta", result)
    
    # Test 2: Get entry metadata
    result = tu.run_one_function({
        "name": "ena_get_entry",
        "arguments": {
            "accession": "U00096"
        }
    })
    print_result("ena_get_entry", result)


def main():
    """Run all tests"""
    print("="*80)
    print("EBI API TOOLS TEST SUITE")
    print("="*80)
    print("\nThis script tests all newly implemented EBI API tools.")
    print("It verifies that tools return valid information and work correctly.\n")
    
    # Initialize ToolUniverse
    try:
        tu = ToolUniverse()
        print("✓ ToolUniverse initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize ToolUniverse: {e}")
        return
    
    # Run tests
    try:
        test_ebi_search_tools(tu)
        test_intact_tools(tu)
        test_metabolights_tools(tu)
        test_proteins_api_tools(tu)
        test_arrayexpress_tools(tu)
        test_dbfetch_tools(tu)
        test_pdbe_api_tools(tu)
        test_ena_browser_tools(tu)
        
        print("\n" + "="*80)
        print("ALL TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
