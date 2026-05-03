"""
Example usage of MetaCyc metabolic pathway tools.

MetaCyc is a curated database of experimentally elucidated metabolic
pathways from all domains of life.

No authentication required for basic access.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("MetaCyc Metabolic Pathway Tools Examples")
    print("=" * 60)

    # Example 1: Search for pathways
    print("\n1. Search for glycolysis pathways")
    result = tu.run_tool(
        "MetaCyc_search_pathways",
        {"operation": "search_pathways", "query": "glycolysis"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Query: {data.get('query')}")
        if data.get("search_url"):
            print(f"   Search URL: {data.get('search_url')}")
        if data.get("results"):
            print(f"   Results: {len(data.get('results', []))}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 2: Get pathway details
    print("\n2. Get glycolysis pathway details")
    result = tu.run_tool(
        "MetaCyc_get_pathway",
        {"operation": "get_pathway", "pathway_id": "GLYCOLYSIS"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Pathway ID: {data.get('pathway_id')}")
        print(f"   Pathway URL: {data.get('url')}")
        print(f"   Diagram URL: {data.get('diagram_url')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 3: Get compound details
    print("\n3. Get pyruvate compound details")
    result = tu.run_tool(
        "MetaCyc_get_compound",
        {"operation": "get_compound", "compound_id": "PYRUVATE"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Compound ID: {data.get('compound_id')}")
        print(f"   Compound URL: {data.get('url')}")
    else:
        print(f"   Error: {result.get('error')}")

    # Example 4: Get reaction details
    print("\n4. Get pyruvate kinase reaction")
    result = tu.run_tool(
        "MetaCyc_get_reaction",
        {"operation": "get_reaction", "reaction_id": "PEPDEPHOS-RXN"},
    )
    if result.get("status") == "success":
        data = result["data"]
        print(f"   Reaction ID: {data.get('reaction_id')}")
        print(f"   Reaction URL: {data.get('url')}")
    else:
        print(f"   Error: {result.get('error')}")


if __name__ == "__main__":
    main()
