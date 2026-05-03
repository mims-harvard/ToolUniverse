"""
Example usage of Enamine compound supplier tools.

Enamine is a leading supplier of make-on-demand compounds, building
blocks, and screening libraries for drug discovery.

No authentication required for basic search functionality.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("Enamine Compound Supplier Tools Examples")
    print("=" * 60)

    # Example 1: Search catalog
    print("\n1. Search Enamine catalog for pyridine")
    result = tu.run_tool(
        "Enamine_search_catalog",
        {"operation": "search_catalog", "query": "pyridine"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query: {data.get('query')}")
        print(f"   Catalog: {data.get('catalog')}")
        if data.get("search_url"):
            print(f"   Search URL: {data.get('search_url')}")
        if data.get("results"):
            print(f"   Results: {data.get('count', len(data['results']))}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 2: Get compound by ID
    print("\n2. Get compound by Enamine ID")
    result = tu.run_tool(
        "Enamine_get_compound",
        {"operation": "get_compound", "enamine_id": "EN300-123456"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Enamine ID: {data.get('enamine_id')}")
        if data.get("url"):
            print(f"   URL: {data.get('url')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 3: Search by SMILES
    print("\n3. Search for compounds similar to benzene")
    result = tu.run_tool(
        "Enamine_search_smiles",
        {
            "operation": "search_smiles",
            "smiles": "c1ccccc1",
            "search_type": "substructure",
        },
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query SMILES: {data.get('query_smiles')}")
        print(f"   Search type: {data.get('search_type')}")
        if data.get("search_url"):
            print(f"   Search URL: {data.get('search_url')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 4: Get available libraries
    print("\n4. Get available Enamine libraries")
    result = tu.run_tool(
        "Enamine_get_libraries",
        {"operation": "get_libraries"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print("   Available libraries:")
        for lib in data.get("libraries", []):
            print(f"   - {lib.get('name')}: {lib.get('description')}")
    else:
        print(f"   Error: {result.get('error')}")


if __name__ == "__main__":
    main()
