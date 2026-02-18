# Quick Start: GWAS Fine-Mapping & Causal Variant Prioritization

Get started with fine-mapping GWAS loci in 5 minutes.

## Installation

```bash
pip install tooluniverse
```

No API keys required - all tools use public data.

## 30-Second Example

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools()

# Get credible sets for rs7903146 (TCF7L2, T2D risk variant)
result = tu.run_one_function({
    "name": "OpenTargets_get_variant_credible_sets",
    "arguments": {
        "variantId": "10_112998590_C_T",  # rs7903146
        "size": 5
    }
})

# Print credible sets
for cs in result["data"]["variant"]["credibleSets"]["rows"]:
    trait = cs["study"]["traitFromSource"]
    method = cs["finemappingMethod"]
    gene = cs["l2GPredictions"]["rows"][0]["target"]["approvedSymbol"]
    print(f"{trait}: {gene} ({method})")
```

## Python SDK Usage

### Example 1: Prioritize Variants at a Locus

```python
from python_implementation import prioritize_causal_variants

# Prioritize variants in TCF7L2 for diabetes
result = prioritize_causal_variants("TCF7L2", "type 2 diabetes")

# Print summary
print(result.get_summary())

# Output:
# Query Gene: TCF7L2
#
# Credible Sets Found: 8
# Associated Traits: 15
#
# Top Causal Genes (by L2G score):
#   - TCF7L2 (L2G score: 0.863)
#
# Top Credible Sets:
#
# 1. type 2 diabetes
#    Region: 10:112861809-113404438
#    Method: SuSiE-inf
#    Top gene: TCF7L2 (L2G score: 0.863)
```

### Example 2: Fine-Map a Specific Variant

```python
# Fine-map rs429358 (APOE4, Alzheimer's risk allele)
result = prioritize_causal_variants("rs429358")

# Check credible sets
for cs in result.credible_sets:
    print(f"Trait: {cs.trait}")
    print(f"Method: {cs.finemapping_method}")
    print(f"Region: {cs.region}")

    if cs.l2g_genes:
        print(f"Top gene: {cs.l2g_genes[0]}")
```

### Example 3: Explore All Loci from a GWAS

```python
from python_implementation import get_credible_sets_for_study

# Get all loci from a type 2 diabetes GWAS
credible_sets = get_credible_sets_for_study("GCST90029024")

print(f"Found {len(credible_sets)} independent loci")

# Show top 5 loci
for cs in credible_sets[:5]:
    print(f"\nRegion: {cs.region}")

    if cs.lead_variant:
        print(f"Lead variant: {cs.lead_variant.rs_ids[0] if cs.lead_variant.rs_ids else 'N/A'}")
        if cs.lead_variant.p_value:
            print(f"P-value: {cs.lead_variant.p_value:.2e}")

    if cs.l2g_genes:
        top_gene = cs.l2g_genes[0]
        print(f"Top gene: {top_gene.gene_symbol} (L2G: {top_gene.l2g_score:.3f})")
```

### Example 4: Search for Studies

```python
from python_implementation import search_gwas_studies_for_disease

# Search for Alzheimer's disease studies
studies = search_gwas_studies_for_disease("Alzheimer's disease")

for study in studies[:5]:
    print(f"{study['id']}")
    print(f"  Samples: {study.get('nSamples', 'N/A')}")
    print(f"  Author: {study.get('publicationFirstAuthor', 'N/A')}")
    print(f"  Summary stats: {study.get('hasSumstats', False)}")
```

### Example 5: Get Validation Suggestions

```python
result = prioritize_causal_variants("APOE", "alzheimer")

# Get experimental validation suggestions
suggestions = result.get_validation_suggestions()
for suggestion in suggestions:
    print(suggestion)

# Output:
# 1. Functional validation in APOE:
#    - CRISPR knock-in of risk allele in cell lines
#    - Reporter assays for regulatory variants
#    - eQTL analysis in relevant tissues
#
# 2. Colocalization analysis:
#    - Check overlap with eQTLs, sQTLs, pQTLs
#    - Examine chromatin accessibility in disease-relevant cells
#
# 3. Independent replication:
#    - Targeted genotyping in independent cohort
#    - Meta-analysis with additional GWAS
```

## MCP Integration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/ToolUniverse",
        "run",
        "tooluniverse-mcp"
      ]
    }
  }
}
```

Then use in Claude:

```
User: Which variant at the APOE locus is most likely causal for Alzheimer's?

Claude: I'll help you identify causal variants at the APOE locus...

[Uses OpenTargets_get_variant_credible_sets and related tools]

Based on fine-mapping data, rs429358 (APOE4 allele) has:
- Posterior probability: 0.87 (87% chance of being causal)
- Fine-mapping method: SuSiE-inf
- L2G gene: APOE (score: 0.95)
- Functional consequence: missense variant (Cys130Arg)

This variant is the most likely causal allele for Alzheimer's at this locus.
```

## Common Patterns

### Pattern 1: Gene → Loci → Validation Plan

```python
# Start with a gene
gene = "TCF7L2"

# Find associated loci
result = prioritize_causal_variants(gene, "diabetes")

# Get validation plan
print(result.get_summary())
print("\nValidation Strategy:")
for suggestion in result.get_validation_suggestions():
    print(suggestion)
```

### Pattern 2: Disease → Studies → Top Loci

```python
# Start with a disease
disease = "type 2 diabetes"
disease_id = "MONDO_0005148"

# Find studies
studies = search_gwas_studies_for_disease(disease, disease_id)
largest = max(studies, key=lambda s: s.get('nSamples', 0) or 0)

# Get all loci
credible_sets = get_credible_sets_for_study(largest['id'])

# Analyze top loci
for cs in credible_sets[:10]:
    print(f"{cs.region}: {cs.l2g_genes[0] if cs.l2g_genes else 'No L2G'}")
```

### Pattern 3: Variant → Traits → Prioritization

```python
# Start with a variant
variant = "rs7903146"

# Get all associated traits
result = prioritize_causal_variants(variant)

print(f"Associated with {len(set(result.associated_traits))} unique traits")
print("\nTop traits:")
for trait in list(set(result.associated_traits))[:5]:
    print(f"  - {trait}")

# Check credible sets
print(f"\nAppears in {len(result.credible_sets)} credible sets")
```

## Tips

### Variant ID Formats

Open Targets uses `chr_position_ref_alt` format:
```python
# Example conversions:
# rs429358 (APOE) → 19_44908684_T_C
# rs7903146 (TCF7L2) → 10_112998590_C_T
```

Use `gwas_get_snp_by_id` to get coordinates for rsIDs:
```python
result = tu.run_one_function({
    "name": "gwas_get_snp_by_id",
    "arguments": {"rs_id": "rs7903146"}
})

location = result["locations"][0]
print(f"chr{location['chromosome_name']}:{location['chromosome_position']}")
```

### Finding Disease IDs

Use disease ontology browsers:
- **EFO**: [EMBL-EBI Ontology Lookup](https://www.ebi.ac.uk/ols/ontologies/efo)
- **MONDO**: [Monarch Disease Ontology](https://monarchinitiative.org/disease)

Common examples:
- Alzheimer's: `EFO_0000249`
- Type 2 diabetes: `MONDO_0005148`
- Coronary artery disease: `MONDO_0005010`

### Interpreting L2G Scores

```python
for gene in result.top_causal_genes:
    if gene.l2g_score > 0.7:
        confidence = "HIGH"
    elif gene.l2g_score > 0.5:
        confidence = "MODERATE"
    elif gene.l2g_score > 0.3:
        confidence = "LOW"
    else:
        confidence = "VERY LOW"

    print(f"{gene.gene_symbol}: {confidence} (L2G: {gene.l2g_score:.3f})")
```

## Troubleshooting

### No credible sets found
- Not all variants have fine-mapping data
- Try querying by gene instead of rsID
- Check if the variant is genome-wide significant (p < 5e-8)

### Missing variant ID
Open Targets requires `chr_pos_ref_alt` format. Get coordinates from GWAS Catalog first:
```python
gwas_result = tu.run_one_function({
    "name": "gwas_get_snp_by_id",
    "arguments": {"rs_id": "rs123456"}
})
# Extract chr and position from locations
```

### Empty L2G predictions
Some loci don't have L2G scores (computational limitations or gene deserts). Consider:
- Checking nearby genes manually
- Using eQTL colocalization
- Examining Hi-C chromatin interactions

## Next Steps

- Read the full [SKILL.md](./SKILL.md) for detailed concepts
- Review [test_skill_comprehensive.py](./test_skill_comprehensive.py) for more examples
- Explore the [GWAS Catalog documentation](https://www.ebi.ac.uk/gwas/docs)
- Check [Open Targets Genetics](https://genetics.opentargets.org/) for web interface

## Resources

- **Open Targets Genetics**: https://genetics.opentargets.org/
- **GWAS Catalog**: https://www.ebi.ac.uk/gwas/
- **SuSiE paper**: https://doi.org/10.1111/rssb.12388
- **L2G paper**: https://doi.org/10.1038/s41588-021-00945-5
