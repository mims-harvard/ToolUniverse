"""
Usage examples for ChIP-Atlas Tools

This file demonstrates common use cases for accessing chromatin data from
ChIP-Atlas (433,000+ ChIP-seq, ATAC-seq, Bisulfite-seq experiments).

Requirements:
    pip install tooluniverse
"""

from tooluniverse import ToolUniverse


def example_1_search_ctcf_experiments():
    """Example 1: Search for CTCF experiments in K562 cells."""
    print("=" * 70)
    print("Example 1: Search CTCF Experiments in K562")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.ChIPAtlas_get_experiments(**{
        "operation": "get_experiment_list",
        "genome": "hg38",
        "antigen": "CTCF",
        "cell_type": "K-562",
        "limit": 10
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_experiments']} experiments")
        
        if "experiments" in result and len(result["experiments"]) > 0:
            print("\n  Sample experiments:")
            for exp in result["experiments"][:3]:
                print(f"    - {exp['experiment_id']}: {exp['track_type']} in {exp['cell_type']}")
                print(f"      Title: {exp.get('title', 'N/A')[:60]}...")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_2_get_peak_data_urls():
    """Example 2: Get download URLs for peak data."""
    print("=" * 70)
    print("Example 2: Get Peak Data Download URLs")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    experiment_id = "SRX097088"
    
    # Get BigWig file (coverage data)
    bigwig_result = tu.tools.ChIPAtlas_get_peak_data(**{
        "operation": "get_peak_data",
        "experiment_id": experiment_id,
        "genome": "hg19",
        "format": "bigwig"
    })
    
    # Get BED file (peak calls)
    bed_result = tu.tools.ChIPAtlas_get_peak_data(**{
        "operation": "get_peak_data",
        "experiment_id": experiment_id,
        "genome": "hg19",
        "format": "bed",
        "threshold": "05"  # Q-value < 1e-5
    })
    
    print(f"Experiment: {experiment_id}")
    
    if bigwig_result["status"] == "success":
        print(f"\n✓ BigWig (coverage): {bigwig_result['url']}")
    
    if bed_result["status"] == "success":
        print(f"✓ BED (peaks):      {bed_result['url']}")
    
    print()


def example_3_enrichment_analysis_gene_list():
    """Example 3: Enrichment analysis with gene list."""
    print("=" * 70)
    print("Example 3: Enrichment Analysis - Gene List")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # p53 pathway genes
    gene_list = ["TP53", "MDM2", "CDKN1A", "BAX", "PUMA", "NOXA"]
    
    result = tu.tools.ChIPAtlas_enrichment_analysis(**{
        "operation": "enrichment_analysis",
        "gene_list": gene_list,
        "genome": "hg38",
        "distance": "5000",  # ±5kb from TSS
        "threshold": "05"
    })
    
    if result["status"] == "success":
        print("✓ Enrichment analysis prepared")
        print(f"  Genes: {', '.join(gene_list)}")
        print(f"  Genome: hg38")
        print(f"  Distance from TSS: ±5kb")
        print(f"\n  {result['message']}")
        print(f"  Submit at: {result.get('url', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_4_enrichment_analysis_motif():
    """Example 4: Enrichment analysis with DNA motif."""
    print("=" * 70)
    print("Example 4: Enrichment Analysis - DNA Motif")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # E-box motif (CANNTG) - recognized by MYC, MAX, etc.
    motif = "CANNTG"
    
    result = tu.tools.ChIPAtlas_enrichment_analysis(**{
        "operation": "enrichment_analysis",
        "motif": motif,
        "genome": "hg38",
        "threshold": "10"  # Q-value < 1e-10 (high confidence)
    })
    
    if result["status"] == "success":
        print(f"✓ Motif enrichment analysis prepared")
        print(f"  Motif: {motif} (E-box)")
        print(f"  {result['message']}")
        print(f"  {result.get('note', '')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_5_search_by_antigen():
    """Example 5: Search all datasets for specific antigen."""
    print("=" * 70)
    print("Example 5: Search Datasets by Antigen")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.ChIPAtlas_search_datasets(**{
        "operation": "search_datasets",
        "antigen": "H3K27ac",  # Active enhancer mark
        "genome": "hg38"
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_results']} datasets for H3K27ac")
        
        if "results" in result and len(result["results"]) > 0:
            print("\n  Sample datasets:")
            for dataset in result["results"][:3]:
                print(f"    - {dataset.get('name')}")
                print(f"      Experiments: {dataset.get('num_experiments')}")
                exp_ids = dataset.get('experiment_ids', [])
                if exp_ids:
                    print(f"      Sample IDs: {', '.join(exp_ids[:3])}...")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_6_workflow_compare_histone_marks():
    """Example 6: Workflow - Compare histone modifications."""
    print("=" * 70)
    print("Example 6: Workflow - Compare Histone Modifications")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Histone marks of interest
    marks = {
        "H3K4me3": "Active promoters",
        "H3K27ac": "Active enhancers",
        "H3K27me3": "Repressive mark"
    }
    
    print("Searching for histone modification experiments...\n")
    
    for mark, description in marks.items():
        result = tu.tools.ChIPAtlas_search_datasets(**{
            "operation": "search_datasets",
            "antigen": mark,
            "genome": "hg38"
        })
        
        if result["status"] == "success":
            num_datasets = result.get("num_results", 0)
            print(f"✓ {mark:12} ({description:20}): {num_datasets} datasets")
        else:
            print(f"✗ {mark:12}: Error - {result['error']}")
    
    print()


def example_7_batch_download_workflow():
    """Example 7: Batch download workflow."""
    print("=" * 70)
    print("Example 7: Workflow - Batch Download Peak Data")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Step 1: Find experiments
    search_result = tu.tools.ChIPAtlas_get_experiments(**{
        "operation": "get_experiment_list",
        "genome": "hg38",
        "antigen": "CTCF",
        "limit": 5
    })
    
    if search_result["status"] != "success":
        print(f"✗ Search failed: {search_result['error']}")
        return
    
    experiments = search_result.get("experiments", [])
    print(f"Step 1: Found {len(experiments)} CTCF experiments\n")
    
    # Step 2: Get download URLs for each
    print("Step 2: Getting download URLs...\n")
    
    download_urls = []
    for exp in experiments[:3]:  # Just first 3 for example
        exp_id = exp["experiment_id"]
        
        url_result = tu.tools.ChIPAtlas_get_peak_data(**{
            "operation": "get_peak_data",
            "experiment_id": exp_id,
            "genome": "hg38",
            "format": "bed",
            "threshold": "05"
        })
        
        if url_result["status"] == "success":
            download_urls.append(url_result["url"])
            print(f"  ✓ {exp_id}: {url_result['url']}")
    
    print(f"\nStep 3: Ready to download {len(download_urls)} files")
    print("  Use curl or wget to download:")
    print(f"  curl -O {download_urls[0]}")
    
    print()


def example_8_error_handling():
    """Example 8: Proper error handling."""
    print("=" * 70)
    print("Example 8: Error Handling")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Test 1: Missing required parameter
    result1 = tu.tools.ChIPAtlas_get_peak_data(**{
        "operation": "get_peak_data",
        "genome": "hg38"
        # Missing experiment_id
    })
    
    print("Test 1: Missing experiment_id")
    if result1["status"] == "error":
        print(f"  ✓ Error caught: {result1['error']}")
    
    # Test 2: Invalid format
    result2 = tu.tools.ChIPAtlas_get_peak_data(**{
        "operation": "get_peak_data",
        "experiment_id": "SRX000001",
        "genome": "hg38",
        "format": "invalid_format"
    })
    
    print("\nTest 2: Invalid format")
    if result2["status"] == "error":
        print(f"  ✓ Error caught: {result2['error']}")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("ChIP-Atlas Tools - Usage Examples")
    print("=" * 70 + "\n")
    
    example_1_search_ctcf_experiments()
    example_2_get_peak_data_urls()
    example_3_enrichment_analysis_gene_list()
    example_4_enrichment_analysis_motif()
    example_5_search_by_antigen()
    example_6_workflow_compare_histone_marks()
    example_7_batch_download_workflow()
    example_8_error_handling()
    
    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
