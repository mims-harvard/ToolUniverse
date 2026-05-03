"""
Examples for using GPCRdb tools in ToolUniverse.

GPCRdb is a comprehensive database for G protein-coupled receptors,
which are targets of ~35% of all approved drugs.

No authentication required.
"""

from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("GPCRdb (GPCR Database) Examples")
    print("=" * 60)

    # Example 1: Get beta-2 adrenergic receptor info
    print("\n1. Get ADRB2 (beta-2 adrenergic receptor) info:")
    print("-" * 40)
    result = tu.tools.GPCRdb_get_protein(operation="get_protein", protein="adrb2_human")

    if result["status"] == "success":
        data = result["data"]
        print(f"Entry: {data.get('entry_name', 'N/A')}")
        print(f"Name: {data.get('name', 'N/A')}")
        print(f"Family: {data.get('family', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Get structures
    print("\n2. Get ADRB2 crystal structures:")
    print("-" * 40)
    result = tu.tools.GPCRdb_get_structures(operation="get_structures", protein="adrb2_human")

    if result["status"] == "success":
        print(f"Structures found: {result['data']['count']}")
        for struct in result["data"]["structures"][:3]:
            print(f"  - PDB: {struct.get('pdb_code', 'N/A')}, State: {struct.get('state', 'N/A')}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Get ligands
    print("\n3. Get ADRB2 ligands:")
    print("-" * 40)
    result = tu.tools.GPCRdb_get_ligands(operation="get_ligands", protein="adrb2_human")

    if result["status"] == "success":
        print(f"Ligands found: {result['data']['count']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
