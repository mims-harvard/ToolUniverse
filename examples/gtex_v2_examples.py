"""
GTEx Portal API V2 Usage Examples

Demonstrates how to use GTEx V2 tools for tissue-specific gene expression
and eQTL analysis. Based on Adult GTEx V11 (January 2026).
"""

from tooluniverse import ToolUniverse


def example_1_basic_expression():
    """Example 1: Get median expression of TP53 across tissues."""
    print("=" * 70)
    print("Example 1: Get median expression of TP53 (tumor suppressor) across tissues")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Get median expression for TP53 (ENSG00000141510.16)
    result = tu.tools.GTEx_get_median_gene_expression(**{
        "operation": "get_median_gene_expression",
        "gencode_id": "ENSG00000141510.16",  # TP53
        "items_per_page": 10  # Get first 10 tissues
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found expression data in {result['num_results']} tissues")
        print("\nTP53 Expression (TPM) in selected tissues:")
        for expr in result["data"][:5]:
            print(f"  • {expr['tissueSiteDetailId']:<40} {expr['median']:.2f} TPM")
    else:
        print(f"✗ Error: {result['error']}")


def example_2_tissue_discovery():
    """Example 2: Discover available tissues and their sample sizes."""
    print("\n" + "=" * 70)
    print("Example 2: Discover available GTEx tissues and sample sizes")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_tissue_sites(**{
        "operation": "get_tissue_sites",
        "items_per_page": 10
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_tissues']} tissue sites")
        print("\nTissue Details:")
        for tissue in result["data"][:5]:
            rna_summary = tissue.get("rnaSeqSampleSummary", {})
            total = rna_summary.get("totalCount", 0)
            egene_count = tissue.get("eGeneCount", 0)
            print(f"  • {tissue['tissueSiteDetail']}")
            print(f"    ID: {tissue['tissueSiteDetailId']}")
            print(f"    Samples: {total}, eGenes: {egene_count}")
    else:
        print(f"✗ Error: {result['error']}")


def example_3_eqtl_discovery():
    """Example 3: Find eQTL genes in Whole Blood."""
    print("\n" + "=" * 70)
    print("Example 3: Find genes with significant eQTLs in Whole Blood")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_eqtl_genes(**{
        "operation": "get_eqtl_genes",
        "tissue_site_detail_id": ["Whole_Blood"],
        "items_per_page": 10
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_egenes']} eGenes in Whole Blood")
        print("\nTop eGenes (genes with significant eQTLs):")
        for egene in result["data"][:5]:
            print(f"  • {egene['geneSymbol']} ({egene['gencodeId']})")
            print(f"    p-value: {egene['pValue']:.2e}, q-value: {egene['qValue']:.3f}")
            print(f"    Allelic fold change: {egene['log2AllelicFoldChange']:.3f}")
    else:
        print(f"✗ Error: {result['error']}")


def example_4_single_tissue_eqtls():
    """Example 4: Get specific eQTLs for TP53 in blood."""
    print("\n" + "=" * 70)
    print("Example 4: Find TP53 eQTLs in Whole Blood")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_single_tissue_eqtls(**{
        "operation": "get_single_tissue_eqtls",
        "gencode_id": ["ENSG00000141510.16"],  # TP53
        "tissue_site_detail_id": ["Whole_Blood"],
        "items_per_page": 5
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_eqtls']} eQTLs for TP53")
        print("\nTop eQTL associations:")
        for eqtl in result["data"][:3]:
            print(f"  • Variant: {eqtl.get('snpId', eqtl['variantId'])}")
            print(f"    Position: {eqtl['chromosome']}:{eqtl['pos']}")
            print(f"    p-value: {eqtl['pValue']:.2e}, NES: {eqtl['nes']:.3f}")
    else:
        print(f"✗ Error: {result['error']}")


def example_5_top_expressed():
    """Example 5: Get top expressed genes in liver."""
    print("\n" + "=" * 70)
    print("Example 5: Top expressed genes in Liver tissue")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_top_expressed_genes(**{
        "operation": "get_top_expressed_genes",
        "tissue_site_detail_id": "Liver",
        "filter_mt_genes": True,  # Exclude mitochondrial genes
        "items_per_page": 10
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_genes']} highly expressed genes")
        print("\nTop 5 expressed genes in Liver:")
        for i, gene in enumerate(result["data"][:5], 1):
            print(f"  {i}. {gene['geneSymbol']:<15} {gene['median']:.1f} TPM")
    else:
        print(f"✗ Error: {result['error']}")


def example_6_compare_tissues():
    """Example 6: Compare TP53 expression across specific tissues."""
    print("\n" + "=" * 70)
    print("Example 6: Compare TP53 expression in Brain vs Liver vs Blood")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    tissues = ["Brain_Cortex", "Liver", "Whole_Blood"]
    
    result = tu.tools.GTEx_get_median_gene_expression(**{
        "operation": "get_median_gene_expression",
        "gencode_id": "ENSG00000141510.16",  # TP53
        "tissue_site_detail_id": tissues
    })
    
    if result["status"] == "success":
        print(f"\n✓ Retrieved expression data")
        print("\nTP53 Expression Comparison:")
        for expr in result["data"]:
            tissue = expr['tissueSiteDetailId']
            tpm = expr['median']
            print(f"  • {tissue:<20} {tpm:>8.2f} TPM")
    else:
        print(f"✗ Error: {result['error']}")


def example_7_dataset_info():
    """Example 7: Get GTEx dataset information."""
    print("\n" + "=" * 70)
    print("Example 7: Get GTEx dataset metadata")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_dataset_info(**{
        "operation": "get_dataset_info"
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_datasets']} dataset(s)")
        for dataset in result["datasets"][:2]:
            print(f"\nDataset: {dataset.get('displayName', dataset['datasetId'])}")
            print(f"  ID: {dataset['datasetId']}")
            print(f"  Genome: {dataset.get('genomeBuild', 'N/A')}")
            print(f"  GENCODE: {dataset.get('gencodeVersion', 'N/A')}")
            print(f"  Subjects: {dataset.get('subjectCount', 'N/A')}")
            print(f"  Tissues: {dataset.get('tissueCount', 'N/A')}")
            print(f"  RNA-seq samples: {dataset.get('rnaSeqSampleCount', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")


def example_8_sample_metadata():
    """Example 8: Get sample metadata with demographic filters."""
    print("\n" + "=" * 70)
    print("Example 8: Get female samples from Liver tissue")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_sample_info(**{
        "operation": "get_sample_info",
        "tissue_site_detail_id": ["Liver"],
        "sex": "female",
        "age_bracket": ["50-59", "60-69"],
        "items_per_page": 5
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_samples']} matching samples")
        print("\nSample Details:")
        for sample in result["data"][:3]:
            print(f"  • Sample: {sample.get('sampleId', 'N/A')}")
            print(f"    Subject: {sample.get('subjectId', 'N/A')}")
            print(f"    Age: {sample.get('ageBracket', 'N/A')}, Sex: {sample.get('sex', 'N/A')}")
            print(f"    RIN: {sample.get('rin', 'N/A')}")
    else:
        print(f"✗ Error: {result['error']}")


def example_9_multi_tissue_eqtl():
    """Example 9: Get multi-tissue eQTL meta-analysis."""
    print("\n" + "=" * 70)
    print("Example 9: Multi-tissue eQTL analysis for TP53")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    result = tu.tools.GTEx_get_multi_tissue_eqtls(**{
        "operation": "get_multi_tissue_eqtls",
        "gencode_id": "ENSG00000141510.16",  # TP53
        "items_per_page": 3
    })
    
    if result["status"] == "success":
        print(f"\n✓ Found {result['num_results']} multi-tissue eQTL result(s)")
        if result["data"]:
            for i, eqtl in enumerate(result["data"][:1], 1):
                print(f"\neQTL #{i}:")
                print(f"  Variant: {eqtl['variantId']}")
                print(f"  Meta p-value: {eqtl.get('metaP', 'N/A')}")
                print(f"  Tissue effects:")
                tissues = eqtl.get("tissues", {})
                for tissue_name, tissue_data in list(tissues.items())[:5]:
                    m_val = tissue_data.get('mValue', 0)
                    nes = tissue_data.get('nes', 0)
                    print(f"    • {tissue_name}: m-value={m_val:.3f}, NES={nes:.3f}")
    else:
        print(f"✗ Error: {result['error']}")


def example_10_workflow():
    """Example 10: Complete workflow - Gene discovery to eQTL analysis."""
    print("\n" + "=" * 70)
    print("Example 10: Complete Workflow - From gene discovery to eQTL")
    print("=" * 70)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    tissue = "Liver"
    
    # Step 1: Find top expressed genes in liver
    print(f"\nStep 1: Finding top expressed genes in {tissue}...")
    top_genes = tu.tools.GTEx_get_top_expressed_genes(**{
        "operation": "get_top_expressed_genes",
        "tissue_site_detail_id": tissue,
        "items_per_page": 5
    })
    
    if top_genes["status"] == "success" and top_genes["data"]:
        gene = top_genes["data"][0]
        gene_id = gene["gencodeId"]
        gene_symbol = gene["geneSymbol"]
        print(f"  ✓ Top gene: {gene_symbol} ({gene['median']:.1f} TPM)")
        
        # Step 2: Check if it's an eGene
        print(f"\nStep 2: Checking if {gene_symbol} has eQTLs in {tissue}...")
        egenes = tu.tools.GTEx_get_eqtl_genes(**{
            "operation": "get_eqtl_genes",
            "tissue_site_detail_id": [tissue],
            "items_per_page": 100
        })
        
        if egenes["status"] == "success":
            is_egene = any(g["gencodeId"] == gene_id for g in egenes["data"])
            if is_egene:
                print(f"  ✓ {gene_symbol} is an eGene!")
                
                # Step 3: Get its eQTLs
                print(f"\nStep 3: Retrieving eQTLs for {gene_symbol}...")
                eqtls = tu.tools.GTEx_get_single_tissue_eqtls(**{
                    "operation": "get_single_tissue_eqtls",
                    "gencode_id": [gene_id],
                    "tissue_site_detail_id": [tissue],
                    "items_per_page": 3
                })
                
                if eqtls["status"] == "success" and eqtls["data"]:
                    print(f"  ✓ Found {eqtls['num_eqtls']} eQTL(s)")
                    for eqtl in eqtls["data"][:2]:
                        print(f"    • {eqtl.get('snpId', 'N/A')}: p={eqtl['pValue']:.2e}")
            else:
                print(f"  • {gene_symbol} is not an eGene in {tissue}")
    else:
        print(f"  ✗ Error: {top_genes.get('error', 'Unknown error')}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("GTEx Portal API V2 Usage Examples")
    print("Adult GTEx V11 (January 2026) - 54 tissues, ~1,000 donors")
    print("=" * 70)
    
    try:
        example_1_basic_expression()
        example_2_tissue_discovery()
        example_3_eqtl_discovery()
        example_4_single_tissue_eqtls()
        example_5_top_expressed()
        example_6_compare_tissues()
        example_7_dataset_info()
        example_8_sample_metadata()
        example_9_multi_tissue_eqtl()
        example_10_workflow()
        
        print("\n" + "=" * 70)
        print("All examples completed!")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error running examples: {e}")
        import traceback
        traceback.print_exc()
