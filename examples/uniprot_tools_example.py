#!/usr/bin/env python3
"""
UniProt Tools Comprehensive Example

Demonstrates ALL UniProt tools available in ToolUniverse, including:
- Basic retrieval by accession (original 10 tools)
- New search functionality (UniProt_search)
- New ID mapping functionality (UniProt_id_mapping)

This example shows complete workflows from gene names to protein data.
"""

from tooluniverse import ToolUniverse

# =============================================================================
# Tool Initialization
# =============================================================================
print("Initializing ToolUniverse...")
tu = ToolUniverse()
tu.load_tools()
print("✅ ToolUniverse loaded successfully\n")

result1 = tu.run({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {
        "accession": "Q6ZNX1",
    }
})
print(result1)
exit()
# =============================================================================
# PART 1: Search Functionality (NEW)
# =============================================================================
print("=" * 80)
print("PART 1: Search Functionality - Finding proteins by name")
print("=" * 80)

# Example 1: Search by gene name
print("\n1.1 Searching for MEIOB gene in humans...")
result1 = tu.run({
    "name": "UniProt_search",
    "arguments": {
        "query": "gene:MEIOB",
        "organism": "human",
        "limit": 3
    }
})

if "results" in result1 and len(result1["results"]) > 0:
    protein = result1["results"][0]
    print(f"   ✅ Found: {protein['protein_name']}")
    print(f"   Accession: {protein['accession']}")
    print(f"   ID: {protein['id']}")
    print(f"   Gene names: {protein['gene_names']}")
    print(f"   Organism: {protein['organism']}")
    print(f"   Length: {protein['length']} residues")
    MEIOB_ACCESSION = protein['accession']
else:
    print("   ❌ No results found")
    MEIOB_ACCESSION = "Q5SWX9"  # Fallback for testing

# Example 2: Search by protein name
print("\n1.2 Searching for p53 protein...")
result2 = tu.run({
    "name": "UniProt_search",
    "arguments": {
        "query": 'protein_name:"tumor protein p53"',
        "organism": "human",
        "limit": 2
    }
})

if "results" in result2 and len(result2["results"]) > 0:
    p53 = result2["results"][0]
    print(f"   ✅ Found: {p53['protein_name']}")
    print(f"   Accession: {p53['accession']}")
    print(f"   Gene names: {p53['gene_names']}")
    TP53_ACCESSION = p53['accession']
else:
    print("   ❌ No results found")
    TP53_ACCESSION = "P04637"

# Example 3: Advanced search with multiple criteria
print("\n1.3 Advanced search: reviewed human proteins related to apoptosis...")
result3 = tu.run({
    "name": "UniProt_search",
    "arguments": {
        "query": "apoptosis AND reviewed:true",
        "organism": "human",
        "limit": 5
    }
})

if "results" in result3:
    print(f"   ✅ Found {result3['total_results']} proteins")
    print(f"   Showing first {result3['returned']} results:")
    for i, protein in enumerate(result3["results"][:3], 1):
        print(f"   {i}. {protein['protein_name']} ({protein['accession']})")

# =============================================================================
# PART 2: ID Mapping Functionality (NEW)
# =============================================================================
print("\n" + "=" * 80)
print("PART 2: ID Mapping - Converting between database identifiers")
print("=" * 80)

# Example 1: Map gene names to UniProt accessions
print("\n2.1 Mapping gene names to UniProt accessions...")
result4 = tu.run({
    "name": "UniProt_id_mapping",
    "arguments": {
        "ids": ["MEIOB", "TP53", "EGFR"],
        "from_db": "Gene_Name",
        "to_db": "UniProtKB"
    }
})

if "results" in result4:
    print(f"   ✅ Mapped {result4['mapped_count']} gene names")
    for mapping in result4["results"][:3]:
        print(f"   {mapping['from']} → {mapping['to']['accession']} "
              f"({mapping['to']['id']})")

# Example 2: Map Ensembl IDs to UniProt
print("\n2.2 Mapping Ensembl IDs to UniProt accessions...")
result5 = tu.run({
    "name": "UniProt_id_mapping",
    "arguments": {
        "ids": ["ENSG00000141510", "ENSG00000134057"],
        "from_db": "Ensembl",
        "to_db": "UniProtKB"
    }
})

if "results" in result5:
    print(f"   ✅ Mapped {result5['mapped_count']} Ensembl IDs")
    for mapping in result5["results"][:2]:
        print(f"   {mapping['from']} → {mapping['to']['accession']}")

# =============================================================================
# PART 3: Basic Retrieval Tools (Existing)
# =============================================================================
print("\n" + "=" * 80)
print("PART 3: Basic Retrieval Tools - Getting protein data by accession")
print("=" * 80)

# Use a known accession for demonstrations
TEST_ACCESSION = "P05067"  # Amyloid-beta precursor protein

# Example 1: Get complete entry
print("\n3.1 Getting complete protein entry...")
result6 = tu.run({
    "name": "UniProt_get_entry_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result6, dict) and "error" not in result6:
    print(f"   ✅ Retrieved entry: {result6.get('uniProtkbId', 'Unknown')}")
    print(f"   Name: {result6.get('proteinDescription', {})}")
else:
    print(f"   ⚠️  {result6.get('error', 'Unknown error')}")  # noqa: F541

# Example 2: Get function information
print("\n3.2 Getting function annotation...")
result7 = tu.run({
    "name": "UniProt_get_function_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result7, list) and len(result7) > 0:
    print(f"   ✅ Found {len(result7)} function descriptions")
    print(f"   First function: {result7[0][:100]}...")
elif isinstance(result7, str):
    print(f"   ✅ Function: {result7[:100]}...")  # noqa: F541
else:
    print("   ⚠️  No function data available")

# Example 3: Get protein names
print("\n3.3 Getting protein names...")
result8 = tu.run({
    "name": "UniProt_get_recommended_name_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result8, str):
    print(f"   ✅ Recommended name: {result8}")
    print("\n   Alternative names:")
    result9 = tu.run({
        "name": "UniProt_get_alternative_names_by_accession",
        "arguments": {"accession": TEST_ACCESSION}
    })
    if isinstance(result9, list):
        for alt_name in result9[:3]:
            print(f"   - {alt_name}")

# Example 4: Get organism information
print("\n3.4 Getting organism information...")
result10 = tu.run({
    "name": "UniProt_get_organism_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result10, str):
    print(f"   ✅ Organism: {result10}")

# Example 5: Get subcellular location
print("\n3.5 Getting subcellular location...")
result11 = tu.run({
    "name": "UniProt_get_subcellular_location_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result11, list) and len(result11) > 0:
    print(f"   ✅ Found {len(result11)} subcellular locations:")
    for location in result11[:3]:
        print(f"   - {location}")

# Example 6: Get sequence
print("\n3.6 Getting protein sequence...")
result12 = tu.run({
    "name": "UniProt_get_sequence_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result12, str):
    print(f"   ✅ Sequence length: {len(result12)} amino acids")
    print(f"   First 50 residues: {result12[:50]}...")

# Example 7: Get disease variants
print("\n3.7 Getting disease variants...")
result13 = tu.run({
    "name": "UniProt_get_disease_variants_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result13, list):
    print(f"   ✅ Found {len(result13)} disease variants")
    for variant in result13[:2]:
        location = variant.get('location', {})
        print(f"   Variant at {location.get('start')}-{location.get('end')}")

# Example 8: Get PTM and processing sites
print("\n3.8 Getting PTM and processing sites...")
result14 = tu.run({
    "name": "UniProt_get_ptm_processing_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result14, list):
    print(f"   ✅ Found {len(result14)} modification sites")

# Example 9: Get isoform IDs
print("\n3.9 Getting isoform IDs...")
result15 = tu.run({
    "name": "UniProt_get_isoform_ids_by_accession",
    "arguments": {"accession": TEST_ACCESSION}
})

if isinstance(result15, list) and len(result15) > 0:
    print(f"   ✅ Found {len(result15)} isoforms:")
    for isoform in result15[:3]:
        print(f"   - {isoform}")
else:
    print("   ℹ️  No isoforms found")

# =============================================================================
# PART 4: Complete Workflow Example
# =============================================================================
print("\n" + "=" * 80)
print("PART 4: Complete Workflow - From gene name to protein data")
print("=" * 80)

print("\n4.1 Complete workflow example:")
print("    Step 1: Search for BRCA1 gene")
print("    Step 2: Get UniProt accession")
print("    Step 3: Retrieve protein function")
print("    Step 4: Get sequence")

try:
    # Step 1: Search for gene
    workflow_result1 = tu.run({
        "name": "UniProt_search",
        "arguments": {
            "query": "gene:BRCA1",
            "organism": "human",
            "limit": 1
        }
    })

    if "results" in workflow_result1 and len(workflow_result1["results"]) > 0:
        brca1 = workflow_result1["results"][0]
        brca1_acc = brca1['accession']
        print("\n   Step 1: ✅ Found BRCA1")
        print(f"   Accession: {brca1_acc}")
        print(f"   Protein: {brca1['protein_name']}")

        # Step 2: Get function
        workflow_result2 = tu.run({
            "name": "UniProt_get_function_by_accession",
            "arguments": {"accession": brca1_acc}
        })
        print("\n   Step 2: ✅ Retrieved function")
        if isinstance(workflow_result2, list) and len(workflow_result2) > 0:
            print(f"   Function: {workflow_result2[0][:150]}...")

        # Step 3: Get sequence
        workflow_result3 = tu.run({
            "name": "UniProt_get_sequence_by_accession",
            "arguments": {"accession": brca1_acc}
        })
        print("\n   Step 3: ✅ Retrieved sequence")
        if isinstance(workflow_result3, str):
            print(f"   Length: {len(workflow_result3)} amino acids")

except Exception as e:
    print(f"   ⚠️  Workflow error: {e}")

# =============================================================================
# Helper Function for Result Formatting
# =============================================================================


def format_value(value, max_items=5, max_length=200):
    """Helper function to format output values with more detail"""
    if isinstance(value, dict):
        dict_str = str(value)
        return (
            f"Dict ({len(dict_str)} chars): "
            f"{dict_str[:500]}{'...' if len(dict_str) > 500 else ''}"
        )
    elif isinstance(value, list):
        if not value:
            return "Empty list"
        items_to_show = value[:max_items]
        items_str = "\n  - ".join(
            [
                str(item)[:max_length] + (
                    "..." if len(str(item)) > max_length else ""
                )
                for item in items_to_show
            ]
        )
        remaining = len(value) - max_items
        return f"List with {len(value)} items:\n  - {items_str}" + (
            f"\n  ... and {remaining} more items" if remaining > 0 else ""
        )
    elif isinstance(value, str):
        return (
            f"String ({len(value)} chars): "
            f"{value[:max_length]}{'...' if len(value) > max_length else ''}"
        )
    else:
        return f"Type: {type(value)}, Value: {value}"


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nAll UniProt tools demonstrated:")
print("\n✅ Search Tools (NEW):")
print("   - UniProt_search: Find proteins by gene name, protein name, etc.")
print("   - UniProt_id_mapping: Convert between database identifiers")

print("\n✅ Basic Retrieval Tools (12 tools):")
print("   - UniProt_get_entry_by_accession: Complete entry")
print("   - UniProt_get_function_by_accession: Function annotation")
print("   - UniProt_get_recommended_name_by_accession: Protein name")
print("   - UniProt_get_alternative_names_by_accession: Alternative names")
print("   - UniProt_get_organism_by_accession: Organism info")
print("   - UniProt_get_subcellular_location_by_accession: Subcellular loc")
print("   - UniProt_get_disease_variants_by_accession: Disease variants")
print("   - UniProt_get_ptm_processing_by_accession: PTM sites")
print("   - UniProt_get_sequence_by_accession: Protein sequence")
print("   - UniProt_get_isoform_ids_by_accession: Isoform IDs")

print("\nUsage patterns:")
print("   1. Search: Use UniProt_search to find accessions by name")
print("   2. Map IDs: Use UniProt_id_mapping to convert identifiers")
print("   3. Get data: Use *_by_accession tools for detailed information")

print("\n🎉 Example completed successfully!")
