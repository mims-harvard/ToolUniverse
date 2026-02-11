#!/usr/bin/env python3
"""ProteinsPlus tools -- protein-ligand docking and binding site analysis examples."""

from tooluniverse import ToolUniverse


def example_binding_site_prediction():
    """Example 1: Predict druggable binding sites in a protein structure."""
    print("=" * 80)
    print("Example 1: Binding Site Prediction (DoGSiteScorer)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Predict binding sites in hemoglobin (4HHB)
    result = tu.tools.ProteinsPlus_predict_binding_sites(
        pdb_id="4HHB",
        chain="A"
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'N/A')}")
    else:
        print(f"Found {len(result['data'].get('pockets', []))} binding pockets")
        for pocket in result['data'].get('pockets', [])[:3]:
            print(f"\nPocket {pocket.get('pocket_id')}:")
            print(f"  Druggability Score: {pocket.get('druggability_score', 'N/A'):.3f}")
            print(f"  Volume: {pocket.get('volume', 'N/A'):.1f} Å³")
            print(f"  Surface Area: {pocket.get('surface_area', 'N/A'):.1f} Å²")
            print(f"  Residues: {', '.join(pocket.get('residues', [])[:5])}...")

    tu.close()


def example_structure_validation():
    """Example 2: Check structure quality before docking."""
    print("\n" + "=" * 80)
    print("Example 2: Structure Quality Check")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Check structure quality
    result = tu.tools.ProteinsPlus_check_structure(
        pdb_id="1A2B"
    )

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        data = result.get('data', {})
        print(f"Quality Score: {data.get('quality_score', 'N/A')}/100")

        stats = data.get('statistics', {})
        print(f"\nStructure Statistics:")
        print(f"  Atoms: {stats.get('num_atoms', 'N/A')}")
        print(f"  Residues: {stats.get('num_residues', 'N/A')}")
        print(f"  Chains: {stats.get('num_chains', 'N/A')}")
        print(f"  Missing Atoms: {stats.get('missing_atoms', 0)}")
        print(f"  Steric Clashes: {stats.get('steric_clashes', 0)}")

        issues = data.get('issues', [])
        if issues:
            print(f"\nIssues Found: {len(issues)}")
            for issue in issues[:5]:
                print(f"  [{issue.get('type', 'N/A').upper()}] {issue.get('message', 'N/A')}")

    tu.close()


def example_ligand_docking():
    """Example 3: Dock a small molecule ligand into a protein."""
    print("\n" + "=" * 80)
    print("Example 3: Protein-Ligand Docking (JAMDA)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Dock aspirin into a protein structure
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"

    result = tu.tools.ProteinsPlus_dock_ligand(
        pdb_id="1A2B",
        ligand_smiles=aspirin_smiles,
        num_poses=5
    )

    if "error" in result:
        print(f"Error: {result['error']}")
        print(f"Detail: {result.get('detail', 'N/A')}")
    else:
        print(f"Ligand: Aspirin (SMILES: {aspirin_smiles})")
        poses = result['data'].get('poses', [])
        print(f"Generated {len(poses)} docking poses")

        if poses:
            best_pose = poses[0]
            print(f"\nBest Pose:")
            print(f"  Score: {best_pose.get('score', 'N/A'):.2f}")
            print(f"  RMSD: {best_pose.get('rmsd', 'N/A'):.2f} Å")
            print(f"  Overall Best Score: {result['data'].get('best_score', 'N/A'):.2f}")

    tu.close()


def example_interaction_analysis():
    """Example 4: Analyze protein-ligand interactions."""
    print("\n" + "=" * 80)
    print("Example 4: Interaction Analysis (PLIP)")
    print("=" * 80)

    tu = ToolUniverse()
    tu.load_tools()

    # Analyze interactions in hemoglobin with heme
    result = tu.tools.ProteinsPlus_analyze_interactions(
        pdb_id="4HHB",
        ligand_id="HEM",
        chain="A"
    )

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        interactions = result['data'].get('interactions', {})

        hbonds = interactions.get('hydrogen_bonds', [])
        hydrophobic = interactions.get('hydrophobic_contacts', [])
        salt_bridges = interactions.get('salt_bridges', [])
        pi_stacking = interactions.get('pi_stacking', [])

        print(f"Interaction Summary:")
        print(f"  Hydrogen Bonds: {len(hbonds)}")
        print(f"  Hydrophobic Contacts: {len(hydrophobic)}")
        print(f"  Salt Bridges: {len(salt_bridges)}")
        print(f"  Pi-Stacking: {len(pi_stacking)}")

        if hbonds:
            print(f"\nTop Hydrogen Bonds:")
            for hb in hbonds[:3]:
                print(f"  {hb.get('donor', 'N/A')} ↔ {hb.get('acceptor', 'N/A')}")
                print(f"    Distance: {hb.get('distance', 'N/A'):.2f} Å")

        binding_site = result['data'].get('binding_site_residues', [])
        if binding_site:
            print(f"\nBinding Site Residues ({len(binding_site)}):")
            print(f"  {', '.join(binding_site[:10])}...")

    tu.close()


def example_drug_discovery_workflow():
    """Example 5: Complete drug discovery workflow."""
    print("\n" + "=" * 80)
    print("Example 5: Complete Drug Discovery Workflow")
    print("=" * 80)

    tu = ToolUniverse(use_cache=True)
    tu.load_tools()

    pdb_id = "1A2B"
    ligand_smiles = "CC(C)Cc1ccc(cc1)C(C)C(O)=O"  # Ibuprofen

    print(f"Target: PDB {pdb_id}")
    print(f"Ligand: Ibuprofen")

    # Step 1: Check structure quality
    print("\n[Step 1] Checking structure quality...")
    quality = tu.tools.ProteinsPlus_check_structure(pdb_id=pdb_id)
    if "error" not in quality:
        score = quality['data'].get('quality_score', 0)
        print(f"  Quality Score: {score}/100")
        if score < 70:
            print("  Warning: Low quality structure")

    # Step 2: Predict binding sites
    print("\n[Step 2] Predicting binding sites...")
    sites = tu.tools.ProteinsPlus_predict_binding_sites(pdb_id=pdb_id)
    if "error" not in sites:
        pockets = sites['data'].get('pockets', [])
        print(f"  Found {len(pockets)} druggable pockets")
        if pockets:
            best_pocket = max(pockets, key=lambda p: p.get('druggability_score', 0))
            print(f"  Best pocket: #{best_pocket.get('pocket_id')} "
                  f"(score: {best_pocket.get('druggability_score', 0):.3f})")

    # Step 3: Dock ligand
    print("\n[Step 3] Docking ligand...")
    docking = tu.tools.ProteinsPlus_dock_ligand(
        pdb_id=pdb_id,
        ligand_smiles=ligand_smiles,
        num_poses=10
    )
    if "error" not in docking:
        poses = docking['data'].get('poses', [])
        print(f"  Generated {len(poses)} poses")
        if poses:
            best_score = docking['data'].get('best_score', 0)
            print(f"  Best binding score: {best_score:.2f}")

    # Step 4: Predict ADMET properties (if ligand docked successfully)
    if "error" not in docking and docking['data'].get('poses'):
        print("\n[Step 4] Predicting ADMET properties...")
        try:
            admet = tu.tools.ADMETAI_predict_admet(smiles=ligand_smiles)
            if "error" not in admet:
                props = admet.get('properties', {})
                print(f"  Lipophilicity: {props.get('lipophilicity', 'N/A')}")
                print(f"  Solubility: {props.get('solubility', 'N/A')}")
                print(f"  CYP Inhibition: {props.get('cyp_inhibition', 'N/A')}")
        except Exception as e:
            print(f"  ADMET prediction not available: {e}")

    print("\n[Workflow Complete]")
    tu.close()


if __name__ == "__main__":
    print("ProteinsPlus Tools - Structure-Based Drug Design Examples")
    print("=" * 80)
    print()

    try:
        example_binding_site_prediction()
        example_structure_validation()
        example_ligand_docking()
        example_interaction_analysis()
        example_drug_discovery_workflow()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("Examples complete!")
