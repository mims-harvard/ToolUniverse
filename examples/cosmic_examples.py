"""
Examples for using COSMIC tools in ToolUniverse.

COSMIC (Catalogue of Somatic Mutations in Cancer) is the world's largest
expert-curated database of somatic mutations in human cancer.

This tool uses the NLM Clinical Tables Search Service API which provides
free access to COSMIC mutation data.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("COSMIC (Somatic Mutations in Cancer) Examples")
    print("=" * 60)

    # Example 1: Search for BRAF V600E mutations
    print("\n1. Search for BRAF V600E mutations:")
    print("-" * 40)
    result = tu.tools.COSMIC_search_mutations(
        operation="search", terms="BRAF V600E", max_results=10
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Total mutations found: {data['total_count']}")
        print(f"Genome build: {data['genome_build']}")
        for mut in data["results"][:5]:
            print(f"  - {mut['mutation_id']}: {mut.get('display', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Get all mutations for TP53
    print("\n2. Get mutations for TP53 (tumor suppressor):")
    print("-" * 40)
    result = tu.tools.COSMIC_get_mutations_by_gene(
        operation="get_by_gene", gene="TP53", max_results=20
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Gene: {data['gene']}")
        print(f"Total mutations: {data['total_count']}")
        for mut in data["results"][:5]:
            aa_change = mut.get("MutationAA", "N/A")
            cds_change = mut.get("MutationCDS", "N/A")
            print(f"  - {mut['mutation_id']}: {aa_change} ({cds_change})")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Search for EGFR mutations (lung cancer relevance)
    print("\n3. Search for EGFR mutations:")
    print("-" * 40)
    result = tu.tools.COSMIC_get_mutations_by_gene(
        operation="get_by_gene", gene="EGFR", max_results=15
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Total EGFR mutations: {data['total_count']}")
        for mut in data["results"][:5]:
            site = mut.get("PrimarySite", "N/A")
            histology = mut.get("PrimaryHistology", "N/A")
            print(f"  - {mut['mutation_id']}: Site={site}, Histology={histology}")
    else:
        print(f"Error: {result['error']}")

    # Example 4: Search with GRCh38 coordinates
    print("\n4. Search using GRCh38 genome build:")
    print("-" * 40)
    result = tu.tools.COSMIC_search_mutations(
        operation="search", terms="KRAS G12", max_results=10, genome_build=38
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Results using {data['genome_build']}:")
        print(f"Total: {data['total_count']} mutations")
        for mut in data["results"][:3]:
            print(f"  - {mut['mutation_id']}: {mut.get('display', 'N/A')}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
