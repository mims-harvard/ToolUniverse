"""
Example: How to Get IntAct Interaction IDs

This example demonstrates how to obtain IntAct interaction IDs
that can be used with intact_get_interaction_details and intact_get_interaction_network.
"""

from tooluniverse import ToolUniverse


def example_get_interaction_ids():
    """Example: Getting interaction IDs from IntAct queries"""
    print("="*80)
    print("EXAMPLE: Getting IntAct Interaction IDs")
    print("="*80)
    
    tu = ToolUniverse()
    tu.load_tools()
    
    # Method 1: Get interactions for a protein
    print("\n1. Get interactions for a protein (P04637 - p53):")
    print("-" * 80)
    result = tu.run_one_function({
        "name": "intact_get_interactions",
        "arguments": {
            "identifier": "P04637",
            "size": 5
        }
    })
    
    if result.get("status") == "success":
        interaction_ids = result.get("interaction_ids", [])
        print(f"✓ Found {len(interaction_ids)} interaction IDs")
        print(f"\nInteraction IDs:")
        for i, interaction_id in enumerate(interaction_ids[:5], 1):
            print(f"  {i}. {interaction_id}")
        
        # Now use one of these IDs to get details
        if interaction_ids:
            print(f"\n2. Get detailed information for first interaction:")
            print("-" * 80)
            detail_result = tu.run_one_function({
                "name": "intact_get_interaction_details",
                "arguments": {
                    "interaction_id": interaction_ids[0]
                }
            })
            
            if detail_result.get("status") == "success":
                print(f"✓ Successfully retrieved interaction details")
                print(f"  URL: {detail_result.get('url', 'N/A')}")
            else:
                print(f"⚠️  Note: {detail_result.get('error', 'Unknown error')}")
                print("  (Direct IntAct API may not be available, but IDs are still useful)")
    
    # Method 2: Search for interactions
    print("\n\n3. Search for interactions by gene name (BRCA1):")
    print("-" * 80)
    result = tu.run_one_function({
        "name": "intact_search_interactions",
        "arguments": {
            "query": "BRCA1",
            "max": 5
        }
    })
    
    if result.get("status") == "success":
        interaction_ids = result.get("interaction_ids", [])
        print(f"✓ Found {len(interaction_ids)} interaction IDs")
        print(f"\nInteraction IDs:")
        for i, interaction_id in enumerate(interaction_ids[:5], 1):
            print(f"  {i}. {interaction_id}")
    
    print("\n" + "="*80)
    print("SUMMARY: How to Get IntAct Interaction IDs")
    print("="*80)
    print("""
To get IntAct interaction IDs:

1. Use intact_get_interactions:
   - Provide a protein identifier (UniProt ID, gene name, etc.)
   - The response includes an 'interaction_ids' field
   - Each ID is in format 'EBI-XXXXXX-EBI-YYYYYY'

2. Use intact_search_interactions:
   - Provide a search query (protein name, gene name, etc.)
   - The response includes an 'interaction_ids' field
   - Extract IDs from the results

3. Use the IDs:
   - With intact_get_interaction_details: Provide the interaction_id
   - With intact_get_interaction_network: Can use interactor IDs or interaction IDs
   - Note: Direct IntAct API endpoints may have limitations, but the IDs
     are still useful for reference and can be used on the IntAct website

Example workflow:
  1. intact_get_interactions(identifier="P04637") → get interaction_ids
  2. intact_get_interaction_details(interaction_id="EBI-366083-EBI-366083")
    """)


if __name__ == "__main__":
    example_get_interaction_ids()
