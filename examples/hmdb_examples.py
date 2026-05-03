"""
Example usage of HMDB (Human Metabolome Database) tools.

HMDB is the most comprehensive database of human metabolites containing
chemical, clinical, and molecular biology data.

No authentication required for basic access.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("HMDB (Human Metabolome Database) Tools Examples")
    print("=" * 60)

    # Example 1: Get metabolite by HMDB ID
    print("\n1. Get metabolite by HMDB ID (1-Methylhistidine)")
    result = tu.run_tool(
        "HMDB_get_metabolite",
        {"operation": "get_metabolite", "hmdb_id": "HMDB0000001"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Name: {data.get('name')}")
        print(f"   Formula: {data.get('chemical_formula')}")
        print(f"   MW: {data.get('average_molecular_weight')}")
        print(f"   SMILES: {data.get('smiles')}")
        print(f"   Kingdom: {data.get('kingdom')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 2: Search for metabolites
    print("\n2. Search for glucose metabolites")
    result = tu.run_tool(
        "HMDB_search",
        {"operation": "search", "query": "glucose"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query: {data.get('query')}")
        print(f"   Results found: {data.get('count', 0)}")
        print(f"   Search URL: {data.get('search_url')}")
        if data.get("results"):
            for r in data["results"][:3]:
                if isinstance(r, dict):
                    print(f"   - {r.get('name', r)}")
                else:
                    print(f"   - {r}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 3: Get disease associations
    print("\n3. Get disease associations for phenylalanine (HMDB0000159)")
    result = tu.run_tool(
        "HMDB_get_diseases",
        {"operation": "get_diseases", "hmdb_id": "HMDB0000159"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Metabolite: {data.get('metabolite_name')}")
        print(f"   Diseases: {data.get('disease_count', 0)}")
        print(f"   Pathways: {data.get('pathway_count', 0)}")
        if data.get("diseases"):
            print("   Disease associations:")
            for d in data["diseases"][:5]:
                if isinstance(d, dict):
                    print(f"   - {d.get('name', d)}")
                else:
                    print(f"   - {d}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 4: Get lactate info (common metabolic biomarker)
    print("\n4. Get lactate information (HMDB0000190)")
    result = tu.run_tool(
        "HMDB_get_metabolite",
        {"operation": "get_metabolite", "hmdb_id": "HMDB0000190"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Name: {data.get('name')}")
        print(f"   Formula: {data.get('chemical_formula')}")
        print(f"   Class: {data.get('class', 'N/A')}")
        print(f"   Super class: {data.get('super_class', 'N/A')}")
    else:
        print(f"   Error: {result.get('error')}")


if __name__ == "__main__":
    main()
