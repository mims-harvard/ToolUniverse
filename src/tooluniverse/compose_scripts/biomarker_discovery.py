"""
Biomarker Discovery Workflow
Discover and validate biomarkers for a specific disease condition using compose tools
"""


def _extract_genes(tool_result):
    """Pull a gene list out of an HPA_search_genes_by_query result.

    call_tool() returns the tool's raw envelope (e.g.
    {"status": "success", "data": {"genes": [...]}}), not the unwrapped
    payload -- this previously checked for "genes" at the top level only,
    which never matched, so every disease query silently fell through to
    (formerly) a hardcoded fallback / (now) an honest "no genes found".
    Check the nested location first, then the top level and bare list, for
    resilience to either response shape.
    """
    if isinstance(tool_result, dict):
        data = tool_result.get("data")
        if isinstance(data, dict) and isinstance(data.get("genes"), list):
            return data["genes"]
        if isinstance(tool_result.get("genes"), list):
            return tool_result["genes"]
    elif isinstance(tool_result, list):
        return tool_result
    return []


def compose(arguments, tooluniverse, call_tool):
    """Discover and validate biomarkers for a specific disease condition"""

    disease_condition = arguments["disease_condition"]
    sample_type = arguments.get("sample_type", "blood")

    print("🔬 Biomarker Discovery Workflow")
    print(f"Disease: {disease_condition}")
    print(f"Sample Type: {sample_type}")
    print("=" * 50)

    results = {}

    # Step 1: Literature-based biomarker discovery
    print("Step 1: Literature-based biomarker discovery...")
    try:
        literature_biomarkers = call_tool(
            "LiteratureSearchTool",
            {"research_topic": f"{disease_condition} biomarkers {sample_type}"},
        )
        results["literature_evidence"] = literature_biomarkers
        print("✅ Literature analysis completed")
    except Exception as e:
        print(f"⚠️ Literature search failed: {e}")
        results["literature_evidence"] = {"error": str(e)}

    # Step 2: Database mining for expression data
    print("Step 2: Database mining for expression data...")
    try:
        # Try multiple gene search strategies
        gene_search_results = []

        # Strategy 1: Direct disease name search
        try:
            hpa_result = call_tool(
                "HPA_search_genes_by_query", {"search_query": disease_condition}
            )
            genes = _extract_genes(hpa_result)
            if genes:
                gene_search_results.extend(genes)
                print(
                    f"✅ HPA search found {len(genes)} genes for '{disease_condition}'"
                )
        except Exception as e:
            print(f"⚠️ HPA search failed: {e}")

        # Strategy 2: Search for common biomarker genes if no results
        if not gene_search_results:
            biomarker_keywords = ["biomarker", "marker", "indicator", "diagnostic"]
            for keyword in biomarker_keywords:
                try:
                    search_term = f"{disease_condition} {keyword}"
                    hpa_result = call_tool(
                        "HPA_search_genes_by_query", {"search_query": search_term}
                    )
                    genes = _extract_genes(hpa_result)
                    if genes:
                        gene_search_results.extend(genes)
                        print(
                            f"✅ HPA search found {len(genes)} genes for '{search_term}'"
                        )
                        break
                except Exception as e:
                    print(f"⚠️ HPA search failed for '{search_term}': {e}")

        # NOTE: this used to silently substitute a hardcoded list of
        # generic cancer genes (BRCA1/BRCA2/TP53/EGFR/MYC) here and print a
        # "✅" success line whenever HPA search found nothing -- for a
        # disease with no matches (e.g. "healthy aging", which isn't a
        # disease HPA indexes genes against), that meant every downstream
        # step silently analyzed unrelated cancer genes while every log
        # line still claimed success. Report the miss honestly instead so
        # callers can tell "no data for this query" apart from "found
        # data."
        if not gene_search_results:
            print(
                "⚠️ No genes found with HPA search strategies for "
                f"'{disease_condition}' -- skipping expression/pathway "
                "steps that depend on a specific gene."
            )

        if gene_search_results:
            # Get details for the first gene found
            first_gene = gene_search_results[0]
            if "ensembl_id" in first_gene and first_gene["ensembl_id"] != "unknown":
                expression_data = call_tool(
                    "HPA_get_comprehensive_gene_details_by_ensembl_id",
                    {"ensembl_id": first_gene["ensembl_id"]},
                )
                results["expression_data"] = {
                    "search_query": disease_condition,
                    "genes_found": len(gene_search_results),
                    "search_strategy": "multi-strategy",
                    "gene_details": expression_data,
                    "all_candidates": gene_search_results,
                }
                print(
                    f"✅ Expression data retrieved for {first_gene.get('gene_name', 'unknown gene')}"
                )
            else:
                results["expression_data"] = {
                    "search_query": disease_condition,
                    "genes_found": len(gene_search_results),
                    "search_strategy": "multi-strategy",
                    "gene_details": first_gene,
                    "all_candidates": gene_search_results,
                }
                print("✅ Expression data retrieved using fallback strategy")
        else:
            results["expression_data"] = {
                "error": "No genes found with any search strategy"
            }
            print("⚠️ No genes found with any search strategy")
    except Exception as e:
        print(f"⚠️ Expression data search failed: {e}")
        results["expression_data"] = {"error": str(e)}

    # Step 3: Pathway enrichment analysis
    print("Step 3: Pathway enrichment analysis...")
    try:
        # Use genes found in step 2 for pathway analysis
        pathway_data = {}

        if (
            "expression_data" in results
            and "gene_details" in results["expression_data"]
        ):
            # Extract gene name from the gene details
            gene_details = results["expression_data"]["gene_details"]
            if "gene_name" in gene_details:
                gene_name = gene_details["gene_name"]

                # Multi-tool pathway analysis using available HPA tools
                pathway_results = {}

                # Tool 1: HPA biological processes
                try:
                    hpa_processes = call_tool(
                        "HPA_get_biological_processes_by_gene", {"gene": gene_name}
                    )
                    pathway_results["hpa_biological_processes"] = hpa_processes
                    print(f"✅ HPA biological processes completed for {gene_name}")
                except Exception as e:
                    pathway_results["hpa_biological_processes"] = {"error": str(e)}
                    print(f"⚠️ HPA biological processes failed for {gene_name}: {e}")

                # Tool 2: HPA contextual biological process analysis
                try:
                    contextual_analysis = call_tool(
                        "HPA_get_contextual_biological_process_analysis",
                        {"gene": gene_name},
                    )
                    pathway_results["hpa_contextual_analysis"] = contextual_analysis
                    print(f"✅ HPA contextual analysis completed for {gene_name}")
                except Exception as e:
                    pathway_results["hpa_contextual_analysis"] = {"error": str(e)}
                    print(f"⚠️ HPA contextual analysis failed for {gene_name}: {e}")

                # Tool 3: HPA protein interactions
                try:
                    protein_interactions = call_tool(
                        "HPA_get_protein_interactions_by_gene", {"gene": gene_name}
                    )
                    pathway_results["hpa_protein_interactions"] = protein_interactions
                    print(f"✅ HPA protein interactions completed for {gene_name}")
                except Exception as e:
                    pathway_results["hpa_protein_interactions"] = {"error": str(e)}
                    print(f"⚠️ HPA protein interactions failed for {gene_name}: {e}")

                # Tool 4: HPA cancer prognostics (if relevant)
                try:
                    cancer_prognostics = call_tool(
                        "HPA_get_cancer_prognostics_by_gene", {"gene": gene_name}
                    )
                    pathway_results["hpa_cancer_prognostics"] = cancer_prognostics
                    print(f"✅ HPA cancer prognostics completed for {gene_name}")
                except Exception as e:
                    pathway_results["hpa_cancer_prognostics"] = {"error": str(e)}
                    print(f"⚠️ HPA cancer prognostics failed for {gene_name}: {e}")

                pathway_data[gene_name] = pathway_results
            else:
                pathway_data["error"] = "No gene name available for pathway analysis"
                print("⚠️ No gene name available for pathway analysis")
        else:
            # Fallback: use disease condition for pathway search
            try:
                processes = call_tool(
                    "HPA_get_biological_processes_by_gene", {"gene": disease_condition}
                )
                pathway_data[disease_condition] = {
                    "hpa_biological_processes": processes,
                    "note": "Fallback analysis using disease condition",
                }
                print("✅ Pathway analysis completed using disease condition")
            except Exception as e:
                pathway_data["error"] = str(e)
                print(f"⚠️ Pathway analysis failed: {e}")

        results["pathway_analysis"] = pathway_data
    except Exception as e:
        print(f"⚠️ Pathway analysis failed: {e}")
        results["pathway_analysis"] = {"error": str(e)}

    # Step 4: Clinical validation search
    print("Step 4: Clinical validation search...")
    try:
        # Use FDA drug names instead
        clinical_evidence = call_tool(
            "FDA_get_drug_names_by_clinical_pharmacology",
            {"clinical_pharmacology": disease_condition},
        )
        results["clinical_validation"] = clinical_evidence
        print("✅ Clinical validation search completed")
    except Exception as e:
        print(f"⚠️ Clinical validation search failed: {e}")
        results["clinical_validation"] = {"error": str(e)}

    # Step 5: Additional protein information
    print("Step 5: Protein information gathering...")
    protein_info = {}

    # Use genes found in step 2 for protein information
    if "expression_data" in results and "gene_details" in results["expression_data"]:
        gene_details = results["expression_data"]["gene_details"]
        if "gene_name" in gene_details and "ensembl_id" in gene_details:
            gene_name = gene_details["gene_name"]
            gene_details["ensembl_id"]
            try:
                # Get comprehensive gene details (already retrieved in step 2)
                protein_info[gene_name] = gene_details
                print(f"✅ Protein information gathered for {gene_name}")
            except Exception as e:
                print(f"⚠️ Protein info failed for {gene_name}: {e}")
                protein_info[gene_name] = {"error": str(e)}
        else:
            protein_info["error"] = "No gene name or Ensembl ID available"
            print("⚠️ No gene name or Ensembl ID available")
    else:
        protein_info["error"] = "No gene data available from expression analysis"
        print("⚠️ No gene data available from expression analysis")

    results["protein_information"] = protein_info
    print(f"✅ Protein information gathered for {len(protein_info)} genes")

    return {
        "disease": disease_condition,
        "sample_type": sample_type,
        "literature_evidence": results["literature_evidence"],
        "expression_data": results["expression_data"],
        "pathway_analysis": results["pathway_analysis"],
        "clinical_validation": results["clinical_validation"],
        "protein_information": results["protein_information"],
    }
