"""
Example usage of eMolecules vendor aggregator tools.

eMolecules aggregates compounds from 200+ chemical suppliers,
providing pricing and availability information.

No authentication required for basic search functionality.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("eMolecules Vendor Aggregator Tools Examples")
    print("=" * 60)

    # Example 1: Search by name
    print("\n1. Search for caffeine")
    result = tu.run_tool(
        "eMolecules_search",
        {"operation": "search", "query": "caffeine"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query: {data.get('query')}")
        if data.get("search_url"):
            print(f"   Search URL: {data.get('search_url')}")
        if data.get("results"):
            print(f"   Results: {data.get('count', len(data['results']))}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 2: Search by SMILES (caffeine)
    print("\n2. Search by SMILES (caffeine)")
    caffeine_smiles = "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
    result = tu.run_tool(
        "eMolecules_search_smiles",
        {
            "operation": "search_smiles",
            "smiles": caffeine_smiles,
            "search_type": "exact",
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

    # Example 3: Get vendors for aspirin
    print("\n3. Get vendors for aspirin")
    aspirin_smiles = "CC(=O)Oc1ccccc1C(=O)O"
    result = tu.run_tool(
        "eMolecules_get_vendors",
        {"operation": "get_vendors", "smiles": aspirin_smiles},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query SMILES: {data.get('query_smiles')}")
        if data.get("vendor_count"):
            print(f"   Vendors found: {data.get('vendor_count')}")
        if data.get("note"):
            print(f"   Note: {data.get('note')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 4: Get compound by ID
    print("\n4. Get compound by eMolecules ID")
    result = tu.run_tool(
        "eMolecules_get_compound",
        {"operation": "get_compound", "emol_id": "12345678"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   eMolecules ID: {data.get('emol_id')}")
        if data.get("url"):
            print(f"   URL: {data.get('url')}")
    else:
        print(f"   Error: {result.get('error')}")


if __name__ == "__main__":
    main()
