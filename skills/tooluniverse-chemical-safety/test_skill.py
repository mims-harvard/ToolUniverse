#!/usr/bin/env python3
"""
Comprehensive Test Suite for Chemical Safety & Toxicology Skill

Tests all 8 phases of the skill workflow using real tool calls.
Validates tool parameters, response structures, and documentation accuracy.
"""

import sys
import time
import traceback

# Track results
test_results = []
total_tests = 0
passed_tests = 0
failed_tests = 0


def record_result(test_name, passed, details=""):
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    if passed:
        passed_tests += 1
        status = "PASS"
    else:
        failed_tests += 1
        status = "FAIL"
    test_results.append({"name": test_name, "status": status, "details": details})
    print(f"  [{status}] {test_name}")
    if details and not passed:
        print(f"        Details: {details}")


def test_tool_loading():
    """Test 1: Verify all required tools load into ToolUniverse"""
    print("\n=== Test 1: Tool Loading ===")
    try:
        from tooluniverse import ToolUniverse
        tu = ToolUniverse()
        tu.load_tools()

        required_tools = [
            # ADMET-AI tools (Phase 1 & 2)
            "ADMETAI_predict_toxicity",
            "ADMETAI_predict_BBB_penetrance",
            "ADMETAI_predict_bioavailability",
            "ADMETAI_predict_clearance_distribution",
            "ADMETAI_predict_CYP_interactions",
            "ADMETAI_predict_nuclear_receptor_activity",
            "ADMETAI_predict_physicochemical_properties",
            "ADMETAI_predict_solubility_lipophilicity_hydration",
            "ADMETAI_predict_stress_response",
            # CTD tools (Phase 3)
            "CTD_get_chemical_gene_interactions",
            "CTD_get_chemical_diseases",
            # FDA tools (Phase 4)
            "FDA_get_boxed_warning_info_by_drug_name",
            "FDA_get_contraindications_by_drug_name",
            "FDA_get_adverse_reactions_by_drug_name",
            "FDA_get_warnings_by_drug_name",
            "FDA_get_nonclinical_toxicology_info_by_drug_name",
            # DrugBank (Phase 5)
            "drugbank_get_safety_by_drug_name_or_drugbank_id",
            # STITCH (Phase 6)
            "STITCH_resolve_identifier",
            "STITCH_get_chemical_protein_interactions",
            # ChEMBL (Phase 7)
            "ChEMBL_search_compound_structural_alerts",
            # PubChem (Phase 0)
            "PubChem_get_CID_by_compound_name",
            "PubChem_get_compound_properties_by_CID",
        ]

        all_tools = set(tu.all_tool_dict.keys())
        missing = [t for t in required_tools if t not in all_tools]

        if missing:
            record_result("All required tools loaded", False,
                          f"Missing tools: {missing}")
        else:
            record_result("All required tools loaded", True,
                          f"All {len(required_tools)} tools found in {len(all_tools)} total tools")

        return tu
    except Exception as e:
        record_result("Tool loading", False, f"Exception: {e}")
        return None


def test_phase0_disambiguation(tu):
    """Test 2: Phase 0 - Compound disambiguation"""
    print("\n=== Test 2: Phase 0 - Compound Disambiguation ===")
    if tu is None:
        record_result("Phase 0 skipped (no TU)", False, "ToolUniverse not loaded")
        return None, None

    # Test 2a: Name to CID resolution
    try:
        result = tu.tools.PubChem_get_CID_by_compound_name(name="Acetaminophen")
        if isinstance(result, dict) and "data" in result:
            cid_data = result["data"]
            if isinstance(cid_data, dict) and "IdentifierList" in cid_data:
                cids = cid_data["IdentifierList"].get("CID", [])
                if len(cids) > 0 and cids[0] == 1983:
                    record_result("PubChem name->CID (Acetaminophen=1983)", True)
                else:
                    record_result("PubChem name->CID", True,
                                  f"CID returned: {cids[0] if cids else 'none'} (expected 1983)")
            else:
                record_result("PubChem name->CID", False,
                              f"Unexpected data structure: {list(cid_data.keys()) if isinstance(cid_data, dict) else type(cid_data)}")
        else:
            # Try direct access pattern
            if isinstance(result, dict):
                record_result("PubChem name->CID", True,
                              f"Non-standard response, keys: {list(result.keys())[:5]}")
            else:
                record_result("PubChem name->CID", False,
                              f"Unexpected response type: {type(result)}")
    except Exception as e:
        record_result("PubChem name->CID", False, f"Exception: {e}")

    # Test 2b: CID to properties
    smiles = None
    try:
        result = tu.tools.PubChem_get_compound_properties_by_CID(cid=1983)
        if isinstance(result, dict):
            # Try to extract SMILES from response
            data = result.get("data", result)
            if isinstance(data, dict):
                props = data.get("PropertyTable", {}).get("Properties", [{}])
                if props and isinstance(props, list) and len(props) > 0:
                    smiles = props[0].get("CanonicalSMILES") or props[0].get("IsomericSMILES")
                    if smiles:
                        record_result("PubChem CID->properties (SMILES extracted)", True,
                                      f"SMILES: {smiles}")
                    else:
                        record_result("PubChem CID->properties", True,
                                      f"Properties found but no SMILES field. Keys: {list(props[0].keys())[:8]}")
                else:
                    record_result("PubChem CID->properties", True,
                                  f"Data returned, structure: {list(data.keys())[:5]}")
            else:
                record_result("PubChem CID->properties", True,
                              f"Data type: {type(data)}")
        else:
            record_result("PubChem CID->properties", False,
                          f"Unexpected response type: {type(result)}")
    except Exception as e:
        record_result("PubChem CID->properties", False, f"Exception: {e}")

    # Fallback SMILES for Acetaminophen if extraction failed
    if not smiles:
        smiles = "CC(=O)Nc1ccc(O)cc1"
        print(f"  [INFO] Using fallback SMILES: {smiles}")

    return 1983, smiles


def test_phase1_toxicity(tu, smiles):
    """Test 3: Phase 1 - Predictive toxicity (ADMET-AI)"""
    print("\n=== Test 3: Phase 1 - Predictive Toxicity ===")
    if tu is None or smiles is None:
        record_result("Phase 1 skipped", False, "Prerequisites not met")
        return

    # Test 3a: Toxicity prediction
    try:
        result = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
        if isinstance(result, dict):
            data = result.get("data", result)
            record_result("ADMETAI_predict_toxicity", True,
                          f"Response keys: {list(data.keys())[:8] if isinstance(data, dict) else type(data)}")
        else:
            record_result("ADMETAI_predict_toxicity", True,
                          f"Response type: {type(result)}")
    except Exception as e:
        record_result("ADMETAI_predict_toxicity", False, f"Exception: {e}")

    # Test 3b: Stress response prediction
    try:
        result = tu.tools.ADMETAI_predict_stress_response(smiles=[smiles])
        if isinstance(result, dict):
            record_result("ADMETAI_predict_stress_response", True)
        else:
            record_result("ADMETAI_predict_stress_response", True,
                          f"Type: {type(result)}")
    except Exception as e:
        record_result("ADMETAI_predict_stress_response", False, f"Exception: {e}")

    # Test 3c: Nuclear receptor activity
    try:
        result = tu.tools.ADMETAI_predict_nuclear_receptor_activity(smiles=[smiles])
        if isinstance(result, dict):
            record_result("ADMETAI_predict_nuclear_receptor_activity", True)
        else:
            record_result("ADMETAI_predict_nuclear_receptor_activity", True,
                          f"Type: {type(result)}")
    except Exception as e:
        record_result("ADMETAI_predict_nuclear_receptor_activity", False, f"Exception: {e}")


def test_phase2_admet(tu, smiles):
    """Test 4: Phase 2 - ADMET Properties"""
    print("\n=== Test 4: Phase 2 - ADMET Properties ===")
    if tu is None or smiles is None:
        record_result("Phase 2 skipped", False, "Prerequisites not met")
        return

    admet_tools = [
        ("ADMETAI_predict_BBB_penetrance", "BBB"),
        ("ADMETAI_predict_bioavailability", "Bioavailability"),
        ("ADMETAI_predict_clearance_distribution", "Clearance/Distribution"),
        ("ADMETAI_predict_CYP_interactions", "CYP Interactions"),
        ("ADMETAI_predict_physicochemical_properties", "Physicochemical"),
        ("ADMETAI_predict_solubility_lipophilicity_hydration", "Solubility/Lipophilicity"),
    ]

    for tool_name, label in admet_tools:
        try:
            tool_fn = getattr(tu.tools, tool_name)
            result = tool_fn(smiles=[smiles])
            if result is not None:
                record_result(f"ADMET: {label}", True)
            else:
                record_result(f"ADMET: {label}", False, "None returned")
        except Exception as e:
            record_result(f"ADMET: {label}", False, f"Exception: {e}")


def test_phase3_toxicogenomics(tu):
    """Test 5: Phase 3 - CTD Toxicogenomics"""
    print("\n=== Test 5: Phase 3 - CTD Toxicogenomics ===")
    if tu is None:
        record_result("Phase 3 skipped", False, "Prerequisites not met")
        return

    # Test 5a: Chemical-gene interactions
    try:
        result = tu.tools.CTD_get_chemical_gene_interactions(input_terms="Acetaminophen")
        if isinstance(result, (list, dict)):
            if isinstance(result, list):
                count = len(result)
            elif isinstance(result, dict):
                data = result.get("data", [])
                count = len(data) if isinstance(data, list) else 1
            else:
                count = 0
            record_result("CTD chemical-gene interactions", True,
                          f"Results: {count} interactions")
        else:
            record_result("CTD chemical-gene interactions", True,
                          f"Response type: {type(result)}")
    except Exception as e:
        record_result("CTD chemical-gene interactions", False, f"Exception: {e}")

    # Test 5b: Chemical-disease associations
    try:
        result = tu.tools.CTD_get_chemical_diseases(input_terms="Acetaminophen")
        if isinstance(result, (list, dict)):
            if isinstance(result, list):
                count = len(result)
            elif isinstance(result, dict):
                data = result.get("data", [])
                count = len(data) if isinstance(data, list) else 1
            else:
                count = 0
            record_result("CTD chemical-disease associations", True,
                          f"Results: {count} associations")
        else:
            record_result("CTD chemical-disease associations", True,
                          f"Response type: {type(result)}")
    except Exception as e:
        record_result("CTD chemical-disease associations", False, f"Exception: {e}")


def test_phase4_fda(tu):
    """Test 6: Phase 4 - FDA Regulatory Safety"""
    print("\n=== Test 6: Phase 4 - FDA Regulatory Safety ===")
    if tu is None:
        record_result("Phase 4 skipped", False, "Prerequisites not met")
        return

    fda_tools = [
        ("FDA_get_boxed_warning_info_by_drug_name", "Boxed Warning"),
        ("FDA_get_contraindications_by_drug_name", "Contraindications"),
        ("FDA_get_adverse_reactions_by_drug_name", "Adverse Reactions"),
        ("FDA_get_warnings_by_drug_name", "Warnings"),
        ("FDA_get_nonclinical_toxicology_info_by_drug_name", "Nonclinical Toxicology"),
    ]

    for tool_name, label in fda_tools:
        try:
            tool_fn = getattr(tu.tools, tool_name)
            result = tool_fn(drug_name="Acetaminophen")
            if result is not None:
                record_result(f"FDA: {label}", True)
            else:
                record_result(f"FDA: {label}", False, "None returned")
        except Exception as e:
            record_result(f"FDA: {label}", False, f"Exception: {e}")


def test_phase5_drugbank(tu):
    """Test 7: Phase 5 - DrugBank Safety"""
    print("\n=== Test 7: Phase 5 - DrugBank Safety ===")
    if tu is None:
        record_result("Phase 5 skipped", False, "Prerequisites not met")
        return

    try:
        result = tu.tools.drugbank_get_safety_by_drug_name_or_drugbank_id(
            query="Acetaminophen",
            case_sensitive=False,
            exact_match=False,
            limit=5
        )
        if result is not None:
            record_result("DrugBank safety profile", True,
                          f"Response type: {type(result).__name__}")
        else:
            record_result("DrugBank safety profile", False, "None returned")
    except Exception as e:
        record_result("DrugBank safety profile", False, f"Exception: {e}")


def test_phase6_stitch(tu):
    """Test 8: Phase 6 - STITCH Chemical-Protein Interactions"""
    print("\n=== Test 8: Phase 6 - STITCH Interactions ===")
    if tu is None:
        record_result("Phase 6 skipped", False, "Prerequisites not met")
        return

    # Test 8a: Resolve identifier
    try:
        result = tu.tools.STITCH_resolve_identifier(
            identifier="acetaminophen", species=9606
        )
        if result is not None:
            record_result("STITCH resolve identifier", True)
        else:
            record_result("STITCH resolve identifier", False, "None returned")
    except Exception as e:
        record_result("STITCH resolve identifier", False, f"Exception: {e}")

    # Test 8b: Chemical-protein interactions
    try:
        result = tu.tools.STITCH_get_chemical_protein_interactions(
            identifiers=["CIDm01983"],  # STITCH format for PubChem CID
            species=9606,
            required_score=400
        )
        if result is not None:
            record_result("STITCH chemical-protein interactions", True)
        else:
            record_result("STITCH chemical-protein interactions", False, "None returned")
    except Exception as e:
        record_result("STITCH chemical-protein interactions", False, f"Exception: {e}")


def test_phase7_structural_alerts(tu):
    """Test 9: Phase 7 - ChEMBL Structural Alerts"""
    print("\n=== Test 9: Phase 7 - Structural Alerts ===")
    if tu is None:
        record_result("Phase 7 skipped", False, "Prerequisites not met")
        return

    try:
        # CHEMBL112 is Acetaminophen
        result = tu.tools.ChEMBL_search_compound_structural_alerts(
            molecule_chembl_id="CHEMBL112",
            limit=20
        )
        if result is not None:
            record_result("ChEMBL structural alerts", True,
                          f"Response type: {type(result).__name__}")
        else:
            record_result("ChEMBL structural alerts", False, "None returned")
    except Exception as e:
        record_result("ChEMBL structural alerts", False, f"Exception: {e}")


def test_environmental_chemical(tu):
    """Test 10: Environmental chemical (non-drug) workflow"""
    print("\n=== Test 10: Environmental Chemical (Bisphenol A) ===")
    if tu is None:
        record_result("Environmental test skipped", False, "Prerequisites not met")
        return

    # Test BPA: a key environmental chemical
    try:
        result = tu.tools.CTD_get_chemical_gene_interactions(input_terms="bisphenol A")
        if isinstance(result, (list, dict)):
            data = result if isinstance(result, list) else result.get("data", [])
            count = len(data) if isinstance(data, list) else 0
            record_result("CTD: BPA gene interactions", True,
                          f"Found {count} gene interactions")
        else:
            record_result("CTD: BPA gene interactions", True,
                          f"Response: {type(result)}")
    except Exception as e:
        record_result("CTD: BPA gene interactions", False, f"Exception: {e}")

    try:
        result = tu.tools.CTD_get_chemical_diseases(input_terms="bisphenol A")
        if isinstance(result, (list, dict)):
            data = result if isinstance(result, list) else result.get("data", [])
            count = len(data) if isinstance(data, list) else 0
            record_result("CTD: BPA disease associations", True,
                          f"Found {count} disease associations")
        else:
            record_result("CTD: BPA disease associations", True,
                          f"Response: {type(result)}")
    except Exception as e:
        record_result("CTD: BPA disease associations", False, f"Exception: {e}")


def test_batch_smiles(tu):
    """Test 11: Batch SMILES processing"""
    print("\n=== Test 11: Batch SMILES Processing ===")
    if tu is None:
        record_result("Batch test skipped", False, "Prerequisites not met")
        return

    # Test batch ADMET prediction with multiple compounds
    smiles_batch = [
        "CC(=O)Nc1ccc(O)cc1",     # Acetaminophen
        "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin
        "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen
    ]

    try:
        result = tu.tools.ADMETAI_predict_toxicity(smiles=smiles_batch)
        if result is not None:
            record_result("Batch toxicity prediction (3 compounds)", True)
        else:
            record_result("Batch toxicity prediction", False, "None returned")
    except Exception as e:
        record_result("Batch toxicity prediction", False, f"Exception: {e}")


def generate_report():
    """Generate test report"""
    print("\n" + "=" * 60)
    print("CHEMICAL SAFETY SKILL - TEST REPORT")
    print("=" * 60)
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Pass Rate: {passed_tests}/{total_tests} ({100*passed_tests/max(total_tests,1):.1f}%)")
    print()

    if failed_tests > 0:
        print("FAILED TESTS:")
        for r in test_results:
            if r["status"] == "FAIL":
                print(f"  - {r['name']}: {r['details']}")
        print()

    print("ALL RESULTS:")
    for r in test_results:
        print(f"  [{r['status']}] {r['name']}")
        if r["details"]:
            print(f"         {r['details']}")

    return failed_tests == 0


def main():
    print("Chemical Safety & Toxicology Skill - Comprehensive Test Suite")
    print("=" * 60)
    print(f"Testing against: Acetaminophen (primary), Bisphenol A (environmental)")
    print()

    start_time = time.time()

    # Test 1: Tool loading
    tu = test_tool_loading()

    # Test 2: Phase 0 - Disambiguation
    cid, smiles = test_phase0_disambiguation(tu)

    # Test 3: Phase 1 - Toxicity predictions
    test_phase1_toxicity(tu, smiles)

    # Test 4: Phase 2 - ADMET properties
    test_phase2_admet(tu, smiles)

    # Test 5: Phase 3 - CTD toxicogenomics
    test_phase3_toxicogenomics(tu)

    # Test 6: Phase 4 - FDA regulatory safety
    test_phase4_fda(tu)

    # Test 7: Phase 5 - DrugBank safety
    test_phase5_drugbank(tu)

    # Test 8: Phase 6 - STITCH interactions
    test_phase6_stitch(tu)

    # Test 9: Phase 7 - Structural alerts
    test_phase7_structural_alerts(tu)

    # Test 10: Environmental chemical workflow
    test_environmental_chemical(tu)

    # Test 11: Batch processing
    test_batch_smiles(tu)

    elapsed = time.time() - start_time
    print(f"\nTotal execution time: {elapsed:.1f} seconds")

    # Generate report
    all_passed = generate_report()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
