"""
Example usage of ZINC compound library tools.

ZINC is a free database of commercially available compounds for
virtual screening, containing 750M+ purchasable molecules.

No authentication required.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("ZINC Virtual Screening Library Tools Examples")
    print("=" * 60)

    # Example 1: Get compound by ZINC ID
    print("\n1. Get compound by ZINC ID")
    result = tu.run_tool(
        "ZINC_get_substance",
        {"operation": "get_substance", "zinc_id": "ZINC000000000001"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   ZINC ID: {data.get('zinc_id')}")
        print(f"   SMILES: {data.get('smiles')}")
        print(f"   MW: {data.get('mwt')}")
        print(f"   LogP: {data.get('logp')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 2: Search by compound name
    print("\n2. Search for aspirin")
    result = tu.run_tool(
        "ZINC_search_by_name",
        {"operation": "search_by_name", "name": "aspirin", "max_results": 10},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query: {data.get('query')}")
        print(f"   Results: {data.get('count', 0)}")
        print(f"   Search URL: {data.get('search_url')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 3: Search by SMILES (similarity search)
    print("\n3. Find similar compounds to aspirin")
    aspirin_smiles = "CC(=O)Oc1ccccc1C(=O)O"
    result = tu.run_tool(
        "ZINC_search_by_smiles",
        {
            "operation": "search_by_smiles",
            "smiles": aspirin_smiles,
            "search_type": "similarity",
            "max_results": 10,
        },
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query SMILES: {data.get('query_smiles')}")
        print(f"   Search type: {data.get('search_type')}")
        print(f"   Results: {data.get('count', 0)}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 4: Get available catalogs
    print("\n4. Get available ZINC catalogs")
    result = tu.run_tool(
        "ZINC_get_catalogs",
        {"operation": "get_catalogs"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Available catalogs: {data.get('count', len(data.get('catalogs', [])))}")
        for cat in data.get("catalogs", [])[:5]:
            if isinstance(cat, dict):
                print(f"   - {cat.get('name', cat)}: {cat.get('description', '')}")
            else:
                print(f"   - {cat}")
    else:
        print(f"   Error: {result.get('error')}")


if __name__ == "__main__":
    main()
