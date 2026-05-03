#!/usr/bin/env python3
"""
Usage examples for GEO tools in ToolUniverse

This script demonstrates how to use the GEO database tools for gene expression
dataset search, metadata retrieval, and sample information analysis.
"""

import sys
import os

# Ensure we import the local development version of the package
ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "src")
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from tooluniverse import ToolUniverse

def example_search_datasets():
    """Search for cancer-related datasets in human"""
    print("🔍 Searching for cancer datasets in human...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "geo_search_datasets",
        "arguments": {
            "query": "cancer",
            "organism": "Homo sapiens",
            "limit": 10
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        esearch = data.get('esearchresult', {})
        print(f"Found {esearch.get('count')} datasets")
        idlist = esearch.get('idlist', [])
        print(f"Dataset IDs: {idlist[:5]}")  # Show first 5
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_search_by_study_type():
    """Search for microarray datasets"""
    print("\n🔍 Searching for microarray datasets...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.run({
        "name": "geo_search_datasets",
        "arguments": {
            "query": "diabetes",
            "study_type": "Expression profiling by array",
            "limit": 5
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        esearch = data.get('esearchresult', {})
        print(f"Found {esearch.get('count')} microarray datasets")
        idlist = esearch.get('idlist', [])
        print(f"Dataset IDs: {idlist}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_dataset_info():
    """Get detailed information for a dataset using GSE accession"""
    print("\n📊 Getting dataset information for GSE15852...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Test with GSE accession number
    # (this was previously failing with "Invalid uid" error)
    result = tu.run({
        "name": "geo_get_dataset_info",
        "arguments": {
            "dataset_id": "GSE15852"  # GEO Series accession
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        # Check for error in the response data
        if 'error' in data:
            print(f"⚠️ API returned error: {data.get('error')}")
            return result
        
        result_data = data.get('result', {})
        if result_data:
            # Handle case where result is a dict with UIDs as keys
            if isinstance(result_data, dict) and 'uids' in result_data:
                uids = result_data.get('uids', [])
                if uids:
                    uid = uids[0]
                    dataset_info = result_data.get(uid, {})
                    print(f"Dataset UID: {uid}")
                    print(f"Title: {dataset_info.get('title', 'N/A')}")
                    summary = dataset_info.get('summary', 'N/A')
                    print(f"Summary: {summary[:100]}...")
                    print(f"Organism: {dataset_info.get('organism', 'N/A')}")
                    print(f"Platform: {dataset_info.get('platform', 'N/A')}")
                else:
                    print("No UIDs found in result")
            else:
                # Direct result structure
                print(f"Dataset UID: {result_data.get('uid', 'N/A')}")
                print(f"Title: {result_data.get('title', 'N/A')}")
                print(f"Organism: {result_data.get('organism', 'N/A')}")
                print(f"Platform: {result_data.get('platform', 'N/A')}")
        else:
            print("No dataset information found in result")
            print(f"Full response data: {data}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_get_sample_info():
    """Get sample information for a dataset using GSE accession"""
    print("\n🧬 Getting sample information for GSE15852...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Test with GSE accession number
    result = tu.run({
        "name": "geo_get_sample_info",
        "arguments": {
            "dataset_id": "GSE15852"  # GEO Series accession
        }
    })
    
    print(f"Status: {result.get('status')}")
    if result.get('status') == 'success':
        data = result.get('data', {})
        # Check for error in the response data
        if 'error' in data:
            print(f"⚠️ API returned error: {data.get('error')}")
            return result
        
        result_data = data.get('result', {})
        if result_data:
            # Handle case where result is a dict with UIDs as keys
            if isinstance(result_data, dict) and 'uids' in result_data:
                uids = result_data.get('uids', [])
                if uids:
                    uid = uids[0]
                    sample_info = result_data.get(uid, {})
                    print(f"Dataset UID: {uid}")
                    print(f"Title: {sample_info.get('title', 'N/A')}")
                    summary = sample_info.get('summary', 'N/A')
                    print(f"Summary: {summary[:100]}...")
                else:
                    print("No UIDs found in result")
            else:
                print(f"Dataset UID: {result_data.get('uid', 'N/A')}")
                samples = result_data.get('samples', [])
                if samples:
                    print(f"Number of samples: {len(samples)}")
                    for i, sample in enumerate(samples[:3]):  # Show first 3
                        sample_id = sample.get('sample_id', 'N/A')
                        chars = sample.get('characteristics', 'N/A')
                        print(f"  Sample {i+1}: {sample_id} - {chars}")
                else:
                    print("No sample information found")
        else:
            print("No sample information found in result")
            print(f"Full response data: {data}")
    else:
        print(f"Error: {result.get('error')}")
    
    return result

def example_test_different_accession_types():
    """Test different GEO accession types (GSE, GDS, GSM)"""
    print("\n🧪 Testing different accession types...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Test with GSE (GEO Series)
    print("\n  Testing GSE accession (GEO Series):")
    gse_result = tu.run({
        "name": "geo_get_dataset_info",
        "arguments": {
            "dataset_id": "GSE15852"
        }
    })
    print(f"    Status: {gse_result.get('status')}")
    if gse_result.get('status') == 'success' and 'error' not in gse_result.get('data', {}):
        print("    ✅ GSE accession works!")
    else:
        error_msg = gse_result.get(
            'error',
            gse_result.get('data', {}).get('error', 'Unknown error')
        )
        print(f"    ❌ GSE failed: {error_msg}")
    
    # Test with GDS (GEO Dataset) - if we can find one from search
    print("\n  Testing GDS accession (GEO Dataset):")
    # First search for a GDS
    search_result = tu.run({
        "name": "geo_search_datasets",
        "arguments": {
            "query": "cancer",
            "limit": 1
        }
    })
    
    if search_result.get('status') == 'success':
        data = search_result.get('data', {})
        esearch = data.get('esearchresult', {})
        idlist = esearch.get('idlist', [])
        
        if idlist:
            # GDS IDs from search are UIDs, but let's try to get info
            # Note: search returns UIDs, not accessions, so this tests UID handling
            gds_result = tu.run({
                "name": "geo_get_dataset_info",
                "arguments": {
                    "dataset_id": idlist[0]  # This is a UID, not an accession
                }
            })
            print(f"    Status: {gds_result.get('status')}")
            if gds_result.get('status') == 'success' and 'error' not in gds_result.get('data', {}):
                print("    ✅ GDS UID works!")
            else:
                print(f"    ❌ GDS failed: {gds_result.get('error', 'Unknown error')}")
        else:
            print("    ⚠️ No GDS datasets found to test")
    else:
        print("    ⚠️ Search failed, cannot test GDS")
    
    return gse_result

def example_combined_search():
    """Search for datasets and get info for the first result"""
    print("\n🔗 Combined search and info retrieval...")
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # First search for datasets
    search_result = tu.run({
        "name": "geo_search_datasets",
        "arguments": {
            "query": "breast cancer",
            "organism": "Homo sapiens",
            "limit": 3
        }
    })
    
    if search_result.get('status') == 'success':
        data = search_result.get('data', {})
        esearch = data.get('esearchresult', {})
        idlist = esearch.get('idlist', [])
        
        if idlist:
            print(
                f"Found {len(idlist)} datasets, "
                f"getting info for first one (UID: {idlist[0]})..."
            )
            
            # Get info for first dataset (this is a UID from search)
            info_result = tu.run({
                "name": "geo_get_dataset_info",
                "arguments": {
                    "dataset_id": idlist[0]  # This is a UID, tests UID handling
                }
            })
            
            print(f"Info status: {info_result.get('status')}")
            if info_result.get('status') == 'success':
                info_data = info_result.get('data', {})
                if 'error' in info_data:
                    print(f"⚠️ API error: {info_data.get('error')}")
                else:
                    result_data = info_data.get('result', {})
                    if result_data:
                        # Handle different result structures
                        if isinstance(result_data, dict) and 'uids' in result_data:
                            uids = result_data.get('uids', [])
                            if uids:
                                uid = uids[0]
                                dataset_info = result_data.get(uid, {})
                                print(f"Dataset: {dataset_info.get('title', 'N/A')}")
                                print(f"Organism: {dataset_info.get('organism', 'N/A')}")
                        else:
                            print(f"Dataset: {result_data.get('title', 'N/A')}")
                            print(f"Organism: {result_data.get('organism', 'N/A')}")
            else:
                print(f"Error getting info: {info_result.get('error')}")
        else:
            print("No datasets found")
    else:
        print(f"Search failed: {search_result.get('error')}")
    
    return search_result

def main():
    """Run all GEO tool examples"""
    print("🚀 GEO Tools Usage Examples")
    print("=" * 40)
    
    try:
        # Run examples
        example_search_datasets()
        example_search_by_study_type()
        
        # Test the fix for accession number to UID conversion
        print("\n" + "=" * 40)
        print("🔧 Testing Accession Number to UID Conversion Fix")
        print("=" * 40)
        example_get_dataset_info()
        example_get_sample_info()
        example_test_different_accession_types()
        
        example_combined_search()
        
        print("\n✅ All examples completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
