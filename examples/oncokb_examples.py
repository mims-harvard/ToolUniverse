"""
Examples for using OncoKB tools in ToolUniverse.

OncoKB is a precision oncology knowledge base that provides information about
the effects and treatment implications of specific cancer gene alterations.

API access requires registration: https://www.oncokb.org/apiAccess
Set ONCOKB_API_TOKEN environment variable for full access.
Demo mode (limited to BRAF, TP53, ROS1) available without token.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("OncoKB (Precision Oncology Knowledge Base) Examples")
    print("=" * 60)

    # Example 1: Annotate BRAF V600E mutation
    print("\n1. Annotate BRAF V600E mutation:")
    print("-" * 40)
    result = tu.tools.OncoKB_annotate_variant(
        operation="annotate_variant",
        gene="BRAF",
        variant="V600E"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"API Mode: {result['metadata']['api_mode']}")
        print(f"Oncogenic: {data.get('oncogenic', 'N/A')}")
        if "mutationEffect" in data:
            print(f"Mutation Effect: {data['mutationEffect'].get('knownEffect', 'N/A')}")
        print(f"Highest Sensitive Level: {data.get('highestSensitiveLevel', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Annotate BRAF V600E in melanoma specifically
    print("\n2. Annotate BRAF V600E in melanoma (tumor-specific):")
    print("-" * 40)
    result = tu.tools.OncoKB_annotate_variant(
        operation="annotate_variant",
        gene="BRAF",
        variant="V600E",
        tumor_type="MEL"  # Melanoma OncoTree code
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Tumor Type: MEL (Melanoma)")
        print(f"Oncogenic: {data.get('oncogenic', 'N/A')}")
        print(f"Highest Level: {data.get('highestSensitiveLevel', 'N/A')}")
        if data.get("treatments"):
            print("Treatments:")
            for tx in data["treatments"][:3]:
                print(f"  - {tx.get('drugs', 'N/A')}: Level {tx.get('level', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Get gene-level information
    print("\n3. Get gene information for TP53:")
    print("-" * 40)
    result = tu.tools.OncoKB_get_gene_info(
        operation="get_gene_info",
        gene="TP53"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Gene: {data.get('hugoSymbol', 'N/A')}")
        print(f"Oncogene: {data.get('oncogene', False)}")
        print(f"Tumor Suppressor: {data.get('tsg', False)}")
    else:
        print(f"Error: {result['error']}")

    # Example 4: Get evidence level definitions
    print("\n4. Get OncoKB evidence levels:")
    print("-" * 40)
    result = tu.tools.OncoKB_get_levels(operation="get_levels")

    if result["status"] == "success":
        for level in result["data"][:5]:
            print(f"  {level.get('level', 'N/A')}: {level.get('description', 'N/A')[:60]}...")
    else:
        print(f"Error: {result['error']}")

    # Example 5: List cancer genes
    print("\n5. Get cancer genes from OncoKB:")
    print("-" * 40)
    result = tu.tools.OncoKB_get_cancer_genes(operation="get_cancer_genes")

    if result["status"] == "success":
        data = result["data"]
        print(f"Total genes in database: {data.get('total_genes', 0)}")
        print(f"Cancer-related genes: {data.get('cancer_genes_count', 0)}")
        if data.get("genes"):
            print("Sample oncogenes:")
            oncogenes = [g for g in data["genes"] if g.get("oncogene")][:5]
            for g in oncogenes:
                print(f"  - {g.get('hugoSymbol', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 6: Annotate copy number alteration
    print("\n6. Annotate ERBB2 amplification:")
    print("-" * 40)
    result = tu.tools.OncoKB_annotate_copy_number(
        operation="annotate_copy_number",
        gene="ERBB2",
        copy_number_type="AMPLIFICATION"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Gene: ERBB2")
        print(f"Alteration: Amplification")
        print(f"Oncogenic: {data.get('oncogenic', 'N/A')}")
        print(f"Highest Level: {data.get('highestSensitiveLevel', 'N/A')}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
