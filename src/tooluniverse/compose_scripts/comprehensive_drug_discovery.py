"""
Comprehensive Drug Discovery Pipeline
Complete end-to-end drug discovery workflow from disease to optimized candidates
"""

from tooluniverse.compose_scripts import payload


def compose(arguments, tooluniverse, call_tool):
    """End-to-end drug discovery: Target → Lead → Optimization → Validation"""

    disease_efo_id = arguments["disease_efo_id"]
    results = {}

    # Phase 1: Target Identification & Validation
    print("Phase 1: Target Identification...")
    try:
        target_result = call_tool(
            "OpenTargets_get_associated_targets_by_disease_efoId",
            {"efoId": disease_efo_id},
        )
        selected_targets = target_result["data"]["disease"]["associatedTargets"][
            "rows"
        ][:5]
        results["target_selection"] = target_result
        print(f"✅ Found {len(selected_targets)} targets")
    except Exception as e:
        print(f"❌ Target identification failed: {e}")
        results["target_selection"] = {"error": str(e)}
        return results

    # Phase 2: Lead Compound Discovery (using OpenTargets drugs)
    print("Phase 2: Lead Discovery...")
    try:
        # Get known drugs for this disease
        known_drugs = call_tool(
            "OpenTargets_get_associated_drugs_by_disease_efoId",
            {"efoId": disease_efo_id, "size": 20},
        )

        if "data" in known_drugs and "disease" in known_drugs["data"]:
            drugs_data = known_drugs["data"]["disease"].get("knownDrugs", {})
            drug_rows = drugs_data.get("rows", [])
            results["lead_discovery"] = {
                "total_drugs": len(drug_rows),
                "approved_drugs": len(
                    [d for d in drug_rows if d.get("drug", {}).get("isApproved", False)]
                ),
                "drug_data": drug_rows,  # Store full drug data for safety assessment
            }
            print(f"✅ Found {len(drug_rows)} known drugs")
        else:
            results["lead_discovery"] = {"error": "No drug data available"}
            print("⚠️ No drug data available")
    except Exception as e:
        print(f"⚠️ Drug discovery failed: {e}")
        results["lead_discovery"] = {"error": str(e)}

    # Phase 3: Safety Assessment (using ADMETAI tools)
    print("Phase 3: Safety Assessment...")
    safety_assessments = []

    # Extract SMILES from known drugs for ADMET assessment
    try:
        if "lead_discovery" in results and "total_drugs" in results["lead_discovery"]:
            # Get drug SMILES from OpenTargets drug data
            drug_data = results["lead_discovery"].get("drug_data", [])
            if drug_data:
                # Extract SMILES from first few drugs for assessment
                test_smiles = []
                processed_drugs = set()  # Track processed drugs to avoid duplicates

                for drug in drug_data[:5]:  # Test first 5 drugs
                    if "drug" in drug:
                        drug_info = drug["drug"]
                        drug_name = drug_info.get("name", "")

                        # Skip if already processed
                        if drug_name in processed_drugs:
                            continue
                        processed_drugs.add(drug_name)

                        # Try to get SMILES from drug name using PubChem
                        if drug_name:
                            try:
                                # Get CID from drug name
                                cid_result = payload(
                                    call_tool(
                                        "PubChem_get_CID_by_compound_name",
                                        {"name": drug_name},
                                    )
                                )

                                if (
                                    cid_result
                                    and "IdentifierList" in cid_result
                                    and "CID" in cid_result["IdentifierList"]
                                ):
                                    cids = cid_result["IdentifierList"]["CID"]
                                    if cids:
                                        # Get SMILES from first CID
                                        smiles_result = payload(
                                            call_tool(
                                                "PubChem_get_compound_properties_by_CID",
                                                {"cid": cids[0]},
                                            )
                                        )

                                        if (
                                            smiles_result
                                            and "PropertyTable" in smiles_result
                                        ):
                                            properties = smiles_result[
                                                "PropertyTable"
                                            ].get("Properties", [])
                                            if properties:
                                                # Try CanonicalSMILES first, then ConnectivitySMILES
                                                smiles = properties[0].get(
                                                    "CanonicalSMILES"
                                                ) or properties[0].get(
                                                    "ConnectivitySMILES"
                                                )
                                                if (
                                                    smiles and smiles not in test_smiles
                                                ):  # Avoid duplicate SMILES
                                                    test_smiles.append(smiles)
                                                    print(
                                                        f"✅ Found SMILES for {drug_name}: {smiles[:50]}..."
                                                    )

                                                    # Stop after finding 3 unique SMILES
                                                    if len(test_smiles) >= 3:
                                                        break
                            except Exception as e:
                                print(f"⚠️ Failed to get SMILES for {drug_name}: {e}")

                if test_smiles:
                    # Test BBB penetrance
                    bbb_result = call_tool(
                        "ADMETAI_predict_BBB_penetrance", {"smiles": test_smiles}
                    )

                    # Test bioavailability
                    bio_result = call_tool(
                        "ADMETAI_predict_bioavailability", {"smiles": test_smiles}
                    )

                    # Test toxicity
                    tox_result = call_tool(
                        "ADMETAI_predict_toxicity", {"smiles": test_smiles}
                    )

                    safety_assessments.append(
                        {
                            "compounds_assessed": len(test_smiles),
                            "bbb_penetrance": bbb_result,
                            "bioavailability": bio_result,
                            "toxicity": tox_result,
                        }
                    )

                    results["safety_assessment"] = safety_assessments
                    print(
                        f"✅ Completed safety assessment for {len(test_smiles)} compounds"
                    )
                else:
                    print("⚠️ No SMILES data available for safety assessment")
                    results["safety_assessment"] = {"error": "No SMILES data available"}
            else:
                print("⚠️ No drug data available for safety assessment")
                results["safety_assessment"] = {"error": "No drug data available"}
        else:
            print("⚠️ Lead discovery phase failed, skipping safety assessment")
            results["safety_assessment"] = {"error": "Lead discovery phase failed"}
    except Exception as e:
        print(f"⚠️ Safety assessment failed: {e}")
        results["safety_assessment"] = {"error": str(e)}

    # Phase 4: Literature Validation
    print("Phase 4: Literature Validation...")
    try:
        literature_validation = call_tool(
            "LiteratureSearchTool",
            {"research_topic": f"drug discovery {disease_efo_id} therapeutic targets"},
        )
        results["literature_validation"] = literature_validation
        print("✅ Literature validation completed")
    except Exception as e:
        print(f"⚠️ Literature validation failed: {e}")
        results["literature_validation"] = {"error": str(e)}

    return results
