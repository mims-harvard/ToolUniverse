"""
Drug Safety Analysis Pipeline
Comprehensive drug safety analysis combining adverse event data, literature review, and molecular information
"""

from tooluniverse.compose_scripts import payload


def compose(arguments, tooluniverse, call_tool):
    """
    Main composition function for DrugSafetyAnalyzer

    Args:
        arguments (dict): Input arguments containing drug_name, patient_sex, serious_events_only
        tooluniverse: ToolUniverse instance
        call_tool: Function to call other tools

    Returns
        dict: Comprehensive drug safety analysis result
    """
    drug_name = arguments["drug_name"]
    patient_sex = arguments.get("patient_sex")
    serious_only = arguments.get("serious_events_only", False)

    print(f"Starting comprehensive safety analysis for: {drug_name}")

    # Step 1: Get adverse event data from FDA FAERS
    faers_result = None
    try:
        # Prepare FAERS query parameters - only include non-None values
        faers_params = {"medicinalproduct": drug_name}
        if patient_sex:
            faers_params["patientsex"] = patient_sex
        if serious_only:
            faers_params["serious"] = "Yes"
        faers_result = call_tool("FAERS_count_reactions_by_drug_event", faers_params)
    except Exception as e:
        print(f"FAERS query failed: {e}")

    # Step 2: Get molecular information from PubChem
    molecular_info = None
    try:
        pubchem_cid_result = payload(
            call_tool("PubChem_get_CID_by_compound_name", {"name": drug_name})
        )
        if (
            isinstance(pubchem_cid_result, dict)
            and "IdentifierList" in pubchem_cid_result
        ):
            cid_list = pubchem_cid_result["IdentifierList"].get("CID", [])
            if cid_list:
                first_cid = cid_list[0]
                molecular_info = payload(
                    call_tool(
                        "PubChem_get_compound_properties_by_CID", {"cid": first_cid}
                    )
                )
    except Exception as e:
        print(f"PubChem query failed: {e}")

    # Step 3: Search for safety-related literature
    literature_result = None
    try:
        literature_query = f"{drug_name} safety adverse effects"
        literature_result = call_tool(
            "EuropePMC_search_articles", {"query": literature_query, "limit": 10}
        )
    except Exception as e:
        print(f"Literature search failed: {e}")

    # Step 4: Compile comprehensive analysis result
    result = {
        "drug_name": drug_name,
        "analysis_parameters": {
            "patient_sex_filter": patient_sex,
            "serious_events_only": serious_only,
        },
        "adverse_events": faers_result,
        "molecular_properties": molecular_info,
        "safety_literature": literature_result,
        "analysis_summary": {
            "has_adverse_events": bool(payload(faers_result)),
            "has_molecular_data": bool(molecular_info),
            "literature_papers_found": len(payload(literature_result) or []),
        },
    }

    print(f"Safety analysis complete for {drug_name}")
    return result
