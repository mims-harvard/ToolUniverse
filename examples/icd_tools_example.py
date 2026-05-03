"""ICD-10/ICD-11 disease classification tools -- usage examples.

ICD-11 tools require ICD_CLIENT_ID / ICD_CLIENT_SECRET env vars (register at https://icd.who.int/icdapi).
ICD-10 tools require no authentication.
"""

from tooluniverse import ToolUniverse


def example_icd10_search():
    """Example: Search ICD-10-CM codes by disease name."""
    print("\n" + "=" * 80)
    print("Example 1: Search ICD-10-CM codes")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Search for diabetes codes
    result = tu.tools.ICD10_search_codes(
        query="diabetes mellitus type 2",
        limit=5
    )

    print("\nQuery: 'diabetes mellitus type 2'")
    print(f"\nTotal results: {result['data']['total']}")
    print("\nTop 5 codes:")
    for item in result['data']['results'][:5]:
        print(f"  {item['code']}: {item['name']}")


def example_icd10_code_lookup():
    """Example: Get details for a specific ICD-10-CM code."""
    print("\n" + "=" * 80)
    print("Example 2: Look up specific ICD-10-CM code")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Look up E11.9 (Type 2 diabetes without complications)
    result = tu.tools.ICD10_get_code_info(code="E11.9")

    print("\nCode: E11.9")
    if result['data']['results']:
        code_info = result['data']['results'][0]
        print(f"Name: {code_info['name']}")
        print(f"Code: {code_info['code']}")


def example_icd11_search():
    """Example: Search ICD-11 for diseases (requires authentication)."""
    print("\n" + "=" * 80)
    print("Example 3: Search ICD-11 diseases")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Search for hypertension
    result = tu.tools.ICD11_search_diseases(
        query="essential hypertension",
        linearization="mms",
        flatResults=True,
        language="en"
    )

    if 'error' in result:
        print(f"\nError: {result['error']}")
        print("\nNote: ICD-11 tools require authentication.")
        print("Register at: https://icd.who.int/icdapi")
        return

    print("\nQuery: 'essential hypertension'")
    print("\nResults:")
    for entity in result['data'].get('destinationEntities', [])[:5]:
        print(f"  Code: {entity.get('theCode', 'N/A')}")
        print(f"  Title: {entity.get('title', 'N/A')}")
        print(f"  Score: {entity.get('score', 'N/A')}")
        print()


def example_icd11_entity_details():
    """Example: Get detailed ICD-11 entity information."""
    print("\n" + "=" * 80)
    print("Example 4: Get ICD-11 entity details")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Get details for a specific entity (diabetes mellitus)
    result = tu.tools.ICD11_get_entity(
        entity_id="1435254666",
        linearization="mms",
        language="en"
    )

    if 'error' in result:
        print(f"\nError: {result['error']}")
        return

    print("\nEntity ID: 1435254666")
    data = result['data']
    print(f"Title: {data.get('title', {}).get('@value', 'N/A')}")
    print(f"Code: {data.get('code', 'N/A')}")
    print(f"Browser URL: {data.get('browserUrl', 'N/A')}")

    if 'definition' in data:
        definition = data['definition'].get('@value', 'N/A')
        print(f"\nDefinition: {definition[:200]}...")


def example_disease_research_workflow():
    """Example: Complete workflow for disease research."""
    print("\n" + "=" * 80)
    print("Example 5: Disease Research Workflow")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    disease = "hypertension"

    print(f"\nResearch Topic: {disease}")
    print("\n" + "-" * 40)

    # Step 1: Get ICD-10 code
    print("\n1. Finding ICD-10 code...")
    icd10 = tu.tools.ICD10_search_codes(query=disease, limit=1)
    if icd10['data']['results']:
        code = icd10['data']['results'][0]
        print(f"   ICD-10 Code: {code['code']}")
        print(f"   Description: {code['name']}")

    # Step 2: Get ICD-11 information (if authenticated)
    print("\n2. Searching ICD-11...")
    icd11 = tu.tools.ICD11_search_diseases(
        query=disease,
        flatResults=True,
        language="en"
    )

    if 'error' not in icd11:
        entities = icd11['data'].get('destinationEntities', [])
        if entities:
            print(f"   ICD-11 Code: {entities[0].get('theCode', 'N/A')}")
            print(f"   Title: {entities[0].get('title', 'N/A')}")

    # Step 3: Find related targets (using existing tools)
    print("\n3. Finding disease targets...")
    try:
        targets = tu.tools.OpenTargets_get_associated_targets_by_disease_name(
            disease_name=disease,
            limit=3
        )
        if 'data' in targets:
            print(f"   Found {len(targets['data'])} associated targets")
            for target in targets['data'][:3]:
                print(f"   - {target.get('approvedSymbol', 'N/A')}")
    except Exception as e:
        print(f"   (Optional) Could not fetch targets: {e}")

    # Step 4: Search literature
    print("\n4. Searching literature...")
    try:
        papers = tu.tools.PubMed_search_publications(
            query=f"{disease} [Title/Abstract]",
            retmax=3
        )
        if 'data' in papers:
            print(f"   Found {papers['data'].get('count', 0)} papers")
            for article in papers['data'].get('articles', [])[:3]:
                title = article.get('title', 'No title')[:60]
                print(f"   - {title}...")
    except Exception as e:
        print(f"   (Optional) Could not fetch papers: {e}")

    print("\n" + "-" * 40)
    print("Workflow complete!")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("ICD-10/ICD-11 Disease Classification Tools - Examples")
    print("=" * 80)

    # ICD-10 examples (no auth required)
    example_icd10_search()
    example_icd10_code_lookup()

    # ICD-11 examples (require auth)
    example_icd11_search()
    example_icd11_entity_details()

    # Integrated workflow
    example_disease_research_workflow()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
