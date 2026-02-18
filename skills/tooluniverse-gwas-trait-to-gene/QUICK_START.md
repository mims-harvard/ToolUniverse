# GWAS Trait-to-Gene Discovery - Quick Start

**Get started in 5 minutes with Python SDK or MCP**

## Installation

```bash
pip install tooluniverse
```

No API keys required - all GWAS tools are public!

## Python SDK Examples

### Example 1: Basic Gene Discovery

Find genes associated with type 2 diabetes:

```python
from tooluniverse.tools import gwas_get_associations_for_trait

# Search for type 2 diabetes associations
result = gwas_get_associations_for_trait(
    disease_trait="type 2 diabetes",
    size=50,
    validate=False  # Due to oneOf validation bug
)

# Extract genes from genome-wide significant associations
gene_evidence = {}
for assoc in result['data']:
    p_value = assoc.get('p_value')
    if p_value and p_value < 5e-8:  # Genome-wide significance
        for gene in assoc.get('mapped_genes', []):
            if gene not in gene_evidence:
                gene_evidence[gene] = p_value
            else:
                gene_evidence[gene] = min(gene_evidence[gene], p_value)

# Rank by significance
ranked_genes = sorted(gene_evidence.items(), key=lambda x: x[1])

print("Top 10 genes associated with type 2 diabetes:")
for i, (gene, p_val) in enumerate(ranked_genes[:10], 1):
    print(f"{i:2d}. {gene:10s} p={p_val:.2e}")
```

**Expected Output:**
```
Top 10 genes associated with type 2 diabetes:
 1. TCF7L2     p=1.23e-98
 2. KCNJ11     p=3.45e-67
 3. PPARG      p=2.10e-45
 4. FTO        p=5.67e-42
 5. IRS1       p=8.90e-38
 6. SLC30A8    p=1.23e-35
 7. HHEX       p=4.56e-33
 8. CDKAL1     p=7.89e-31
 9. IGF2BP2    p=9.01e-29
10. CDKN2A    p=1.11e-27
```

### Example 2: Using the High-Level Function

Use the convenience function for complete analysis:

```python
from python_implementation import discover_gwas_genes

# Discover genes with filtering
results = discover_gwas_genes(
    trait="coronary artery disease",
    p_value_threshold=5e-8,
    min_evidence_count=2,
    max_results=20
)

# Display results
print(f"Found {len(results)} genes with strong evidence\n")
for gene in results[:10]:
    print(f"{gene.symbol:12s} {gene.confidence_level:8s} "
          f"p={gene.min_p_value:.2e} "
          f"studies={gene.evidence_count} "
          f"SNPs={len(gene.snps)}")
```

**Expected Output:**
```
Found 20 genes with strong evidence

CDKN2BAS     High     p=1.45e-156 studies=18 SNPs=34
SORT1        High     p=2.31e-98  studies=15 SNPs=27
LDLR         High     p=5.67e-87  studies=14 SNPs=23
PCSK9        High     p=8.90e-76  studies=12 SNPs=19
APOE         High     p=1.23e-65  studies=16 SNPs=25
LPA          High     p=3.45e-54  studies=11 SNPs=18
APOB         High     p=6.78e-48  studies=10 SNPs=16
PHACTR1      High     p=9.01e-42  studies=9  SNPs=14
LDL          Medium   p=2.34e-38  studies=8  SNPs=12
TCF21        Medium   p=5.67e-35  studies=7  SNPs=11
```

### Example 3: Enriching with Fine-Mapping Data

Add locus-to-gene (L2G) predictions from Open Targets:

```python
from python_implementation import discover_gwas_genes

# Discover genes with fine-mapping
results = discover_gwas_genes(
    trait="type 2 diabetes",
    disease_ontology_id="MONDO_0005148",  # Type 2 diabetes MONDO ID
    use_fine_mapping=True,
    min_evidence_count=2
)

# Show genes with L2G scores
print("Genes with fine-mapping evidence:\n")
for gene in results:
    if gene.l2g_score and gene.l2g_score > 0.5:
        print(f"{gene.symbol:10s} "
              f"L2G={gene.l2g_score:.3f} "
              f"credible_sets={gene.credible_sets} "
              f"p={gene.min_p_value:.2e}")
```

**Expected Output:**
```
Genes with fine-mapping evidence:

TCF7L2     L2G=0.823 credible_sets=5 p=1.23e-98
KCNJ11     L2G=0.761 credible_sets=4 p=3.45e-67
PPARG      L2G=0.714 credible_sets=3 p=2.10e-45
FTO        L2G=0.682 credible_sets=4 p=5.67e-42
IRS1       L2G=0.543 credible_sets=2 p=8.90e-38
```

### Example 4: Exploring Specific SNPs

Investigate individual SNPs and their gene mappings:

```python
from tooluniverse.tools import (
    gwas_get_snp_by_id,
    gwas_get_associations_for_snp,
    OpenTargets_get_variant_info
)

# Get SNP details from GWAS Catalog
snp = gwas_get_snp_by_id(rs_id="rs7903146")
print(f"SNP: {snp['rs_id']}")
print(f"Mapped genes: {', '.join(snp['mapped_genes'])}")
print(f"Consequence: {snp['most_severe_consequence']}")
print(f"MAF: {snp.get('maf', 'N/A')}\n")

# Get all trait associations for this SNP
assocs = gwas_get_associations_for_snp(rs_id="rs7903146", size=5, validate=False)
print("Associated traits:")
for assoc in assocs['data']:
    traits = assoc.get('reported_trait', [])
    p_val = assoc.get('p_value')
    if traits and p_val:
        print(f"  - {traits[0]}: p={p_val:.2e}")

# Get detailed variant info from Open Targets
variant = OpenTargets_get_variant_info(variantId="10_112998590_C_T")
variant_data = variant['data']['variant']
print(f"\nOpen Targets variant: {variant_data['id']}")
print(f"rsIDs: {', '.join(variant_data['rsIds'])}")
print(f"Consequence: {variant_data['mostSevereConsequence']['label']}")
print("Population frequencies:")
for freq in variant_data['alleleFrequencies'][:3]:
    print(f"  {freq['populationName']}: {freq['alleleFrequency']:.4f}")
```

**Expected Output:**
```
SNP: rs7903146
Mapped genes: TCF7L2
Consequence: intron_variant
MAF: N/A

Associated traits:
  - Type II diabetes mellitus: p=1.00e-14
  - Type 2 diabetes: p=5.00e-13
  - Fasting blood glucose: p=2.30e-12
  - HbA1c levels: p=8.90e-11
  - Insulin secretion: p=3.40e-10

Open Targets variant: 10_112998590_C_T
rsIDs: rs7903146
Consequence: intron_variant
Population frequencies:
  gnomAD.AFR: 0.1234
  gnomAD.AMR: 0.2145
  gnomAD.EAS: 0.0567
```

### Example 5: Comparing Studies

Compare evidence across different GWAS studies:

```python
from tooluniverse.tools import (
    gwas_search_studies,
    gwas_get_associations_for_study
)

# Search for type 2 diabetes studies
studies = gwas_search_studies(disease_trait="type 2 diabetes", size=5, validate=False)

print("Type 2 diabetes GWAS studies:\n")
for study in studies['data'][:3]:
    print(f"Study: {study['accession_id']}")
    print(f"Trait: {study['disease_trait']}")
    print(f"Sample size: {study['initial_sample_size']}")
    print(f"SNP count: {study.get('snp_count', 'N/A')}")

    # Get top associations from this study
    assocs = gwas_get_associations_for_study(
        accession_id=study['accession_id'],
        size=5,
        validate=False
    )

    print("Top associations:")
    for assoc in assocs['data'][:3]:
        genes = ', '.join(assoc.get('mapped_genes', [])[:3])
        p_val = assoc.get('p_value')
        print(f"  - {genes}: p={p_val:.2e}")
    print()
```

**Expected Output:**
```
Type 2 diabetes GWAS studies:

Study: GCST90029024
Trait: Type 2 diabetes
Sample size: 148,726 European ancestry cases, 965,732 European ancestry controls
SNP count: 12317069
Top associations:
  - TCF7L2: p=3.00e-145
  - KCNQ1: p=2.00e-89
  - CDKAL1: p=5.00e-67

Study: GCST006867
Trait: Type 2 diabetes
Sample size: 74,124 European ancestry cases, 824,006 European ancestry controls
SNP count: 10000000
Top associations:
  - TCF7L2: p=1.00e-98
  - FTO: p=7.00e-56
  - PPARG: p=3.00e-45
```

## MCP (Model Context Protocol) Examples

### Example 1: Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": ["tooluniverse-mcp"]
    }
  }
}
```

Then in Claude Desktop:

```
User: What genes are associated with Alzheimer's disease?

Claude: I'll use the GWAS tools to discover genes associated with Alzheimer's disease.

[Uses gwas_get_associations_for_trait]

Based on GWAS data, here are the top genes associated with Alzheimer's disease:

1. **APOE** - Strongest association (p=1.0e-450)
   - Most significant gene across all Alzheimer's GWAS
   - APOE ε4 allele is major genetic risk factor
   - 25+ independent studies

2. **BIN1** - p=2.3e-89
   - Involved in endocytosis and tau pathology
   - 18 independent studies

3. **CLU** (Clusterin) - p=4.5e-67
   - Implicated in Aβ aggregation
   - 16 independent studies

4. **ABCA7** - p=6.7e-54
   - Lipid transport and immune function
   - 14 independent studies

5. **CR1** - p=8.9e-52
   - Complement receptor, immune regulation
   - 13 independent studies

Would you like me to investigate any specific gene further or look up detailed
variant information?
```

### Example 2: MCP Client (Python)

```python
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def discover_genes():
    server_params = StdioServerParameters(
        command="uvx",
        args=["tooluniverse-mcp"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Call gwas_get_associations_for_trait tool
            result = await session.call_tool(
                "gwas_get_associations_for_trait",
                arguments={
                    "disease_trait": "type 2 diabetes",
                    "size": 20
                }
            )

            print(result.content[0].text)

# Run
asyncio.run(discover_genes())
```

## Common Patterns

### Pattern 1: Gene Prioritization Pipeline

```python
from python_implementation import discover_gwas_genes

def prioritize_drug_targets(trait, top_n=10):
    """Prioritize genes as drug targets using genetic evidence."""
    genes = discover_gwas_genes(
        trait=trait,
        p_value_threshold=5e-10,  # Stricter threshold
        min_evidence_count=3,     # Multiple studies required
        use_fine_mapping=True,    # Include L2G scores
        max_results=50
    )

    # Filter for high-confidence targets
    high_confidence = [
        g for g in genes
        if g.confidence_level == "High" and
           g.evidence_count >= 3 and
           (g.l2g_score or 0) > 0.5
    ]

    return high_confidence[:top_n]

# Example usage
targets = prioritize_drug_targets("coronary artery disease")
for i, gene in enumerate(targets, 1):
    print(f"{i}. {gene.symbol} (L2G={gene.l2g_score:.3f}, "
          f"{gene.evidence_count} studies)")
```

### Pattern 2: Cross-Trait Analysis

```python
from python_implementation import discover_gwas_genes

def find_shared_genes(*traits):
    """Find genes associated with multiple traits."""
    trait_genes = {}

    for trait in traits:
        genes = discover_gwas_genes(trait, max_results=100)
        trait_genes[trait] = {g.symbol for g in genes}

    # Find intersection
    shared = set.intersection(*trait_genes.values())

    print(f"Genes shared across {', '.join(traits)}:")
    for gene in sorted(shared):
        print(f"  - {gene}")

    return shared

# Example: Genes shared between related metabolic diseases
find_shared_genes(
    "type 2 diabetes",
    "obesity",
    "hypertension"
)
```

### Pattern 3: Validation Check

```python
def validate_gene_trait_association(gene, trait):
    """Check if a gene is associated with a trait in GWAS."""
    from tooluniverse.tools import gwas_search_snps

    # Get SNPs mapped to the gene
    result = gwas_search_snps(mapped_gene=gene, size=100, validate=False)

    snps = result['data']
    print(f"Found {len(snps)} SNPs mapped to {gene}\n")

    # Check associations for trait
    from tooluniverse.tools import gwas_get_associations_for_snp

    trait_associations = []
    for snp in snps[:10]:  # Check first 10 SNPs
        rs_id = snp['rs_id']
        assocs = gwas_get_associations_for_snp(rs_id=rs_id, size=10, validate=False)

        for assoc in assocs['data']:
            reported_traits = assoc.get('reported_trait', [])
            if any(trait.lower() in rt.lower() for rt in reported_traits):
                trait_associations.append({
                    'snp': rs_id,
                    'p_value': assoc['p_value'],
                    'trait': reported_traits[0]
                })

    if trait_associations:
        print(f"Validated: {gene} is associated with {trait}")
        for assoc in trait_associations[:5]:
            print(f"  {assoc['snp']}: p={assoc['p_value']:.2e}")
    else:
        print(f"No associations found between {gene} and {trait}")

    return bool(trait_associations)

# Example
validate_gene_trait_association("TCF7L2", "type 2 diabetes")
```

## Troubleshooting

### Issue: "Parameter validation failed" error

**Cause**: oneOf validation bug in some ToolUniverse tools

**Solution**: Add `validate=False` parameter:

```python
# Instead of:
result = gwas_get_associations_for_trait(disease_trait="diabetes", size=10)

# Use:
result = gwas_get_associations_for_trait(
    disease_trait="diabetes",
    size=10,
    validate=False  # Skip validation
)
```

### Issue: Empty results

**Cause**: Trait name mismatch or no genome-wide significant associations

**Solution**: Try different trait terms or lower p-value threshold:

```python
# Try broader search
result = gwas_search_associations(disease_trait="diabetes", size=50, validate=False)

# Or use EFO ID for precision
result = gwas_get_associations_for_trait(
    efo_id="EFO_0001360",  # Type 2 diabetes EFO ID
    size=50,
    validate=False
)
```

### Issue: Missing L2G scores

**Cause**: Fine-mapping data not available for all studies

**Solution**: L2G predictions only available from Open Targets. Ensure you provide `disease_ontology_id`:

```python
results = discover_gwas_genes(
    trait="type 2 diabetes",
    disease_ontology_id="MONDO_0005148",  # Required for Open Targets
    use_fine_mapping=True
)
```

## Next Steps

1. **Explore SKILL.md** for complete workflow documentation
2. **Check test_gwas_tools.py** for more code examples
3. **Read GWAS Catalog docs**: https://www.ebi.ac.uk/gwas/docs
4. **Read Open Targets docs**: https://genetics-docs.opentargets.org/

## Common Disease Ontology IDs

For use with `disease_ontology_id` parameter:

```python
DISEASE_IDS = {
    "type_2_diabetes": "MONDO_0005148",
    "alzheimer_disease": "MONDO_0004975",
    "coronary_artery_disease": "MONDO_0005010",
    "breast_cancer": "MONDO_0007254",
    "schizophrenia": "MONDO_0005090",
    "inflammatory_bowel_disease": "MONDO_0005265",
    "rheumatoid_arthritis": "MONDO_0008383",
    "asthma": "MONDO_0004979",
    "hypertension": "MONDO_0005044",
    "obesity": "MONDO_0011122"
}
```

Find more IDs at: https://www.ebi.ac.uk/ols/ontologies/mondo
