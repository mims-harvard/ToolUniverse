"""Test script for SwissDock molecular docking tools.

WARNING: This script makes real API calls and docking can take 5-15 minutes.
"""

import json

from tooluniverse import ToolUniverse


def test_swissdock_tool_loading():
    """Test that SwissDock tools are properly loaded."""
    print("="*80)
    print("Testing SwissDock Tool Loading")
    print("="*80)

    tu = ToolUniverse(tool_files={})
    tu.load_tools()

    # Find SwissDock tools
    swissdock_tools = [t for t in tu.all_tools if 'SwissDock' in t.get('name', '')]

    print(f"\nFound {len(swissdock_tools)} SwissDock tools:")
    for tool in swissdock_tools:
        print(f"  - {tool['name']}")
        print(f"    Description: {tool['description'][:100]}...")
        print(f"    Required params: {tool['parameters'].get('required', [])}")
        print()

    return tu


def test_swissdock_dock_ligand_dry_run(tu):
    """
    Test SwissDock docking tool with a simple example (aspirin to COX-2).

    NOTE: This will make real API calls. Docking can take 5-15 minutes.
    Set dry_run=True to skip actual execution.
    """
    print("="*80)
    print("Testing SwissDock Molecular Docking")
    print("="*80)

    # Example: Dock aspirin (acetylsalicylic acid) to COX-2 enzyme
    # PDB ID: 1CX2 (Cyclooxygenase-2 in complex with a selective inhibitor)
    # Ligand: Aspirin SMILES: CC(=O)Oc1ccccc1C(=O)O

    print("\nExample: Docking aspirin to COX-2 (PDB: 1CX2)")
    print("Ligand SMILES: CC(=O)Oc1ccccc1C(=O)O")
    print("Target: 1CX2 (Cyclooxygenase-2)")
    print("Engine: Attracting Cavities 2.0 (default)")
    print("\nWARNING: This will make real API calls and may take 5-15 minutes.")
    print("To test without running, examine the tool schema above.")

    # Uncomment below to actually run the docking
    # result = tu.run_one_function({
    #     'name': 'SwissDock_dock_ligand',
    #     'arguments': {
    #         'ligand_smiles': 'CC(=O)Oc1ccccc1C(=O)O',  # Aspirin
    #         'pdb_id': '1CX2',  # COX-2
    #         'exhaustiveness': 8,  # Default exhaustiveness
    #         'docking_engine': 'attracting_cavities'
    #     }
    # })
    #
    # print("\nDocking Result:")
    # print(json.dumps(result, indent=2))
    #
    # if result.get('status') == 'success':
    #     data = result.get('data', {})
    #     session_id = data.get('session_id')
    #     print(f"\nSession ID: {session_id}")
    #     if 'download_url' in data:
    #         print(f"Download results from: {data['download_url']}")
    #     else:
    #         print("Job still running. Use SwissDock_check_job_status to monitor progress.")

    print("\n[Test skipped - uncomment code above to run actual docking]")


def test_swissdock_tool_schema(tu):
    """Display detailed schema for SwissDock tools."""
    print("\n" + "="*80)
    print("SwissDock Tool Schemas")
    print("="*80)

    # Get the dock_ligand tool
    dock_tool = next(
        (t for t in tu.all_tools if t['name'] == 'SwissDock_dock_ligand'),
        None
    )

    if dock_tool:
        print("\nSwissDock_dock_ligand:")
        print(f"  Description: {dock_tool['description']}")
        print("\n  Parameters:")
        props = dock_tool['parameters']['properties']
        for param_name, param_def in props.items():
            required = param_name in dock_tool['parameters'].get('required', [])
            req_str = " (required)" if required else " (optional)"
            print(f"    - {param_name}{req_str}:")
            print(f"        Type: {param_def.get('type')}")
            print(f"        Description: {param_def.get('description')}")
            if 'default' in param_def:
                print(f"        Default: {param_def['default']}")
            if 'enum' in param_def:
                print(f"        Options: {param_def['enum']}")
            print()


def main():
    """Run all SwissDock tests."""
    print("\n" + "="*80)
    print("SwissDock Tool Test Suite")
    print("="*80)
    print("\nSwissDock provides protein-ligand molecular docking using:")
    print("  - AutoDock Vina")
    print("  - Attracting Cavities 2.0")
    print("\nWebsite: https://www.swissdock.ch/")
    print("API Docs: https://www.swissdock.ch/command-line.php")
    print()

    # Test 1: Tool loading
    tu = test_swissdock_tool_loading()

    # Test 2: Tool schema
    test_swissdock_tool_schema(tu)

    # Test 3: Dry run (doesn't execute)
    test_swissdock_dock_ligand_dry_run(tu)

    print("\n" + "="*80)
    print("Test Suite Complete")
    print("="*80)
    print("\nTo perform actual docking:")
    print("1. Uncomment the code in test_swissdock_dock_ligand_dry_run()")
    print("2. Run this script again")
    print("3. Wait 5-15 minutes for docking to complete")
    print("4. Check results in the returned data")
    print()


if __name__ == "__main__":
    main()
