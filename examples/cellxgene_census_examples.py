"""
Usage examples for CELLxGENE Census Tools

This file demonstrates common use cases for accessing single-cell RNA-seq data
from the CELLxGENE Census (50M+ cells).

Requirements:
    pip install tooluniverse
    pip install cellxgene-census  # Optional, for full functionality
"""

from tooluniverse import ToolUniverse
import sys


def check_package_installed():
    """Check if cellxgene-census package is installed."""
    try:
        import cellxgene_census
        return True
    except ImportError:
        print("WARNING: cellxgene-census package not installed.")
        print("Install with: pip install cellxgene-census")
        print("Continuing with limited functionality...\n")
        return False


def example_1_get_available_versions():
    """Example 1: Get available Census versions."""
    print("=" * 70)
    print("Example 1: Get Available Census Versions")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.CELLxGENE_get_census_versions(**{
        "operation": "get_census_versions"
    })
    
    if result["status"] == "success":
        print("✓ Available Census versions:")
        versions = result.get("versions", {})
        
        # Show latest stable version
        if isinstance(versions, dict):
            for key in ["stable", "latest"]:
                if key in versions:
                    print(f"  - {key}: {versions[key]}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_2_query_brain_cells():
    """Example 2: Query cell metadata for brain tissue."""
    print("=" * 70)
    print("Example 2: Query Brain Cells")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    result = tu.tools.CELLxGENE_get_cell_metadata(**{
        "operation": "get_obs_metadata",
        "organism": "Homo sapiens",
        "obs_value_filter": "tissue == 'brain' and disease == 'normal'",
        "census_version": "stable"
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_cells']} brain cells")
        print(f"  Available metadata columns: {len(result.get('columns', []))}")
        
        # Show sample of data if available
        if "data" in result and len(result["data"]) > 0:
            print("\n  Sample cell metadata:")
            sample = result["data"][0]
            for key in list(sample.keys())[:5]:  # Show first 5 fields
                print(f"    - {key}: {sample[key]}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_3_find_cancer_marker_genes():
    """Example 3: Search for specific genes (cancer markers)."""
    print("=" * 70)
    print("Example 3: Find Cancer Marker Genes")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Search for common cancer marker genes
    marker_genes = ["TP53", "KRAS", "EGFR", "MYC", "BRCA1"]
    
    result = tu.tools.CELLxGENE_get_gene_metadata(**{
        "operation": "get_var_metadata",
        "organism": "Homo sapiens",
        "var_value_filter": f"feature_name in {marker_genes}",
        "census_version": "stable"
    })
    
    if result["status"] == "success":
        print(f"✓ Found {result['num_genes']} genes")
        
        if "data" in result and len(result["data"]) > 0:
            print("\n  Gene information:")
            for gene in result["data"]:
                feature_name = gene.get("feature_name", "Unknown")
                feature_id = gene.get("feature_id", "Unknown")
                print(f"    - {feature_name} ({feature_id})")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_4_access_embeddings():
    """Example 4: Access pre-calculated embeddings."""
    print("=" * 70)
    print("Example 4: Access Pre-calculated Embeddings")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Get available embeddings
    result = tu.tools.CELLxGENE_get_embeddings(**{
        "operation": "get_embeddings",
        "organism": "Homo sapiens",
        "census_version": "stable"
    })
    
    if result["status"] == "success":
        if "available_embeddings" in result:
            print("✓ Available embeddings:")
            embeddings = result["available_embeddings"]
            
            if isinstance(embeddings, dict):
                for name, info in list(embeddings.items())[:3]:  # Show first 3
                    print(f"    - {name}")
            elif isinstance(embeddings, list):
                for name in embeddings[:3]:
                    print(f"    - {name}")
        else:
            print(f"✓ Embedding retrieved: {result.get('embedding_name')}")
            print(f"  Shape: {result.get('shape')}")
    else:
        print(f"✗ Error: {result['error']}")
    
    print()


def example_5_workflow_find_cell_types_in_lung():
    """Example 5: Complete workflow - Find cell types in lung tissue."""
    print("=" * 70)
    print("Example 5: Workflow - Cell Types in Lung Tissue")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Step 1: Query lung cells
    print("Step 1: Querying lung cells...")
    cells_result = tu.tools.CELLxGENE_get_cell_metadata(**{
        "operation": "get_obs_metadata",
        "organism": "Homo sapiens",
        "obs_value_filter": "tissue == 'lung' and disease == 'normal'",
        "column_names": ["cell_type", "tissue", "disease", "assay"],
        "census_version": "stable"
    })
    
    if cells_result["status"] == "success":
        print(f"✓ Found {cells_result['num_cells']} lung cells")
        
        # Count unique cell types
        if "data" in cells_result:
            cell_types = set()
            for cell in cells_result["data"]:
                if "cell_type" in cell:
                    cell_types.add(cell["cell_type"])
            
            print(f"\nStep 2: Identified {len(cell_types)} unique cell types")
            print("  Sample cell types:")
            for ct in list(cell_types)[:5]:
                print(f"    - {ct}")
    else:
        print(f"✗ Error in Step 1: {cells_result['error']}")
    
    # Step 2: Get gene expression for lung-specific markers
    print("\nStep 3: Querying lung marker genes...")
    lung_markers = ["SFTPC", "SCGB1A1", "FOXJ1"]  # Lung cell type markers
    
    genes_result = tu.tools.CELLxGENE_get_gene_metadata(**{
        "operation": "get_var_metadata",
        "organism": "Homo sapiens",
        "var_value_filter": f"feature_name in {lung_markers}",
        "census_version": "stable"
    })
    
    if genes_result["status"] == "success":
        print(f"✓ Found {genes_result['num_genes']} marker genes")
        
        if "data" in genes_result:
            print("  Marker genes:")
            for gene in genes_result["data"]:
                print(f"    - {gene.get('feature_name')}")
    else:
        print(f"✗ Error in Step 3: {genes_result['error']}")
    
    print()


def example_6_error_handling():
    """Example 6: Proper error handling."""
    print("=" * 70)
    print("Example 6: Error Handling")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Intentionally use invalid filter to demonstrate error handling
    result = tu.tools.CELLxGENE_get_cell_metadata(**{
        "operation": "get_obs_metadata",
        "organism": "Homo sapiens",
        "obs_value_filter": "invalid_field == 'value'",  # Invalid field
        "census_version": "stable"
    })
    
    if result["status"] == "error":
        print("✓ Error handled correctly:")
        print(f"  Error message: {result['error']}")
        
        if "detail" in result:
            print(f"  Details: {result['detail']}")
    else:
        print("✗ Expected an error but got success")
    
    print()


def example_7_download_dataset():
    """Example 7: Get H5AD download information."""
    print("=" * 70)
    print("Example 7: Get H5AD Download Information")
    print("=" * 70)
    
    tu = ToolUniverse()
    
    # Get URI for a dataset (example dataset ID)
    result = tu.tools.CELLxGENE_download_h5ad(**{
        "operation": "download_h5ad",
        "dataset_id": "example_dataset_id",
        "census_version": "stable"
    })
    
    if result["status"] == "success":
        print("✓ Download information retrieved:")
        print(f"  URI: {result.get('uri', 'N/A')}")
        print(f"  Message: {result.get('message', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")
        print("  (This is expected with example_dataset_id)")
    
    print()


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("CELLxGENE Census Tools - Usage Examples")
    print("=" * 70 + "\n")
    
    # Check if package is installed
    has_package = check_package_installed()
    
    # Run examples
    example_1_get_available_versions()
    
    if has_package:
        example_2_query_brain_cells()
        example_3_find_cancer_marker_genes()
        example_4_access_embeddings()
        example_5_workflow_find_cell_types_in_lung()
    else:
        print("Skipping examples 2-5 (require cellxgene-census package)\n")
    
    example_6_error_handling()
    example_7_download_dataset()
    
    print("=" * 70)
    print("Examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
