#!/usr/bin/env python3
"""Quick manual test of newly implemented tools"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from tooluniverse import ToolUniverse

    print("Initializing ToolUniverse...")
    tu = ToolUniverse()
    tu.load_tools()

    print(f"\nTotal tools loaded: {len(tu.tools)}")

    # Check if target tools are loaded
    target_tools = [
        "STRING_get_network",
        "STRING_get_protein_interactions",
        "STRING_get_interaction_partners",
        "STRING_functional_enrichment",
        "STRING_map_identifiers",
        "STRING_ppi_enrichment",
        "BioGRID_get_interactions",
        "BioGRID_get_chemical_interactions",
        "BioGRID_search_by_pubmed",
        "BioGRID_get_ptms",
        "NCBI_SRA_search_runs",
        "NCBI_SRA_get_run_info",
        "NCBI_SRA_get_download_urls",
        "NCBI_SRA_link_to_biosample",
        "ICD11_search_diseases",
        "ICD11_get_entity",
        "ICD11_browse_hierarchy",
        "ICD10_search_codes",
        "ICD10_get_code_info",
        "LOINC_search_tests",
        "LOINC_get_code_details",
        "LOINC_get_answer_list",
        "LOINC_search_forms",
        "SASBDB_search_entries",
        "SASBDB_get_entry_data",
        "SASBDB_get_scattering_profile",
        "SASBDB_get_models",
        "SASBDB_download_data",
        "ProteinsPlus_predict_binding_sites",
        "ProteinsPlus_dock_ligand",
        "ProteinsPlus_analyze_interactions",
        "ProteinsPlus_check_structure",
    ]

    print("\n" + "="*70)
    print("TOOL LOADING STATUS")
    print("="*70)

    loaded = []
    not_loaded = []

    for tool in target_tools:
        if tool in tu.tools:
            loaded.append(tool)
            print(f"✅ {tool}")
        else:
            not_loaded.append(tool)
            print(f"❌ {tool} - NOT FOUND")

    print(f"\n{'='*70}")
    print(f"Loaded: {len(loaded)}/32")
    print(f"Not Loaded: {len(not_loaded)}/32")
    print(f"{'='*70}\n")

    if not_loaded:
        print("❌ Some tools are not loaded!")
        sys.exit(1)

    # Test one tool from each category
    print("\n" + "="*70)
    print("RUNNING BASIC TESTS")
    print("="*70)

    # Test STRING (no auth required)
    print("\n1. Testing STRING_map_identifiers...")
    try:
        result = tu.run_one_function({
            "name": "STRING_map_identifiers",
            "arguments": {
                "protein_ids": ["TP53"],
                "species": 9606,
                "limit": 1
            }
        })
        if isinstance(result, list) and len(result) > 0:
            print("   ✅ PASS - Got results")
        elif isinstance(result, dict) and result.get("error"):
            print(f"   ❌ FAIL - {result.get('error')}")
        else:
            print(f"   ⚠️ UNKNOWN - Result: {type(result)}")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    # Test NCBI SRA (no auth required)
    print("\n2. Testing NCBI_SRA_search_runs...")
    try:
        result = tu.run_one_function({
            "name": "NCBI_SRA_search_runs",
            "arguments": {
                "operation": "search",
                "organism": "Homo sapiens",
                "strategy": "RNA-Seq",
                "limit": 2
            }
        })
        if isinstance(result, dict):
            if result.get("status") == "success":
                print("   ✅ PASS - Search successful")
            elif result.get("error"):
                print(f"   ❌ FAIL - {result.get('error')}")
            else:
                print(f"   ⚠️ UNKNOWN - {result}")
        else:
            print(f"   ⚠️ UNKNOWN - Result type: {type(result)}")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    # Test ICD10 (no auth required)
    print("\n3. Testing ICD10_search_codes...")
    try:
        result = tu.run_one_function({
            "name": "ICD10_search_codes",
            "arguments": {
                "query": "diabetes",
                "limit": 5
            }
        })
        if isinstance(result, dict):
            if result.get("status") == "success" or result.get("data"):
                print("   ✅ PASS - Search successful")
            elif result.get("error"):
                print(f"   ❌ FAIL - {result.get('error')}")
            else:
                print(f"   ⚠️ UNKNOWN - {result}")
        else:
            print(f"   ⚠️ UNKNOWN - Result type: {type(result)}")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    # Test LOINC (no auth required)
    print("\n4. Testing LOINC_search_tests...")
    try:
        result = tu.run_one_function({
            "name": "LOINC_search_tests",
            "arguments": {
                "terms": "cholesterol",
                "max_results": 5
            }
        })
        if isinstance(result, dict):
            if result.get("results") or result.get("count", 0) > 0:
                print("   ✅ PASS - Search successful")
            elif result.get("error"):
                print(f"   ❌ FAIL - {result.get('error')}")
            else:
                print(f"   ⚠️ UNKNOWN - {result}")
        else:
            print(f"   ⚠️ UNKNOWN - Result type: {type(result)}")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    # Test SASBDB (no auth required)
    print("\n5. Testing SASBDB_search_entries...")
    try:
        result = tu.run_one_function({
            "name": "SASBDB_search_entries",
            "arguments": {
                "query": "lysozyme",
                "method": "SAXS",
                "limit": 5
            }
        })
        if result:
            print(f"   ✅ PASS - Got result (type: {type(result)})")
        else:
            print("   ❌ FAIL - No result")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    # Test ProteinsPlus (may have API issues)
    print("\n6. Testing ProteinsPlus_check_structure...")
    try:
        result = tu.run_one_function({
            "name": "ProteinsPlus_check_structure",
            "arguments": {
                "pdb_id": "1A2B"
            }
        })
        if result:
            if isinstance(result, dict) and result.get("error"):
                print(f"   ⚠️ API ISSUE - {result.get('error')}")
            else:
                print(f"   ✅ PASS - Got result")
        else:
            print("   ❌ FAIL - No result")
    except Exception as e:
        print(f"   🔥 EXCEPTION - {str(e)}")

    print("\n" + "="*70)
    print("BASIC TESTS COMPLETE")
    print("="*70)
    print("\nNote: Tools requiring API keys (BioGRID, ICD11) were not tested.")
    print("These require environment variables: BIOGRID_ACCESS_KEY, ICD_CLIENT_ID, ICD_CLIENT_SECRET")

except Exception as e:
    print(f"\n❌ Fatal error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
