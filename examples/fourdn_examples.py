"""
Usage examples for 4DN Data Portal Tools

This file demonstrates common use cases for accessing Hi-C and 3D genome
organization data from the 4DN Data Portal.

Requirements:
    pip install tooluniverse

Authentication:
    File downloads require a free 4DN account.
    Create account at: https://data.4dnucleome.org/
    Generate access key in your profile
"""

from tooluniverse import ToolUniverse


def example_1_search_hic_data():
    """Example 1: Search for Hi-C datasets."""
    print("=" * 70)
    print("Example 1: Search Hi-C Datasets")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.FourDN_search_data(**{
        "operation": "search",
        "query": "*",
        "assay_title": "Hi-C",
        "limit": 10
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['total']} Hi-C datasets (showing {result['num_results']})")
        
        if "results" in result and len(result["results"]) > 0:
            print("\n  Sample datasets:")
            for item in result["results"][:3]:
                accession = item.get("accession", "N/A")
                description = item.get("description", "No description")[:60]
                print(f"    - {accession}")
                print(f"      {description}...")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_2_search_by_cell_type():
    """Example 2: Search Hi-C data for specific cell type."""
    print("=" * 70)
    print("Example 2: Search by Cell Type (GM12878)")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.FourDN_search_data(**{
        "operation": "search",
        "query": "*",
        "assay_title": "Hi-C",
        "biosource_name": "GM12878",
        "limit": 10
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_results']} GM12878 Hi-C datasets")
        
        if "results" in result:
            print(f"  Total available: {result.get('total', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_3_get_file_metadata():
    """Example 3: Get detailed file metadata."""
    print("=" * 70)
    print("Example 3: Get File Metadata")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Example file accession
    file_accession = "4DNFIIA7E3HL"
    
    result = tu.tools.FourDN_get_file_metadata(**{
        "operation": "get_file_metadata",
        "file_accession": file_accession
    })
    
    if result["status"] == "success":
        print(f"✓ File: {result['accession']}")
        print(f"  Type: {result.get('file_type', 'N/A')}")
        print(f"  Format: {result.get('file_format', 'N/A')}")
        
        size = result.get('file_size', 0)
        if size:
            size_mb = size / (1024 * 1024)
            print(f"  Size: {size_mb:.2f} MB")
        
        print(f"  Status: {result.get('status', 'N/A')}")
        print(f"  Download: {result.get('download_url', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_4_get_experiment_info():
    """Example 4: Get experiment metadata."""
    print("=" * 70)
    print("Example 4: Get Experiment Metadata")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Example experiment accession
    experiment_accession = "4DNEXO67APU1"
    
    result = tu.tools.FourDN_get_experiment_metadata(**{
        "operation": "get_experiment_metadata",
        "experiment_accession": experiment_accession
    })
    
    if result["status"] == "success":
        print(f"✓ Experiment: {result['accession']}")
        print(f"  Type: {result.get('experiment_type', 'N/A')}")
        print(f"  Description: {result.get('description', 'N/A')[:60]}...")
        
        files = result.get('files', [])
        print(f"  Files: {len(files)} associated files")
        
        if files:
            print("\n  Sample files:")
            for file_ref in files[:3]:
                # File references are usually just accessions or UUIDs
                print(f"    - {file_ref}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_5_get_download_urls():
    """Example 5: Get download URLs for files."""
    print("=" * 70)
    print("Example 5: Get Download URLs")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    file_accession = "4DNFIIA7E3HL"
    
    result = tu.tools.FourDN_get_download_url(**{
        "operation": "download_file_url",
        "file_accession": file_accession
    })
    
    if result["status"] == "success":
        print(f"✓ Download information for {result['accession']}:")
        print(f"\n  Download URL:")
        print(f"    {result['download_url']}")
        print(f"\n  DRS API URL:")
        print(f"    {result['drs_url']}")
        print(f"\n  {result.get('note', '')}")
        print(f"\n  {result.get('instruction', '')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_6_workflow_find_tad_boundaries():
    """Example 6: Workflow - Find TAD boundary files."""
    print("=" * 70)
    print("Example 6: Workflow - Find TAD Boundary Files")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Step 1: Search for files with 'TAD' in description
    print("Step 1: Searching for TAD-related files...\n")
    
    search_result = tu.tools.FourDN_search_data(**{
        "operation": "search",
        "query": "TAD",
        "item_type": "File",
        "limit": 10
    })
    
    if search_result["status"] != "success":
        print(f"✗ Search failed: {search_result['error']}")
        return
    
    results = search_result.get("results", [])
    print(f"✓ Found {len(results)} TAD-related files\n")
    
    # Step 2: Get details for each file
    print("Step 2: Getting file details...\n")
    
    for item in results[:3]:  # Just first 3
        accession = item.get("accession")
        if not accession:
            continue
        
        file_result = tu.tools.FourDN_get_file_metadata(**{
            "operation": "get_file_metadata",
            "file_accession": accession
        })
        
        if file_result["status"] == "success":
            print(f"  ✓ {accession}")
            print(f"    Type: {file_result.get('file_type', 'N/A')}")
            print(f"    Format: {file_result.get('file_format', 'N/A')}")
            size = file_result.get('file_size', 0)
            if size:
                print(f"    Size: {size / (1024*1024):.2f} MB")
            print()
    
    print()


def example_7_workflow_compare_hic_datasets():
    """Example 7: Workflow - Compare Hi-C datasets across cell types."""
    print("=" * 70)
    print("Example 7: Workflow - Compare Hi-C Across Cell Types")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    cell_types = ["GM12878", "H1-hESC", "HFFc6"]
    
    print("Comparing Hi-C data availability...\n")
    
    for cell_type in cell_types:
        result = tu.tools.FourDN_search_data(**{
            "operation": "search",
            "query": "*",
            "assay_title": "Hi-C",
            "biosource_name": cell_type,
            "limit": 100
        })
        
        if result["status"] == "success":
            total = result.get("total", 0)
            num_results = result.get("num_results", 0)
            print(f"  {cell_type:12}: {num_results} files found (total: {total})")
        else:
            print(f"  {cell_type:12}: Error - {result['error']}")
    
    print()


def example_8_search_micro_c():
    """Example 8: Search for Micro-C data (higher resolution)."""
    print("=" * 70)
    print("Example 8: Search Micro-C Data (High Resolution)")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.FourDN_search_data(**{
        "operation": "search",
        "query": "Micro-C",
        "item_type": "File",
        "limit": 10
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_results']} Micro-C files")
        
        if "results" in result and len(result["results"]) > 0:
            print("\n  Sample Micro-C datasets:")
            for item in result["results"][:3]:
                accession = item.get("accession", "N/A")
                desc = item.get("description", "No description")
                print(f"    - {accession}: {desc[:50]}...")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_9_error_handling():
    """Example 9: Proper error handling."""
    print("=" * 70)
    print("Example 9: Error Handling")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Test 1: Missing required parameter
    result1 = tu.tools.FourDN_get_file_metadata(**{
        "operation": "get_file_metadata"
        # Missing file_accession
    })
    
    print("Test 1: Missing file_accession")
    if result1["status"] == "error":
        print(f"  ✓ Error caught: {result1['error']}")
    
    # Test 2: Invalid accession
    result2 = tu.tools.FourDN_get_file_metadata(**{
        "operation": "get_file_metadata",
        "file_accession": "INVALID_ACCESSION"
    })
    
    print("\nTest 2: Invalid accession")
    if result2["status"] == "error":
        print(f"  ✓ Error caught: {result2['error']}")
    else:
        print("  (Request may succeed with 404 response from server)")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("4DN Data Portal Tools - Usage Examples")
    print("=" * 70 + "\n")
    
    example_1_search_hic_data()
    example_2_search_by_cell_type()
    example_3_get_file_metadata()
    example_4_get_experiment_info()
    example_5_get_download_urls()
    example_6_workflow_find_tad_boundaries()
    example_7_workflow_compare_hic_datasets()
    example_8_search_micro_c()
    example_9_error_handling()
    
    print("=" * 70)
    print("Examples completed!")
    print("\nNote: To download files, create a free account at:")
    print("https://data.4dnucleome.org/")
    print("=" * 70)


if __name__ == "__main__":
    main()
