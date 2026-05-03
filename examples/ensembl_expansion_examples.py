"""
Ensembl REST API Expansion Examples
Demonstrates new comparative genomics, ontology, and VEP tools
"""

from tooluniverse import ToolUniverse

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

print("=" * 80)
print("ENSEMBL REST API EXPANSION EXAMPLES")
print("=" * 80)

# ============================================================================
# 1. COMPARATIVE GENOMICS - Find orthologues across species
# ============================================================================
print("\n1. Finding Mouse Orthologues of Human BRCA2")
print("-" * 80)

result = tu.tools.ensembl_get_homology(**{
    "species": "human",
    "symbol": "BRCA2",  # Gene symbol
    "target_species": "mouse",
    "type": "orthologues"
})

if result["status"] == "success":
    print(f"✅ Found homologies for BRCA2")
    # Navigate response structure: result["data"]["data"][0]["homologies"]
    data_list = result["data"]["data"]
    if len(data_list) > 0 and "homologies" in data_list[0]:
        for homology in data_list[0]["homologies"][:3]:
            print(f"  • Type: {homology.get('type', 'N/A')}")
            if "target" in homology:
                target = homology["target"]
                print(f"    Mouse gene: {target.get('id', 'N/A')}")
                print(f"    Protein: {target.get('protein_id', 'N/A')}")
                print(f"    Identity: {target.get('perc_id', 'N/A')}%")
else:
    print(f"⚠️  Note: {result.get('error', 'API may require different parameters')}")

# ============================================================================
# 2. TAXONOMY - Get complete taxonomic classification
# ============================================================================
print("\n2. Taxonomic Classification of Human")
print("-" * 80)

result = tu.tools.ensembl_get_taxonomy(**{
    "id": "9606"  # NCBI Taxonomy ID for Homo sapiens
})

if result["status"] == "success":
    print(f"✅ Taxonomic hierarchy for Homo sapiens:")
    # Display first few levels of taxonomy
    for i, taxon in enumerate(result["data"][:5]):
        name = taxon.get("scientific_name", taxon.get("name", "Unknown"))
        tax_id = taxon.get("id", "N/A")
        print(f"  {i+1}. {name} (ID: {tax_id})")
    print(f"  ... ({len(result['data'])} total levels)")
else:
    print(f"❌ Error: {result['error']}")

# ============================================================================
# 3. SPECIES INFORMATION - List available species
# ============================================================================
print("\n3. Available Species in Ensembl Vertebrates")
print("-" * 80)

result = tu.tools.ensembl_get_species(**{
    "division": "EnsemblVertebrates"
})

if result["status"] == "success":
    species_list = result["data"]["species"]
    print(f"✅ Found {len(species_list)} vertebrate species")
    print("Sample species:")
    for species in species_list[:5]:
        name = species.get("name", "N/A")
        common = species.get("common_name", "N/A")
        assembly = species.get("assembly", "N/A")
        print(f"  • {common} ({name}) - Assembly: {assembly}")
else:
    print(f"❌ Error: {result['error']}")

# ============================================================================
# 4. GENE ONTOLOGY - Explore ontology hierarchies
# ============================================================================
print("\n4. Gene Ontology Term Information")
print("-" * 80)

# Get term details
result = tu.tools.ensembl_get_ontology_term(**{
    "id": "GO:0005737"  # Cytoplasm
})

if result["status"] == "success":
    term = result["data"]
    print(f"✅ GO Term: {term['accession']}")
    print(f"   Name: {term['name']}")
    print(f"   Definition: {term['definition'][:200]}...")
    print(f"   Namespace: {term['namespace']}")
else:
    print(f"❌ Error: {result['error']}")

# Get ancestor terms (broader concepts)
print("\n   Ancestor Terms (Broader Concepts):")
result = tu.tools.ensembl_get_ontology_ancestors(**{
    "id": "GO:0005737"
})

if result["status"] == "success":
    for i, ancestor in enumerate(result["data"][:5]):
        print(f"   {i+1}. {ancestor['accession']}: {ancestor['name']}")
else:
    print(f"   ⚠️  Error: {result['error']}")

# Get descendant terms (more specific concepts)
print("\n   Descendant Terms (More Specific Concepts):")
result = tu.tools.ensembl_get_ontology_descendants(**{
    "id": "GO:0005737",
    "closest_term": True  # Only immediate children
})

if result["status"] == "success":
    for i, descendant in enumerate(result["data"][:5]):
        print(f"   {i+1}. {descendant['accession']}: {descendant['name']}")
else:
    print(f"   ⚠️  Error: {result['error']}")

# ============================================================================
# 5. GENOMIC FEATURES - Find genes in a region
# ============================================================================
print("\n5. Finding Genes in CFTR Region (Chromosome 7)")
print("-" * 80)

result = tu.tools.ensembl_get_overlap_features(**{
    "species": "human",
    "region": "7:117480025-117668665",  # CFTR region
    "feature": "gene"
})

if result["status"] == "success":
    genes = result["data"]
    print(f"✅ Found {len(genes)} genes in region")
    print("Top genes:")
    for gene in genes[:5]:
        gene_id = gene.get("id", "N/A")
        name = gene.get("external_name", gene.get("id", "N/A"))
        biotype = gene.get("biotype", "N/A")
        start = gene.get("start", "N/A")
        end = gene.get("end", "N/A")
        print(f"  • {name} ({gene_id})")
        print(f"    Type: {biotype}, Position: {start}-{end}")
else:
    print(f"❌ Error: {result['error']}")

# ============================================================================
# 6. VARIANT EFFECT PREDICTOR (VEP) - Predict variant consequences
# ============================================================================
print("\n6. Variant Effect Prediction (VEP)")
print("-" * 80)

# Predict effect of a variant
result = tu.tools.ensembl_vep_region(**{
    "species": "human",
    "region": "21:25891796-25891796",  # APP gene variant
    "allele": "T"  # Alternative allele
})

if result["status"] == "success":
    print(f"✅ VEP Analysis completed")
    if result["data"] and len(result["data"]) > 0:
        variant = result["data"][0]
        print(f"   Allele: {variant.get('allele_string', 'N/A')}")
        print(f"   Most severe consequence: {variant.get('most_severe_consequence', 'N/A')}")
        
        # Show transcript consequences
        if "transcript_consequences" in variant:
            trans_cons = variant["transcript_consequences"]
            print(f"\n   Transcript Consequences ({len(trans_cons)} transcripts):")
            for tc in trans_cons[:3]:
                gene = tc.get("gene_symbol", tc.get("gene_id", "N/A"))
                impact = tc.get("impact", "N/A")
                consequence = tc.get("consequence_terms", ["N/A"])
                print(f"   • Gene: {gene}")
                print(f"     Impact: {impact}")
                print(f"     Consequence: {', '.join(consequence)}")
else:
    print(f"❌ Error: {result['error']}")

# ============================================================================
# 7. ARCHIVE - Track gene history across Ensembl releases
# ============================================================================
print("\n7. Gene Archive History")
print("-" * 80)

result = tu.tools.ensembl_get_archive(**{
    "id": "ENSG00000139618"  # BRCA2
})

if result["status"] == "success":
    print(f"✅ Archive information for BRCA2")
    # Show history across releases
    if isinstance(result["data"], list):
        print(f"   Found {len(result['data'])} versions across releases")
        for entry in result["data"][:3]:
            release = entry.get("release", "N/A")
            version = entry.get("version", "N/A")
            assembly = entry.get("assembly", "N/A")
            latest = "✓" if entry.get("latest", False) else ""
            print(f"   • Release {release}, version {version}, assembly {assembly} {latest}")
    elif isinstance(result["data"], dict):
        print(f"   ID: {result['data'].get('id', 'N/A')}")
        print(f"   Latest: {result['data'].get('latest', 'N/A')}")
else:
    print(f"❌ Error: {result['error']}")

# ============================================================================
# 8. GENOMIC ALIGNMENT - Compare sequences across species
# ============================================================================
print("\n8. Genomic Alignment Between Human and Mouse")
print("-" * 80)

result = tu.tools.ensembl_get_alignment(**{
    "species": "human",
    "region": "2:106000000-106100000",
    "species_set_group": "mammals",  # Use predefined species groups
    "method": "EPO"
})

if result["status"] == "success":
    print(f"✅ Alignment retrieved")
    alignments = result["data"]
    print(f"   {len(alignments)} alignment block(s)")
    if len(alignments) > 0 and "alignments" in alignments[0]:
        species_count = len(alignments[0]["alignments"])
        print(f"   {species_count} species in alignment")
else:
    print(f"⚠️  Note: {result.get('error', 'Alignment may not be available for this region')}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY: Ensembl Tools Expanded")
print("=" * 80)
print("""
New Capabilities Added:
  ✓ Comparative Genomics (homology, alignments)
  ✓ Taxonomy Classification
  ✓ Species Information
  ✓ Gene Ontology Navigation
  ✓ Genomic Feature Discovery
  ✓ Variant Effect Prediction (VEP)
  ✓ Gene Archive/History
  
Total Ensembl Tools: 21 (up from 9)
""")

print("For more information:")
print("  • Ensembl REST API: https://rest.ensembl.org/")
print("  • Documentation: https://rest.ensembl.org/documentation")
