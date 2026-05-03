"""
Examples for using OMIM tools in ToolUniverse.

OMIM (Online Mendelian Inheritance in Man) is a comprehensive database
of human genes and genetic disorders.

API access requires registration: https://omim.org/api
Set OMIM_API_KEY environment variable.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("OMIM (Mendelian Disease Database) Examples")
    print("=" * 60)

    # Example 1: Search for BRCA1
    print("\n1. Search for BRCA1 gene:")
    print("-" * 40)
    result = tu.tools.OMIM_search(
        operation="search",
        query="BRCA1",
        limit=5
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Total results: {data['total_results']}")
        for entry in data.get("entries", [])[:3]:
            e = entry.get("entry", {})
            print(f"  - MIM {e.get('mimNumber')}: {e.get('titles', {}).get('preferredTitle', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Search for cystic fibrosis
    print("\n2. Search for cystic fibrosis:")
    print("-" * 40)
    result = tu.tools.OMIM_search(
        operation="search",
        query="cystic fibrosis",
        limit=5
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Total results: {data['total_results']}")
        for entry in data.get("entries", [])[:3]:
            e = entry.get("entry", {})
            print(f"  - MIM {e.get('mimNumber')}: {e.get('titles', {}).get('preferredTitle', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Get BRAF gene entry
    print("\n3. Get BRAF gene entry (MIM 164730):")
    print("-" * 40)
    result = tu.tools.OMIM_get_entry(
        operation="get_entry",
        mim_number="164730"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"MIM Number: {data.get('mimNumber')}")
        titles = data.get("titles", {})
        print(f"Title: {titles.get('preferredTitle', 'N/A')}")
        print(f"Alternative titles: {titles.get('alternativeTitles', 'N/A')[:50]}...")
    else:
        print(f"Error: {result['error']}")

    # Example 4: Get gene map
    print("\n4. Get gene-disease map for CFTR:")
    print("-" * 40)
    result = tu.tools.OMIM_get_gene_map(
        operation="get_gene_map",
        mim_number="602421"  # CFTR gene
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"Gene maps found: {data['count']}")
        for gm in data.get("gene_maps", [])[:2]:
            gene_map = gm.get("geneMap", {})
            print(f"  - Gene: {gene_map.get('geneSymbols', 'N/A')}")
            print(f"    Location: {gene_map.get('chromosomeSymbol', '')}:{gene_map.get('location', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 5: Get clinical synopsis for cystic fibrosis
    print("\n5. Get clinical synopsis for cystic fibrosis (MIM 219700):")
    print("-" * 40)
    result = tu.tools.OMIM_get_clinical_synopsis(
        operation="get_clinical_synopsis",
        mim_number="219700"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"MIM: {data.get('mimNumber')}")
        if "inheritance" in data:
            print(f"Inheritance: {data.get('inheritance')}")
        # Print a few clinical features
        if "respiratory" in data:
            print(f"Respiratory features: {data['respiratory'][:2]}...")
        if "digestive" in data:
            print(f"Digestive features: {data['digestive'][:2]}...")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
