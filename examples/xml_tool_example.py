from tooluniverse import ToolUniverse
import json
import time

# Step 1: Initialize tool universe
tooluni = ToolUniverse()
tooluni.load_tools()

# Test queries for XML tools using MedlinePlus health topics data (reduced limits for faster testing)
test_queries = [
    {
        "name": "mesh_get_subjects_by_pharmacological_action",
        "arguments": {"query": "calcium", "limit": 3},
    },
    {
        "name": "mesh_get_subjects_by_subject_scope_or_definition",
        "arguments": {"query": "glycan", "limit": 2},
    },
    {
        "name": "mesh_get_subjects_by_subject_name",
        "arguments": {
            "query": "antibody",
            "limit": 3,
        },
    },
    {
        "name": "mesh_get_subjects_by_subject_id",
        "arguments": {
            "query": "D007306",
            "limit": 2,
        },
    },
    {
        "name": "drugbank_get_drug_basic_info_by_drug_name_or_drugbank_id",
        "arguments": {"query": "lovastatin", "limit": 2},
    },
    {
        "name": "drugbank_get_indications_by_drug_name_or_drugbank_id",
        "arguments": {"query": "DB00945", "limit": 5},
    },
    {
        "name": "drugbank_get_drug_name_and_description_by_indication",
        "arguments": {"query": "hypertension", "limit": 1},
    },
    {
        "name": "drugbank_get_pharmacology_by_drug_name_or_drugbank_id",
        "arguments": {"query": "lovastatin", "limit": 1},
    },
    {
        "name": "drugbank_get_pharmacology_by_drug_name_or_drugbank_id",
        "arguments": {"query": "simvastatin", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_desc_pharmacology_by_moa",
        "arguments": {"query": "receptor antagonist", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_interactions_by_drug_name_or_drugbank_id",
        "arguments": {"query": "carbidopa", "limit": 1},
    },
    {
        "name": "drugbank_get_targets_by_drug_name_or_drugbank_id",
        "arguments": {"query": "aspirin", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_name_and_description_by_target_name",
        "arguments": {"query": "dopamine receptor", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_products_by_name_or_drugbank_id",
        "arguments": {"query": "ibuprofen", "limit": 1},
    },
    {
        "name": "drugbank_get_safety_by_drug_name_or_drugbank_id",
        "arguments": {"query": "lovastatin", "limit": 2},
    },
    {
        "name": "drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id",
        "arguments": {"query": "caffeine", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_references_by_drug_name_or_drugbank_id",
        "arguments": {"query": "aspirin", "limit": 1},
    },
    {
        "name": "drugbank_get_pathways_reactions_by_drug_or_id",
        "arguments": {"query": "glucose", "limit": 1},
    },
    {
        "name": "drugbank_get_drug_name_and_description_by_pathway_name",
        "arguments": {"query": "glycolysis", "limit": 1},
    },
    {
        "name": "drugbank_filter_drugs_by_name",
        "arguments": {
            "condition": "ends_with",
            "value": "cillin",  # Example: find drugs whose names end with 'cillin', pencillin antibiotics
            "limit": 1,
        },
    },
]

test_queries = test_queries

# Run all test queries (with timeout and error handling)
for idx, query in enumerate(test_queries):
    print(f"\n[{idx+1}] Running tool: {query['name']}")
    print(f"Arguments: {query['arguments']}")
    print("-" * 60)

    try:
        start_time = time.time()
        result = tooluni.run(query)
        end_time = time.time()
        
        print(f"✅ Success! (took {end_time - start_time:.2f}s)")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Skipping to next query...")
        continue
