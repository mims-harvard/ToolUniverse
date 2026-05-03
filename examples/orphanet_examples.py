"""
Examples for using Orphanet tools in ToolUniverse.

Orphanet is the reference portal for rare diseases and orphan drugs,
providing nomenclature, classification, and epidemiological data.

No authentication required - free public access.
"""

from tooluniverse import ToolUniverse


def main():
    # Initialize ToolUniverse
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("Orphanet (Rare Disease Database) Examples")
    print("=" * 60)

    # Example 1: Search for Marfan syndrome
    print("\n1. Search for Marfan syndrome:")
    print("-" * 40)
    result = tu.tools.Orphanet_search_diseases(
        operation="search_diseases",
        query="Marfan syndrome"
    )

    if result["status"] == "success":
        results = result["data"]["results"]
        print(f"Found {len(results)} matching diseases")
        for disease in results[:3]:
            orpha = disease.get("ORPHAcode", "N/A")
            name = disease.get("Preferred term", disease.get("name", "N/A"))
            print(f"  - ORPHA:{orpha}: {name}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Get disease details by ORPHA code
    print("\n2. Get Marfan syndrome details (ORPHA:558):")
    print("-" * 40)
    result = tu.tools.Orphanet_get_disease(
        operation="get_disease",
        orpha_code="558"
    )

    if result["status"] == "success":
        data = result["data"]
        print(f"ORPHA code: {data.get('ORPHAcode', 'N/A')}")
        print(f"Name: {data.get('Preferred term', 'N/A')}")
        definition = data.get("Definition", "N/A")
        if definition and len(definition) > 100:
            definition = definition[:100] + "..."
        print(f"Definition: {definition}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Get genes associated with a disease
    print("\n3. Get genes for Marfan syndrome:")
    print("-" * 40)
    result = tu.tools.Orphanet_get_genes(
        operation="get_genes",
        orpha_code="558"
    )

    if result["status"] == "success":
        genes = result["data"]["genes"]
        print(f"Associated genes: {len(genes)}")
        for gene in genes[:5]:
            symbol = gene.get("Symbol", gene.get("symbol", "N/A"))
            name = gene.get("Name", gene.get("name", "N/A"))
            assoc = gene.get("AssociationType", gene.get("associationType", "N/A"))
            print(f"  - {symbol}: {name} ({assoc})")
    else:
        print(f"Error: {result['error']}")

    # Example 4: Search for muscular dystrophy
    print("\n4. Search for muscular dystrophy:")
    print("-" * 40)
    result = tu.tools.Orphanet_search_diseases(
        operation="search_diseases",
        query="muscular dystrophy"
    )

    if result["status"] == "success":
        results = result["data"]["results"]
        print(f"Found {len(results)} types of muscular dystrophy")
        for disease in results[:5]:
            orpha = disease.get("ORPHAcode", "N/A")
            name = disease.get("Preferred term", disease.get("name", "N/A"))
            print(f"  - ORPHA:{orpha}: {name}")
    else:
        print(f"Error: {result['error']}")

    # Example 5: Get disease classification
    print("\n5. Get classification for cystic fibrosis (ORPHA:586):")
    print("-" * 40)
    result = tu.tools.Orphanet_get_classification(
        operation="get_classification",
        orpha_code="586"
    )

    if result["status"] == "success":
        classification = result["data"]["classification"]
        print(f"ORPHA code: {result['data']['orpha_code']}")
        print(f"Classification hierarchy:")
        if isinstance(classification, dict):
            for key, value in list(classification.items())[:5]:
                print(f"  - {key}: {value}")
        elif isinstance(classification, list):
            for item in classification[:3]:
                print(f"  - {item}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
