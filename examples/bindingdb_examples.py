"""
Examples for using BindingDB tools in ToolUniverse.

BindingDB is a public database of measured binding affinities
containing 3.2M measurements for 1.4M compounds and 11.4K targets.

No authentication required.
"""

from tooluniverse import ToolUniverse


def main():
    tu = ToolUniverse()
    tu.load_tools()

    print("=" * 60)
    print("BindingDB (Protein-Ligand Binding) Examples")
    print("=" * 60)

    # Example 1: Get ligands for EGFR by UniProt
    print("\n1. Get EGFR ligands (P00533) with IC50 < 1000 nM:")
    print("-" * 40)
    result = tu.tools.BindingDB_get_by_uniprot(
        operation="get_by_uniprot",
        uniprot_id="P00533",
        affinity_cutoff=1000
    )

    if result["status"] == "success":
        print(f"UniProt: {result['data']['uniprot_id']}")
        print(f"Ligands found: {result['data']['count']}")
        for lig in result["data"]["ligands"][:3]:
            print(f"  - ID: {lig.get('monomerid', 'N/A')}, SMILES: {lig.get('smiles', 'N/A')[:30]}...")
    else:
        print(f"Error: {result['error']}")

    # Example 2: Get ligands by PDB structure
    print("\n2. Get ligands for PDB 1M17 (EGFR structure):")
    print("-" * 40)
    result = tu.tools.BindingDB_get_by_pdb(
        operation="get_by_pdb",
        pdb_ids="1M17",
        affinity_cutoff=100
    )

    if result["status"] == "success":
        print(f"PDB IDs: {result['data']['pdb_ids']}")
        print(f"Ligands found: {result['data']['count']}")
    else:
        print(f"Error: {result['error']}")

    # Example 3: Search by target name
    print("\n3. Search for COX-2 inhibitors:")
    print("-" * 40)
    result = tu.tools.BindingDB_get_by_target_name(
        operation="get_by_target_name",
        target_name="COX-2",
        affinity_cutoff=100
    )

    if result["status"] == "success":
        print(f"Target: {result['data']['target_name']}")
        print(f"Ligands found: {result['data']['count']}")
    else:
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    main()
