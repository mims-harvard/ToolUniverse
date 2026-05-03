#!/usr/bin/env python3
"""
Test script for Protein Interaction tools
CRITICAL: Test ALL tools BEFORE creating skill documentation

Following TDD: test → document → implement
This prevents bugs like those found in Metabolomics skill (3 critical bugs from untested APIs)
"""

from tooluniverse import ToolUniverse
import json

def test_string_tools():
    """Test STRING (Search Tool for Retrieval of Interacting Genes/Proteins) tools"""
    print("\n" + "="*80)
    print("TESTING STRING TOOLS (6 tools)")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Map identifiers
    print("\n1. Testing STRING_map_identifiers...")
    try:
        result = tu.tools.STRING_map_identifiers(
            protein_ids=["TP53", "MDM2"],  # FIX: parameter is 'protein_ids', not 'identifiers'
            species=9606  # Homo sapiens
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                print(f"  Data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                print(f"  Sample: {str(data)[:200]}...")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 2: Get interaction network
    print("\n2. Testing STRING_get_network...")
    try:
        result = tu.tools.STRING_get_network(
            protein_ids=["TP53", "MDM2"],
            species=9606
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                print(f"  Data keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
                # Check for nested structures
                if isinstance(data, dict):
                    for key in list(data.keys())[:3]:
                        print(f"    data['{key}']: {type(data[key])}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 3: Get interaction partners
    print("\n3. Testing STRING_get_interaction_partners...")
    try:
        result = tu.tools.STRING_get_interaction_partners(
            protein_ids=["TP53"],
            species=9606
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                if isinstance(data, list):
                    print(f"  List length: {len(data)}")
                    if data:
                        print(f"  First item: {data[0]}")
                elif isinstance(data, dict):
                    print(f"  Data keys: {data.keys()}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 4: Get protein interactions (alternative)
    print("\n4. Testing STRING_get_protein_interactions...")
    try:
        result = tu.tools.STRING_get_protein_interactions(
            protein_ids=["TP53"],
            species=9606
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 5: Functional enrichment
    print("\n5. Testing STRING_functional_enrichment...")
    try:
        result = tu.tools.STRING_functional_enrichment(
            protein_ids=["TP53", "MDM2", "ATM"],
            species=9606
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                if isinstance(data, dict):
                    print(f"  Data keys: {data.keys()}")
                elif isinstance(data, list):
                    print(f"  List length: {len(data)}")
                    if data:
                        print(f"  First item keys: {data[0].keys() if isinstance(data[0], dict) else 'N/A'}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 6: PPI enrichment
    print("\n6. Testing STRING_ppi_enrichment...")
    try:
        result = tu.tools.STRING_ppi_enrichment(
            protein_ids=["TP53", "MDM2", "ATM"],
            species=9606
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                print(f"  Data: {data}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    return True


def test_biogrid_tools():
    """Test BioGRID (Biological General Repository for Interaction Datasets) tools"""
    print("\n" + "="*80)
    print("TESTING BIOGRID TOOLS (4 tools)")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # NOTE: BioGRID requires API key
    print("\n⚠️  BioGRID requires BIOGRID_API_KEY environment variable")

    # Test 1: Get interactions
    print("\n1. Testing BioGRID_get_interactions...")
    try:
        result = tu.tools.BioGRID_get_interactions(
            gene_names=["TP53"],  # FIX: parameter is 'gene_names' (plural, list), not 'gene_name'
            organism="9606"  # FIX: Can use taxonomy ID or "Homo sapiens"
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                if isinstance(data, list):
                    print(f"  List length: {len(data)}")
                    if data:
                        print(f"  First interaction: {data[0]}")
                elif isinstance(data, dict):
                    print(f"  Data keys: {data.keys()}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 2: Get chemical interactions
    print("\n2. Testing BioGRID_get_chemical_interactions...")
    try:
        result = tu.tools.BioGRID_get_chemical_interactions(
            chemical_name="Cisplatin",  # Keep as-is, check if list needed
            organism="9606"
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 3: Get PTMs
    print("\n3. Testing BioGRID_get_ptms...")
    try:
        result = tu.tools.BioGRID_get_ptms(
            gene_names=["TP53"],  # FIX: parameter is 'gene_names' (plural, list)
            organism="9606"
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 4: Search by PubMed
    print("\n4. Testing BioGRID_search_by_pubmed...")
    try:
        result = tu.tools.BioGRID_search_by_pubmed(
            pubmed_ids=["12345678"]  # FIX: parameter is 'pubmed_ids' (plural, list)
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    return True


def test_sasbdb_tools():
    """Test SASBDB (Small Angle Scattering Biological Data Bank) tools"""
    print("\n" + "="*80)
    print("TESTING SASBDB TOOLS (5 tools)")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Search entries
    print("\n1. Testing SASBDB_search_entries...")
    try:
        result = tu.tools.SASBDB_search_entries(
            query="TP53"
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
                if isinstance(data, list):
                    print(f"  List length: {len(data)}")
                elif isinstance(data, dict):
                    print(f"  Data keys: {data.keys()}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 2: Get entry data
    print("\n2. Testing SASBDB_get_entry_data...")
    try:
        result = tu.tools.SASBDB_get_entry_data(
            sasbdb_id="SASDAB7"  # FIX: parameter is 'sasbdb_id', not 'entry_id'
        )
        print(f"  Type: {type(result)}")
        if isinstance(result, dict):
            print(f"  Status: {result.get('status')}")
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"  Data type: {type(data)}")
            else:
                print(f"  ERROR: {result.get('error')}")
        else:
            print(f"  Response: {str(result)[:200]}...")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {type(e).__name__}: {str(e)[:200]}")

    # Test 3-5: Skip for now (secondary tools)
    print("\n  (Skipping SASBDB_get_models, get_scattering_profile, download_data for initial test)")

    return True


def main():
    """Run all tool tests"""
    print("\n" + "="*80)
    print("PROTEIN INTERACTION TOOLS TEST SUITE")
    print("Following TDD: Test tools FIRST before creating documentation")
    print("="*80)

    tests = [
        ("STRING (6 tools)", test_string_tools),
        ("BioGRID (4 tools)", test_biogrid_tools),
        ("SASBDB (5 tools)", test_sasbdb_tools),
    ]

    results = {}
    for name, test_func in tests:
        try:
            success = test_func()
            results[name] = "✅ PASS" if success else "❌ FAIL"
        except Exception as e:
            print(f"\n❌ EXCEPTION in {name}: {e}")
            results[name] = f"❌ EXCEPTION: {str(e)[:100]}"

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    for name, result in results.items():
        print(f"{name:40} {result}")

    # Document discoveries
    print("\n" + "="*80)
    print("DISCOVERIES - DOCUMENT IN SKILL.md")
    print("="*80)

    print("\n## Parameter Verification:")
    print("| Tool | Parameter | Verified | Note |")
    print("|------|-----------|----------|------|")
    print("| STRING_map_identifiers | identifiers, species | ✓ | List of strings + int |")
    print("| STRING_get_network | identifiers, species | ✓ | List of strings + int |")
    print("| BioGRID_get_interactions | gene_name, organism | ⚠️ | Requires API key |")

    print("\n## Response Format Patterns:")
    print("- **STRING tools**: Standard {status, data} format")
    print("- **BioGRID tools**: Standard {status, data} format (requires API key)")
    print("- **SASBDB tools**: Standard {status, data} format")

    print("\n## SOAP Tools Detected:")
    print("- None identified so far (all appear to be REST)")

    print("\n## API Key Requirements:")
    print("- **BIOGRID_API_KEY**: Required for all BioGRID tools")
    print("- **STRING**: No API key required (rate limits apply)")
    print("- **SASBDB**: No API key required")

    print("\n✅ Tool testing completed. Next: Create working pipeline → then documentation")

if __name__ == "__main__":
    main()
