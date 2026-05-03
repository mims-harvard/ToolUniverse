"""
Phase 2: Tool Testing for GWAS-to-Drug Target Discovery Skill

Tests ALL tools needed for the workflow with known drug targets:
- Type 2 diabetes (TCF7L2 rs7903146 → DPP4 inhibitors)
- Hypercholesterolemia (HMGCR → statins)
"""

from tooluniverse import ToolUniverse
from tooluniverse.tools.execute_tool import execute_tool


def test_gwas_tools():
    """Test GWAS tools for finding genetic associations."""
    print("\n" + "="*80)
    print("PHASE 1: Testing GWAS Tools")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Search associations for Type 2 Diabetes
    print("\n[Test 1] Search GWAS associations for Type 2 Diabetes...")
    try:
        result = execute_tool(
            "gwas_search_associations",
            {"disease_trait": "type 2 diabetes", "size": 5}
        )

        if result and 'data' in result and len(result['data']) > 0:
            print(f"✓ Found {len(result['data'])} T2D associations")
            assoc = result['data'][0]
            print(f"  - Top association: p-value={assoc.get('p_value')}")
            print(f"  - Mapped genes: {assoc.get('mapped_genes', [])[:5]}")
            rs_ids = [s.get('rs_id') for s in assoc.get('snp_allele', [])[:3] if s.get('rs_id')]
            print(f"  - rs_id: {rs_ids}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Get associations for specific SNP
    print("\n[Test 2] Get associations for rs7903146 (TCF7L2 variant)...")
    try:
        result = execute_tool(
            "gwas_get_associations_for_snp",
            {"rs_id": "rs7903146", "size": 5}
        )

        if result and 'data' in result and len(result['data']) > 0:
            print(f"✓ Found {len(result['data'])} associations for rs7903146")
            traits = [str(a.get('reported_trait', [])) for a in result['data'][:3]]
            print(f"  - Associated traits (sample): {traits[0][:80] if traits else 'N/A'}...")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 3: Get studies for trait
    print("\n[Test 3] Get GWAS studies for cholesterol...")
    try:
        result = execute_tool(
            "gwas_search_studies",
            {"disease_trait": "cholesterol", "size": 5}
        )

        if result and 'data' in result and len(result['data']) > 0:
            print(f"✓ Found {len(result['data'])} cholesterol studies")
            study = result['data'][0]
            print(f"  - Study: {study.get('accession_id')}")
            pubmed = study.get('pubmed_id', 'N/A')
            print(f"  - PubMed: {pubmed}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n✓ All GWAS tools working!")
    return True


def test_opentargets_genetics_tools():
    """Test Open Targets Genetics tools for fine-mapping."""
    print("\n" + "="*80)
    print("PHASE 2: Testing Open Targets Genetics Tools")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Search GWAS studies
    print("\n[Test 1] Search GWAS studies for Type 2 Diabetes...")
    try:
        result = execute_tool(
            "OpenTargets_search_gwas_studies_by_disease",
            {"diseaseIds": ["MONDO_0005148"], "size": 3}
        )

        if result and 'data' in result:
            studies = result['data'].get('studies', {})
            count = studies.get('count', 0)
            rows = studies.get('rows', [])
            print(f"✓ Found {count} T2D GWAS studies")
            if rows:
                study = rows[0]
                print(f"  - Study: {study.get('id')}")
                print(f"  - Samples: {study.get('nSamples')}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Get variant info
    print("\n[Test 2] Get variant info for rs7903146...")
    try:
        result = execute_tool(
            "OpenTargets_get_variant_info",
            {"variantId": "10_112998590_C_T"}
        )

        if result and 'data' in result:
            variant = result['data'].get('variant', {})
            if variant:
                print(f"✓ Variant: {variant.get('id')}")
                print(f"  - rsID: {variant.get('rsIds')}")
                print(f"  - Consequence: {variant.get('mostSevereConsequence', {}).get('label')}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n✓ All Open Targets Genetics tools working!")
    return True


def test_opentargets_platform_tools():
    """Test Open Targets Platform tools."""
    print("\n" + "="*80)
    print("PHASE 3: Testing Open Targets Platform Tools")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Get targets for disease
    print("\n[Test 1] Get targets for Type 2 Diabetes...")
    try:
        result = execute_tool(
            "OpenTargets_get_associated_targets_by_disease_efoId",
            {"efoId": "EFO_0001360"}
        )

        if result and 'data' in result:
            disease = result['data'].get('disease', {})
            targets = disease.get('associatedTargets', {})
            count = targets.get('count', 0)
            rows = targets.get('rows', [])[:5]

            print(f"✓ Found {count} targets for T2D")
            for target_data in rows:
                target = target_data.get('target', {})
                score = target_data.get('score', 0)
                print(f"  - {target.get('approvedSymbol')}: score={score:.3f}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Get drugs for disease
    print("\n[Test 2] Get drugs for Type 2 Diabetes...")
    try:
        result = execute_tool(
            "OpenTargets_get_associated_drugs_by_disease_efoId",
            {"efoId": "EFO_0001360"}
        )

        if result and 'data' in result:
            disease = result['data'].get('disease', {})
            drugs = disease.get('knownDrugs', {})
            count = drugs.get('count', 0)
            rows = drugs.get('rows', [])[:5]

            print(f"✓ Found {count} drugs for T2D")
            for drug_data in rows:
                drug = drug_data.get('drug', {})
                phase = drug_data.get('phase', 'N/A')
                print(f"  - {drug.get('name')}: phase={phase}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n✓ All Open Targets Platform tools working!")
    return True


def test_chembl_tools():
    """Test ChEMBL tools."""
    print("\n" + "="*80)
    print("PHASE 4: Testing ChEMBL Tools")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    # Test 1: Search drugs
    print("\n[Test 1] Search drugs for metformin...")
    try:
        result = execute_tool(
            "ChEMBL_search_drugs",
            {"q": "metformin"}
        )

        if result and 'data' in result:
            drugs = result['data'].get('molecules', [])
            print(f"✓ Found {len(drugs)} drugs")
            if drugs:
                drug = drugs[0]
                print(f"  - {drug.get('pref_name')}: {drug.get('molecule_chembl_id')}")
                print(f"  - Max phase: {drug.get('max_phase')}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Test 2: Get drug mechanisms
    print("\n[Test 2] Get mechanisms for atorvastatin (CHEMBL1431)...")
    try:
        result = execute_tool(
            "ChEMBL_get_drug_mechanisms",
            {"chembl_id": "CHEMBL1431"}
        )

        if result and 'data' in result:
            mechanisms = result['data'].get('mechanisms', [])
            print(f"✓ Found {len(mechanisms)} mechanisms")
            if mechanisms:
                mech = mechanisms[0]
                print(f"  - Target: {mech.get('target_chembl_id')}")
                print(f"  - Mechanism: {mech.get('mechanism_of_action')}")
        else:
            print("✗ No data returned")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    print("\n✓ All ChEMBL tools working!")
    return True


def test_integration_workflow():
    """Test integrated workflow."""
    print("\n" + "="*80)
    print("PHASE 5: Testing Integrated Workflow")
    print("="*80)

    tu = ToolUniverse()
    tu.load_tools()

    print("\n[WORKFLOW] Drug target discovery for Type 2 Diabetes:")
    print("-" * 80)

    # Step 1: Get GWAS associations
    print("\n1. Get GWAS associations for T2D...")
    try:
        result = execute_tool(
            "gwas_get_associations_for_trait",
            {"disease_trait": "type 2 diabetes", "size": 10}
        )

        if not result or 'data' not in result:
            print("✗ Step 1 failed")
            return False

        genes = set()
        for assoc in result['data']:
            genes.update(assoc.get('mapped_genes', []))

        print(f"✓ Found {len(genes)} unique genes from GWAS")
        print(f"  Sample genes: {list(genes)[:8]}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Step 2: Get target-disease associations
    print("\n2. Get target-disease associations for T2D...")
    try:
        result = execute_tool(
            "OpenTargets_get_associated_targets_by_disease_efoId",
            {"efoId": "EFO_0001360"}
        )

        if not result or 'data' not in result:
            print("✗ Step 2 failed")
            return False

        targets = result['data'].get('disease', {}).get('associatedTargets', {}).get('rows', [])
        print(f"✓ Found {len(targets)} associated targets")

        # Find overlap
        target_genes = {t.get('target', {}).get('approvedSymbol') for t in targets[:100]}
        overlap = genes & target_genes
        print(f"  Overlap with GWAS genes: {len(overlap)} genes")
        if overlap:
            print(f"  Overlapping: {list(overlap)[:5]}")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    # Step 3: Get existing drugs
    print("\n3. Get existing drugs for T2D...")
    try:
        result = execute_tool(
            "OpenTargets_get_associated_drugs_by_disease_efoId",
            {"efoId": "EFO_0001360"}
        )

        if not result or 'data' not in result:
            print("✗ Step 3 failed")
            return False

        drugs = result['data'].get('disease', {}).get('knownDrugs', {}).get('rows', [])
        approved_drugs = [d for d in drugs if d.get('phase') == 4]

        print(f"✓ Found {len(approved_drugs)} approved drugs")
        for drug_data in approved_drugs[:5]:
            drug = drug_data.get('drug', {})
            target = drug_data.get('target', {})
            print(f"  - {drug.get('name')} → {target.get('approvedSymbol')}")

        print(f"\n✓ Workflow completed successfully!")
        print(f"Summary: {len(genes)} GWAS genes → {len(overlap)} validated targets → {len(approved_drugs)} approved drugs")

    except Exception as e:
        print(f"✗ Error: {e}")
        return False

    return True


def run_all_tests():
    """Run all test phases."""
    print("\n" + "="*80)
    print("GWAS-TO-DRUG TARGET DISCOVERY SKILL - TOOL VALIDATION")
    print("="*80)

    results = {
        "GWAS Tools": test_gwas_tools(),
        "Open Targets Genetics": test_opentargets_genetics_tools(),
        "Open Targets Platform": test_opentargets_platform_tools(),
        "ChEMBL Tools": test_chembl_tools(),
        "Integration Workflow": test_integration_workflow(),
    }

    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)

    for phase, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {phase}")

    all_pass = all(results.values())

    if all_pass:
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED - Ready to implement skill!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠ SOME TESTS FAILED - Review errors (may be API rate limits)")
        print("="*80)

    return all_pass


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
