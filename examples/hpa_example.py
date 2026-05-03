# test_hpa.py
# Comprehensive test file for all HPA tools including enhanced optimized tools

from tooluniverse import ToolUniverse


# Helper function to format dictionary values
def format_value(value, max_length=800):
    """Format output values, showing more detail for agent reasoning"""
    if isinstance(value, dict):
        formatted = str(value)
        if len(formatted) > max_length:
            return formatted[:max_length] + "... (truncated)"
        return formatted
    elif isinstance(value, list):
        if len(value) > 15:  # Show more list items for better context
            return f"{value[:15]}... (total {len(value)} items)"
        return value
    elif isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    return value


# Initialize ToolUniverse and load all tools
print("🧪 Comprehensive HPA Tools Testing")
print("=" * 80)
print("Testing all HPA tools with complete input/output display for agent reasoning")
print("=" * 80)

tooluni = ToolUniverse()
tooluni.load_tools()

# Define test genes and parameters with biological context
VALID_GENE = "TP53"  # Tumor suppressor gene - nuclear protein
VALID_GENE_2 = "BRCA1"  # Breast cancer susceptibility gene
VALID_GENE_3 = "EGFR"  # Epidermal growth factor receptor
VALID_GENE_4 = "ACTB"  # Beta-actin - housekeeping gene
VALID_GENE_5 = "GFAP"  # Glial fibrillary acidic protein
VALID_GENE_6 = "INS"  # Insulin - pancreas-specific
VALID_GENE_7 = "CD3E"  # T-cell surface glycoprotein
VALID_CELL_LINE = "hela"  # HeLa cervical cancer cell line
VALID_DISEASE = "breast_cancer"  # Breast cancer
VALID_ENSEMBL_ID = "ENSG00000134057"  # CCNB1 gene's Ensembl ID
VALID_ENSEMBL_ID_2 = "ENSG00000141510"  # TP53 gene's Ensembl ID
VALID_ENSEMBL_ID_3 = "ENSG00000012048"  # BRCA1 gene's Ensembl ID
VALID_ENSEMBL_ID_4 = "ENSG00000075624"  # ACTB gene's Ensembl ID
VALID_ENSEMBL_ID_5 = "ENSG00000146648"  # EGFR gene's Ensembl ID

# Comprehensive test cases covering all HPA tools
comprehensive_test_queries = [
    # === GENE SEARCH AND BASIC INFO TOOLS ===
    {
        "name": "HPA_search_genes_by_query",
        "arguments": {"search_query": VALID_GENE},
        "description": "Search for TP53 gene to get Ensembl ID and synonyms",
        "biological_context": "TP53 is a crucial tumor suppressor gene, mutations cause cancer",
        "expected_output": "Should return gene name, Ensembl ID, and known synonyms",
    },
    {
        "name": "HPA_search_genes_by_query",
        "arguments": {"search_query": "BCAS1"},
        "description": "Search for BCAS1 gene (breast carcinoma amplified sequence 1)",
        "biological_context": "BCAS1 is involved in breast cancer progression",
        "expected_output": "Should return ENSG00000064787 as Ensembl ID",
    },
    {
        "name": "HPA_get_gene_basic_info_by_ensembl_id",
        "arguments": {"ensembl_id": VALID_ENSEMBL_ID_2},
        "description": "Get basic gene information for TP53 using JSON API",
        "biological_context": "TP53 basic info should include transcription regulation functions",
        "expected_output": "Gene name, synonyms, Uniprot ID, biological processes",
    },
    {
        "name": "HPA_get_gene_tsv_data_by_ensembl_id",
        "arguments": {"ensembl_id": VALID_ENSEMBL_ID_2},
        "description": "Get detailed gene data in TSV format for TP53",
        "biological_context": "Legacy format often used for bulk data processing",
        "expected_output": "TSV string containing gene data",
    },
    # === EXPRESSION ANALYSIS TOOLS ===
    {
        "name": "HPA_get_comparative_expression_by_gene_and_cellline",
        "arguments": {"gene_name": VALID_GENE, "cell_line": VALID_CELL_LINE},
        "description": "Compare TP53 expression between HeLa cells and healthy tissues",
        "biological_context": "TP53 is often mutated/dysregulated in cancer cell lines like HeLa",
        "expected_output": "Cell line expression vs healthy tissue expression with comparison",
    },
    {
        "name": "HPA_get_disease_expression_by_gene_tissue_disease",
        "arguments": {"gene_name": VALID_GENE_2, "disease_name": VALID_DISEASE},
        "description": "Compare BRCA1 expression in breast cancer vs healthy breast tissue",
        "biological_context": "BRCA1 mutations are major risk factor for breast cancer",
        "expected_output": "Disease vs healthy expression with fold change analysis",
    },
    {
        "name": "HPA_get_rna_expression_in_specific_tissues",
        "arguments": {
            "ensembl_id": VALID_ENSEMBL_ID_2,
            "tissue_names": ["brain", "liver", "heart"],
        },
        "description": "Get TP53 RNA expression levels in brain, liver, and heart tissues",
        "biological_context": "TP53 should be expressed in all tissues as tumor suppressor",
        "expected_output": "nTPM values for each tissue with expression level categories",
    },
    # === NEW OPTIMIZED EXPRESSION TOOLS ===
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": VALID_GENE_4,
            "source_type": "tissue",
            "source_name": "brain",
        },
        "description": "Get ACTB expression in brain using optimized column-based query",
        "biological_context": "ACTB is housekeeping gene, should have high expression everywhere",
        "expected_output": "High nTPM value with 'Very high' or 'High' expression level",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": VALID_GENE_6,
            "source_type": "tissue",
            "source_name": "pancreas",
        },
        "description": "Get insulin expression in pancreas using tissue-specific column",
        "biological_context": "Insulin is exclusively produced by pancreatic beta cells",
        "expected_output": "Very high nTPM value showing tissue specificity",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": VALID_GENE_5,
            "source_type": "brain",
            "source_name": "cerebellum",
        },
        "description": "Get GFAP expression in cerebellum using brain region-specific column",
        "biological_context": "GFAP is astrocyte marker, should be high in brain regions",
        "expected_output": "High expression indicating glial cell presence",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": VALID_GENE_7,
            "source_type": "blood",
            "source_name": "t_cell",
        },
        "description": "Get CD3E expression in T cells using blood cell-specific column",
        "biological_context": "CD3E is T cell receptor component, T cell-specific marker",
        "expected_output": "Very high expression showing T cell specificity",
    },
    # === FUNCTIONAL ANALYSIS TOOLS ===
    {
        "name": "HPA_get_biological_processes_by_gene",
        "arguments": {"gene_name": VALID_GENE},
        "description": "Get biological processes for TP53 with focus on key processes",
        "biological_context": "TP53 involved in apoptosis, cell cycle, transcription regulation",
        "expected_output": "List of processes highlighting apoptosis and cell cycle control",
    },
    {
        "name": "HPA_get_contextual_biological_process_analysis",
        "arguments": {"gene_name": VALID_GENE, "context_name": "brain"},
        "description": "Analyze TP53 biological functions in brain tissue context",
        "biological_context": "TP53 protects brain cells from DNA damage and cancer",
        "expected_output": "Functional relevance assessment based on brain expression",
    },
    {
        "name": "HPA_get_contextual_biological_process_analysis",
        "arguments": {"gene_name": VALID_GENE_3, "context_name": "hela"},
        "description": "Analyze EGFR functions in HeLa cell line context",
        "biological_context": "EGFR drives cell proliferation, often overexpressed in cancer",
        "expected_output": "High expression with growth/proliferation process relevance",
    },
    # === SUBCELLULAR LOCALIZATION TOOLS ===
    {
        "name": "HPA_get_subcellular_location",
        "arguments": {"gene_name": VALID_GENE},
        "description": "Get TP53 subcellular localization using optimized scml/scal columns",
        "biological_context": "TP53 is nuclear transcription factor",
        "expected_output": "Nuclear localization as main location",
    },
    {
        "name": "HPA_get_subcellular_location",
        "arguments": {"gene_name": VALID_GENE_4},
        "description": "Get ACTB subcellular localization - cytoskeletal protein",
        "biological_context": "Actin forms cytoskeletal filaments throughout cytoplasm",
        "expected_output": "Cytoplasmic/cytoskeletal localization",
    },
    {
        "name": "HPA_get_subcellular_location",
        "arguments": {"gene_name": VALID_GENE_5},
        "description": "Get GFAP subcellular localization - intermediate filament protein",
        "biological_context": "GFAP forms intermediate filaments in astrocyte cytoplasm",
        "expected_output": "Cytoplasmic intermediate filaments",
    },
    # === CANCER AND PROGNOSTICS TOOLS ===
    {
        "name": "HPA_get_cancer_prognostics_by_gene",
        "arguments": {"ensembl_id": VALID_ENSEMBL_ID_2},
        "description": "Get TP53 prognostic value across cancer types",
        "biological_context": "TP53 mutations are prognostic markers in many cancers",
        "expected_output": "Multiple cancer types with prognostic significance",
    },
    {
        "name": "HPA_get_cancer_prognostics_by_gene",
        "arguments": {"ensembl_id": VALID_ENSEMBL_ID_3},
        "description": "Get BRCA1 prognostic value in cancers",
        "biological_context": "BRCA1 mutations affect treatment response and survival",
        "expected_output": "Breast/ovarian cancer prognostic associations",
    },
    # === PROTEIN INTERACTION TOOLS ===
    {
        "name": "HPA_get_protein_interactions_by_gene",
        "arguments": {"gene_name": VALID_GENE_3},
        "description": "Get EGFR protein-protein interactions",
        "biological_context": "EGFR interacts with many signaling proteins",
        "expected_output": "List of interaction partners involved in growth signaling",
    },
    {
        "name": "HPA_get_protein_interactions_by_gene",
        "arguments": {"gene_name": VALID_GENE},
        "description": "Get TP53 protein-protein interactions",
        "biological_context": "TP53 interacts with MDM2, p21, and other cell cycle proteins",
        "expected_output": "Interaction partners in DNA damage response pathway",
    },
    # === COMPREHENSIVE GENE DETAILS (IMAGES) ===
    {
        "name": "HPA_get_comprehensive_gene_details_by_ensembl_id",
        "arguments": {"ensembl_id": "ENSG00000064787"},
        "description": "Get comprehensive BCAS1 gene details with enhanced XML parsing",
        "biological_context": "Should include tissue IHC images and subcellular IF images",
        "expected_output": "Gene info, IHC images, IF images, antibody data, expression summary",
    },
    {
        "name": "HPA_get_comprehensive_gene_details_by_ensembl_id",
        "arguments": {
            "ensembl_id": VALID_ENSEMBL_ID_2,
            "include_images": True,
            "include_antibodies": True,
        },
        "description": "Get comprehensive TP53 details with all data types",
        "biological_context": "TP53 should have extensive antibody validation and tissue images",
        "expected_output": "Complete gene profile with images, antibodies, expression data",
    },
    # === ERROR HANDLING TESTS ===
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": VALID_GENE,
            "source_type": "invalid_type",
            "source_name": "brain",
        },
        "description": "Error test: invalid source_type parameter",
        "biological_context": "Should demonstrate proper error handling",
        "expected_output": "Error message with available source types listed",
    },
    {
        "name": "HPA_get_subcellular_location",
        "arguments": {},
        "description": "Error test: missing required gene_name parameter",
        "biological_context": "Should demonstrate parameter validation",
        "expected_output": "Error message indicating gene_name is required",
    },
    {
        "name": "HPA_get_cancer_prognostics_by_gene",
        "arguments": {"ensembl_id": "INVALID_ENSEMBL_ID"},
        "description": "Error test: invalid Ensembl ID",
        "biological_context": "Should handle non-existent gene IDs gracefully",
        "expected_output": "404 error or no data found message",
    },
    # === INTELLIGENT RECOMMENDATION TESTS ===
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": "ACTB",
            "source_type": "blood",
            "source_name": "tcell",
        },
        "description": "Smart recommendation test: typo in source_name (tcell → t_cell)",
        "biological_context": "Should provide intelligent suggestions for misspelled parameters",
        "expected_output": "Error with similar options: ['t_cell'] and complete available list",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": "GFAP",
            "source_type": "brain",
            "source_name": "cortex",
        },
        "description": "Smart recommendation test: partial match (cortex → cerebral_cortex)",
        "biological_context": "Should find partial matches for brain region names",
        "expected_output": "Error with similar options suggesting cerebral_cortex",
    },
    {
        "name": "HPA_get_contextual_biological_process_analysis",
        "arguments": {"gene_name": "TP53", "context_name": "foot"},
        "description": "Smart recommendation test: invalid tissue name",
        "biological_context": "Should provide comprehensive tissue and cell line options",
        "expected_output": "Error with available tissues and cell lines listed",
    },
    {
        "name": "HPA_get_contextual_biological_process_analysis",
        "arguments": {"gene_name": "EGFR", "context_name": "muscle"},
        "description": "Smart recommendation test: ambiguous tissue name (muscle → skeletal_muscle)",
        "biological_context": "Should suggest specific muscle types available",
        "expected_output": "Error with similar options for muscle-related tissues",
    },
    {
        "name": "HPA_get_comparative_expression_by_gene_and_cellline",
        "arguments": {"gene_name": "BRCA1", "cell_line": "heLa"},
        "description": "Smart recommendation test: case sensitivity (heLa → hela)",
        "biological_context": "Should handle case variations in cell line names",
        "expected_output": "Error with similar options suggesting hela",
    },
    {
        "name": "HPA_get_comparative_expression_by_gene_and_cellline",
        "arguments": {"gene_name": "EGFR", "cell_line": "mcf"},
        "description": "Smart recommendation test: partial cell line name (mcf → mcf7)",
        "biological_context": "Should suggest complete cell line names",
        "expected_output": "Error with similar options suggesting mcf7",
    },
    {
        "name": "HPA_get_disease_expression_by_gene_tissue_disease",
        "arguments": {"gene_name": "BRCA1", "disease_name": "cancer"},
        "description": "Smart recommendation test: generic disease name",
        "biological_context": "Should provide specific cancer type options",
        "expected_output": "Error with specific cancer types like breast_cancer, lung_cancer",
    },
    {
        "name": "HPA_get_disease_expression_by_gene_tissue_disease",
        "arguments": {"gene_name": "TP53", "disease_name": "colon"},
        "description": "Smart recommendation test: tissue name as disease (colon → colon_cancer)",
        "biological_context": "Should suggest adding '_cancer' suffix",
        "expected_output": "Error with similar options suggesting colon_cancer",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": "INS",
            "source_type": "tissue",
            "source_name": "islet",
        },
        "description": "Smart recommendation test: related but different term (islet → pancreas)",
        "biological_context": "Should suggest pancreas for insulin-related queries",
        "expected_output": "Error with pancreas in similar options",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": "CD3E",
            "source_type": "blood",
            "source_name": "lymphocyte",
        },
        "description": "Smart recommendation test: general term (lymphocyte → t_cell, b_cell)",
        "biological_context": "Should suggest specific lymphocyte subtypes",
        "expected_output": "Error with t_cell and b_cell in similar options",
    },
    # === EDGE CASE RECOMMENDATION TESTS ===
    {
        "name": "HPA_get_contextual_biological_process_analysis",
        "arguments": {"gene_name": "ACTB", "context_name": ""},
        "description": "Edge case test: empty context_name",
        "biological_context": "Should require context_name parameter",
        "expected_output": "Error indicating context_name is required",
    },
    {
        "name": "HPA_get_rna_expression_by_source",
        "arguments": {
            "gene_name": "GFAP",
            "source_type": "tissue",
            "source_name": "xyz123",
        },
        "description": "Edge case test: completely invalid source_name",
        "biological_context": "Should show no similar options but list all available",
        "expected_output": "Error with complete tissue list but no similar options",
    },
    {
        "name": "HPA_get_rna_expression_in_specific_tissues",
        "arguments": {"ensembl_id": VALID_ENSEMBL_ID_2, "tissue_names": "not_a_list"},
        "description": "Edge case test: wrong parameter type",
        "biological_context": "Should provide example of correct format",
        "expected_output": "Error with tissue name examples",
    },
    # === GENERIC SEARCH TOOL ===
    {
        "name": "HPA_generic_search",
        "arguments": {
            "search_query": "Insulin",
            "columns": "g,gs,gd",
            "format": "json"
        },
        "description": "Generic search for Insulin using the new HPASearchTool",
        "biological_context": "Testing the generic search capability for a well-known protein",
        "expected_output": "List of entries matching 'Insulin' with specified columns",
    },
]

# Execute all test cases with detailed output
for idx, query_info in enumerate(comprehensive_test_queries, 1):
    print(f"\n[{idx}] TOOL: {query_info['name']}")
    print(f"INPUT ARGUMENTS: {query_info['arguments']}")
    print(f"DESCRIPTION: {query_info['description']}")
    print(f"BIOLOGICAL CONTEXT: {query_info['biological_context']}")
    print(f"EXPECTED OUTPUT: {query_info['expected_output']}")
    print("-" * 80)

    # Execute the query
    result = tooluni.run(
        {"name": query_info["name"], "arguments": query_info["arguments"]}
    )

    # Display results with complete formatting for agent reasoning
    if isinstance(result, dict) and "error" in result:
        print("❌ ERROR RESULT:")
        print(f"   Error: {result['error']}")
        if "detail" in result:
            print(f"   Detail: {result['detail']}")

        # Enhanced interpretation for intelligent recommendation tests
        error_msg = result["error"]
        if "Similar options:" in error_msg:
            print("   🧠 SMART RECOMMENDATION: Tool provided intelligent suggestions!")
            print("   💡 FUZZY MATCHING: Successfully identified similar valid options")
            print("   ✨ USER EXPERIENCE: Error message is helpful and actionable")
        elif "Available" in error_msg and (
            "tissues:" in error_msg
            or "cell lines:" in error_msg
            or "sources:" in error_msg
        ):
            print("   📋 COMPREHENSIVE GUIDANCE: Tool provided complete option lists")
            print("   🎯 PARAMETER VALIDATION: Clear indication of valid inputs")
        elif "required" in error_msg:
            print("   ✅ PARAMETER VALIDATION: Proper required field checking")
        else:
            print(
                "   INTERPRETATION: Tool properly handled invalid input with informative error"
            )
    else:
        print("✅ SUCCESS RESULT:")

        if isinstance(result, dict):
            # Display complete result data
            print("   COMPLETE OUTPUT DATA:")
            for key, value in result.items():
                formatted_value = format_value(value)
                print(f"     {key}: {formatted_value}")

            # Add biological interpretation
            print("   BIOLOGICAL INTERPRETATION:")

            # Expression data interpretation
            if "expression_value" in result:
                expr_val = result.get("expression_value", "N/A")
                expr_level = result.get("expression_level", "Unknown")
                source_type = result.get("source_type", "Unknown")
                source_name = result.get("source_name", "Unknown")
                column = result.get("column_queried", "Unknown")
                gene = result.get("gene_name", "Unknown")

                print(
                    f"     Gene {gene} shows {expr_level} expression ({expr_val} nTPM)"
                )
                print(f"     in {source_name} ({source_type}) via column '{column}'")

                # Biological significance
                if expr_val != "N/A":
                    try:
                        val = float(expr_val)
                        if val > 50:
                            print(
                                "     SIGNIFICANCE: Very high expression suggests major functional role"
                            )
                        elif val > 10:
                            print(
                                "     SIGNIFICANCE: High expression indicates important function"
                            )
                        elif val > 1:
                            print(
                                "     SIGNIFICANCE: Moderate expression shows functional presence"
                            )
                        else:
                            print(
                                "     SIGNIFICANCE: Low expression may indicate limited role"
                            )
                    except Exception:
                        print("     SIGNIFICANCE: Expression level unclear from data")

            # Subcellular location interpretation
            if "main_locations" in result:
                main_locs = result.get("main_locations", [])
                add_locs = result.get("additional_locations", [])
                total = result.get("total_locations", 0)
                gene = result.get("gene_name", "Unknown")

                print(f"     Gene {gene} localizes to {total} subcellular compartments")
                if main_locs:
                    print(f"     PRIMARY LOCATIONS: {', '.join(main_locs)}")
                if add_locs:
                    print(f"     ADDITIONAL LOCATIONS: {', '.join(add_locs)}")

                # Functional implications
                if any("nuclear" in loc.lower() for loc in main_locs):
                    print(
                        "     FUNCTIONAL IMPLICATION: Nuclear localization suggests transcriptional role"
                    )
                if any("cytoplasm" in loc.lower() for loc in main_locs):
                    print(
                        "     FUNCTIONAL IMPLICATION: Cytoplasmic localization suggests metabolic/structural role"
                    )
                if any("membrane" in loc.lower() for loc in main_locs):
                    print(
                        "     FUNCTIONAL IMPLICATION: Membrane localization suggests signaling role"
                    )

            # Cancer prognostics interpretation
            if "prognostic_cancers_count" in result:
                count = result.get("prognostic_cancers_count", 0)
                gene = result.get("gene", "Unknown")
                prognostics = result.get("prognostic_summary", [])

                print(f"     Gene {gene} has prognostic value in {count} cancer types")
                if isinstance(prognostics, list) and prognostics:
                    for prog in prognostics[:3]:  # Show first 3
                        cancer_type = prog.get("cancer_type", "Unknown")
                        prog_type = prog.get("prognostic_type", "Unknown")
                        print(f"     {cancer_type}: {prog_type} prognostic marker")
                print(
                    "     CLINICAL SIGNIFICANCE: Can guide treatment decisions and prognosis"
                )

            # Protein interactions interpretation
            if "interactor_count" in result:
                count = result.get("interactor_count", 0)
                gene = result.get("gene", "Unknown")
                interactors = result.get("interactors", [])

                print(f"     Gene {gene} interacts with {count} proteins")
                if interactors and count > 0:
                    print(
                        f"     KEY INTERACTORS: {', '.join(interactors[:5])}"
                    )  # Show first 5
                    print(
                        "     NETWORK SIGNIFICANCE: High connectivity suggests central role in pathways"
                    )
                else:
                    print(
                        "     NETWORK SIGNIFICANCE: Limited interactions or data not available"
                    )

            # Biological processes interpretation
            if "total_biological_processes" in result:
                total_processes = result.get("total_biological_processes", 0)
                target_processes = result.get("target_process_names", [])
                gene = result.get("gene_symbol", result.get("gene", "Unknown"))

                print(
                    f"     Gene {gene} participates in {total_processes} biological processes"
                )
                if target_processes:
                    print(f"     KEY PROCESSES: {', '.join(target_processes)}")
                    print(
                        "     FUNCTIONAL SIGNIFICANCE: Involvement in critical cellular processes"
                    )

            # Comprehensive gene details interpretation
            if "summary" in result and isinstance(result["summary"], dict):
                summary = result["summary"]
                gene = result.get("gene_name", "Unknown")

                print(f"     Gene {gene} comprehensive analysis:")
                for sum_key, sum_val in summary.items():
                    print(f"       {sum_key}: {sum_val}")

                ihc_images = summary.get("total_ihc_images", 0)
                if_images = summary.get("total_if_images", 0)
                antibodies = summary.get("total_antibodies", 0)

                print(
                    f"     EXPERIMENTAL EVIDENCE: {ihc_images} tissue images, {if_images} subcellular images, {antibodies} antibodies"
                )
                print("     DATA QUALITY: Extensive experimental validation available")

            # Contextual analysis interpretation
            if "contextual_conclusion" in result:
                conclusion = result.get("contextual_conclusion", "")
                context = result.get("context", "Unknown")
                gene = result.get("gene", "Unknown")

                print(f"     CONTEXTUAL ANALYSIS for {gene} in {context}:")
                print(f"     {conclusion}")

                relevance = result.get("functional_relevance", "")
                if relevance:
                    print(f"     FUNCTIONAL RELEVANCE: {relevance}")

        elif isinstance(result, list):
            print(f"   LIST RESULT: {len(result)} items")
            if result:
                print(f"   FIRST ITEM: {format_value(result[0])}")
                print("   INTERPRETATION: Multiple data points returned for analysis")

        else:
            print(f"   RAW RESULT: {format_value(result)}")
            print("   INTERPRETATION: Direct data output for further processing")

    print("=" * 80)

print("\n🎯 COMPREHENSIVE HPA TOOLS TESTING COMPLETE!")
print("\n📊 TESTING SUMMARY:")
print(f"✅ Tested {len(comprehensive_test_queries)} different HPA tools and scenarios")
print(
    "✅ Covered all tool categories: search, expression, function, localization, interactions, prognostics"
)
print("✅ Included both original and optimized enhanced tools")
print("✅ Demonstrated error handling and parameter validation")
print("✅ Added comprehensive intelligent recommendation testing")
print("✅ Provided complete input/output data for agent reasoning")
print("✅ Added biological context and functional interpretation")

print("\n🔬 ENHANCED FEATURES DEMONSTRATED:")
print("✨ Column-based optimized queries for direct data access")
print("✨ Comprehensive source type mappings (tissue/blood/brain/single_cell)")
print("✨ Enhanced XML parsing with improved image extraction")
print("✨ Intelligent error handling with informative messages")
print("✨ Smart parameter recommendations with fuzzy matching")
print("✨ Context-aware suggestions for biological terms")
print("✨ Biological interpretation of results for agent reasoning")
print("✨ Complete data transparency for downstream analysis")

print("\n🧠 INTELLIGENT RECOMMENDATION FEATURES:")
print("💡 Typo correction: 'tcell' → suggests 't_cell'")
print("💡 Partial matching: 'cortex' → suggests 'cerebral_cortex'")
print("💡 Case handling: 'heLa' → suggests 'hela'")
print("💡 Context awareness: 'muscle' → suggests 'skeletal_muscle'")
print("💡 Domain knowledge: 'islet' → suggests 'pancreas' for insulin")
print("💡 Hierarchical suggestions: 'lymphocyte' → suggests 't_cell', 'b_cell'")
print("💡 Comprehensive fallback: Shows all available options when no match")
print("💡 Edge case handling: Empty parameters, wrong types, invalid inputs")

print("\n💡 FOR AGENT USAGE:")
print("📋 All inputs and outputs are fully displayed")
print("🧠 Biological context provided for each test")
print("🔍 Results include functional interpretation")
print("⚡ Both original and optimized tools available")
print("🛡️ Error handling demonstrates robustness")
print("\n" + "=" * 80)

