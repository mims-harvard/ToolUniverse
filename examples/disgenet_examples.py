"""
Examples for using DisGeNET tools in ToolUniverse.

DisGeNET is one of the largest databases of gene-disease and
variant-disease associations.

Requires registration: https://www.disgenet.org/
Set DISGENET_API_KEY environment variable.
"""

from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("DisGeNET (Gene-Disease Associations) Examples")
    print("=" * 60)

    # Example 1: Search for diseases associated with BRCA1
    print("\n1. Search diseases for BRCA1:")
    print("-" * 40)
    result = tu.tools.DisGeNET_search_gene(
        operation="search_gene",
        gene="BRCA1",
        limit=10
    )

    if result["status"] == "success":
        print(f"Gene: {result['data']['gene']}")
        print(f"Associations: {result['data']['count']}")
        for assoc in result["data"]["associations"][:5]:
            disease = assoc.get("disease_name", assoc.get("diseaseName", "N/A"))
            score = assoc.get("score", assoc.get("gda_score", "N/A"))
            print(f"  - {disease}: score={score}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Search for genes associated with breast cancer
    print("\n2. Search genes for breast cancer (C0006142):")
    print("-" * 40)
    result = tu.tools.DisGeNET_search_disease(
        operation="search_disease",
        disease="C0006142",
        limit=10
    )

    if result["status"] == "success":
        print(f"Disease: {result['data']['disease']}")
        for assoc in result["data"]["associations"][:5]:
            gene = assoc.get("gene_symbol", assoc.get("geneSymbol", "N/A"))
            score = assoc.get("score", "N/A")
            print(f"  - {gene}: score={score}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Get high-confidence associations
    print("\n3. Get high-confidence TP53 associations (score > 0.3):")
    print("-" * 40)
    result = tu.tools.DisGeNET_get_gda(
        operation="get_gda",
        gene="TP53",
        min_score=0.3,
        limit=15
    )

    if result["status"] == "success":
        print(f"High-confidence associations: {result['data']['count']}")
        for assoc in result["data"]["associations"][:5]:
            disease = assoc.get("disease_name", assoc.get("diseaseName", "N/A"))
            print(f"  - {disease}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
