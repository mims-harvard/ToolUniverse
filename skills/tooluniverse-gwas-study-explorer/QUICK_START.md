# GWAS Study Deep Dive & Meta-Analysis - Quick Start Guide

Get started with GWAS study comparison and meta-analysis in 5 minutes.

---

## Installation

```bash
pip install tooluniverse
```

No API keys required - all GWAS tools use public APIs.

---

## Basic Usage

### Python SDK

```python
from tooluniverse import ToolUniverse
from skills.tooluniverse_gwas_study_explorer.python_implementation import (
    compare_gwas_studies,
    meta_analyze_locus,
    assess_replication
)

# Initialize ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Example 1: Compare all type 2 diabetes studies
result = compare_gwas_studies(
    tu,
    trait="type 2 diabetes",
    min_sample_size=10000,
    max_studies=20
)

print(f"Analyzed {result.n_studies} studies")
print(f"Total samples: {sum(s.sample_size for s in result.studies):,}")
print(f"Replicated loci: {len(result.replicated_loci)}")
print(f"Novel loci: {len(result.novel_loci)}")

# Get quality summary
quality = result.get_quality_summary()
print(f"\nQuality Metrics:")
print(f"  Ancestry diversity: {quality['ancestry_diversity']} populations")
print(f"  Ancestries: {', '.join(quality['ancestries'])}")
print(f"  Studies with summary stats: {quality['studies_with_summary_stats']}")
print(f"  Replication rate: {quality['replication_rate']:.1%}")

# Example 2: Meta-analyze TCF7L2 locus for T2D
meta_result = meta_analyze_locus(
    tu,
    rs_id="rs7903146",
    trait="type 2 diabetes"
)

print(f"\nMeta-Analysis Results for TCF7L2 (rs7903146):")
print(f"  Studies: {meta_result.n_studies}")
print(f"  Combined p-value: {meta_result.combined_p_value:.2e}")
print(f"  Heterogeneity: {meta_result.heterogeneity_level} (I²={meta_result.heterogeneity_i2:.1f}%)")
print(f"  Genome-wide significant: {meta_result.is_significant}")
print(f"\nInterpretation: {meta_result.interpretation}")

# Example 3: Assess replication between studies
replication_results = assess_replication(
    tu,
    trait="type 2 diabetes",
    discovery_study_id="GCST000392",  # Discovery study
    replication_study_id="GCST90029024"  # Replication study
)

print(f"\nReplication Assessment:")
print(f"  Total loci tested: {len(replication_results)}")
replicated = [r for r in replication_results if r.replicated]
print(f"  Replicated: {len(replicated)}")
print(f"  Replication rate: {len(replicated)/len(replication_results):.1%}")

print(f"\nTop replicated loci:")
for r in sorted(replicated, key=lambda x: x.replication_p)[:5]:
    print(f"  {r.locus}: {r.replication_strength}")
    print(f"    Discovery p={r.discovery_p:.2e}, Replication p={r.replication_p:.2e}")
```

**Output:**
```
Searching for type 2 diabetes studies...
Found 12 studies meeting criteria
  Fetching associations for GCST90029024...
  Fetching associations for GCST90444481...
  ...
Found 156 total loci, 89 replicated

Analyzed 12 studies
Total samples: 2,456,890
Replicated loci: 89
Novel loci: 67

Quality Metrics:
  Ancestry diversity: 5 populations
  Ancestries: European, East Asian, Hispanic, African, South Asian
  Studies with summary stats: 9
  Replication rate: 57.1%

Meta-analyzing rs7903146 for type 2 diabetes...
Found 47 associations for type 2 diabetes

Meta-Analysis Results for TCF7L2 (rs7903146):
  Studies: 47
  Combined p-value: 3.45e-156
  Heterogeneity: moderate (I²=42.3%)
  Genome-wide significant: True

Interpretation: Genome-wide significant (p=3.45e-156). Moderate heterogeneity (I²=42.3%)

Assessing replication: GCST000392 -> GCST90029024
Found 23 loci, 18 replicated

Replication Assessment:
  Total loci tested: 23
  Replicated: 18
  Replication rate: 78.3%

Top replicated loci:
  rs9268645: Strong (genome-wide significant)
    Discovery p=1.00e-100, Replication p=2.34e-89
  rs3024505: Strong (genome-wide significant)
    Discovery p=4.50e-45, Replication p=1.23e-52
  ...
```

---

## MCP Usage

If using Claude Desktop or another MCP client:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "tooluniverse-mcp"
    }
  }
}
```

Then in Claude:

> "Compare all GWAS studies for coronary artery disease with sample size > 20,000"

> "Meta-analyze the 9p21 locus (rs1333049) for CAD across all studies"

> "Assess replication of the CARDIoGRAMplusC4D findings in UK Biobank"

---

## Common Workflows

### Workflow 1: Comprehensive Trait Analysis

```python
# Step 1: Find all studies
result = compare_gwas_studies(tu, "coronary artery disease", min_sample_size=20000)

# Step 2: Get study details
for study in result.studies[:5]:
    print(f"\n{study.accession_id}: {study.trait}")
    print(f"  Sample size: {study.sample_size:,}")
    print(f"  Ancestry: {', '.join(study.ancestry)}")

    # Get quality metrics
    metrics = get_study_quality_metrics(study)
    print(f"  Quality: {metrics['tier']}")
    print(f"  Power: {metrics['power_score']}")

# Step 3: Identify top loci
print(f"\nTop 10 associations:")
for i, assoc in enumerate(result.top_associations[:10], 1):
    print(f"{i}. {assoc.rs_id}: p={assoc.p_value:.2e}")
    print(f"   Genes: {', '.join(assoc.mapped_genes[:3])}")
    print(f"   Replicated in {len([a for a in result.replicated_loci if a == assoc.rs_id])} studies")

# Step 4: Check for ancestry-specific effects
european_studies = [s for s in result.studies if "European" in " ".join(s.ancestry)]
asian_studies = [s for s in result.studies if "East Asian" in " ".join(s.ancestry)]

print(f"\nAncestry breakdown:")
print(f"  European studies: {len(european_studies)} (n={sum(s.sample_size for s in european_studies):,})")
print(f"  East Asian studies: {len(asian_studies)} (n={sum(s.sample_size for s in asian_studies):,})")
```

### Workflow 2: Locus Deep Dive

```python
# Meta-analyze a specific locus
locus = "rs7903146"  # TCF7L2 for T2D
trait = "type 2 diabetes"

# Step 1: Meta-analysis
meta_result = meta_analyze_locus(tu, locus, trait)

print(f"Meta-Analysis: {locus} for {trait}")
print(f"  Studies: {meta_result.n_studies}")
print(f"  Combined p: {meta_result.combined_p_value:.2e}")
print(f"  Heterogeneity: {meta_result.heterogeneity_level} (I²={meta_result.heterogeneity_i2:.1f}%)")

# Step 2: Get variant details from Open Targets
variant_result = tu.run({
    "name": "OpenTargets_get_variant_info",
    "arguments": {"variantId": "10_112998590_C_T"}  # rs7903146
})

variant = variant_result["data"]["variant"]
print(f"\nVariant Details:")
print(f"  Position: chr{variant['chromosome']}:{variant['position']}")
print(f"  Alleles: {variant['referenceAllele']}/{variant['alternateAllele']}")
print(f"  Consequence: {variant['mostSevereConsequence']['label']}")

# Step 3: Get credible sets (fine-mapping)
credset_result = tu.run({
    "name": "OpenTargets_get_variant_credible_sets",
    "arguments": {"variantId": "10_112998590_C_T", "size": 10}
})

csets = credset_result["data"]["variant"]["credibleSets"]["rows"]
print(f"\nFine-Mapping (n={len(csets)} credible sets):")
for i, cset in enumerate(csets[:3], 1):
    study = cset["study"]
    print(f"\n{i}. {study['traitFromSource']}")
    print(f"   Method: {cset['finemappingMethod']}")

    # L2G predictions
    l2g = cset["l2GPredictions"]["rows"]
    if l2g:
        top_gene = l2g[0]["target"]["approvedSymbol"]
        top_score = l2g[0]["score"]
        print(f"   Top gene: {top_gene} (L2G score: {top_score:.3f})")

# Step 4: Forest plot data
print(f"\nForest Plot Data:")
print(f"{'Study':<15} {'P-value':<15} {'Genes'}")
print("-" * 60)
for row in meta_result.forest_plot_data[:10]:
    genes = ", ".join(row["mapped_genes"][:2]) if row["mapped_genes"] else "N/A"
    print(f"{row['study']:<15} {row['p_value']:<15.2e} {genes}")
```

### Workflow 3: Multi-Ancestry Comparison

```python
trait = "type 2 diabetes"

# Step 1: Get studies by ancestry
european_result = compare_gwas_studies(
    tu, trait,
    ancestry_filter=["European"],
    min_sample_size=10000
)

asian_result = compare_gwas_studies(
    tu, trait,
    ancestry_filter=["East Asian"],
    min_sample_size=10000
)

# Step 2: Compare top loci
eur_loci = set(a.rs_id for a in european_result.top_associations[:50])
asian_loci = set(a.rs_id for a in asian_result.top_associations[:50])

shared_loci = eur_loci & asian_loci
eur_specific = eur_loci - asian_loci
asian_specific = asian_loci - eur_loci

print("Multi-Ancestry Comparison")
print(f"  European studies: {european_result.n_studies} (n={sum(s.sample_size for s in european_result.studies):,})")
print(f"  East Asian studies: {asian_result.n_studies} (n={sum(s.sample_size for s in asian_result.studies):,})")
print(f"\nLocus sharing:")
print(f"  Shared loci: {len(shared_loci)}")
print(f"  European-specific: {len(eur_specific)}")
print(f"  East Asian-specific: {len(asian_specific)}")

# Step 3: Check allele frequencies for shared loci
print(f"\nShared loci with ancestry-specific frequencies:")
for rs_id in list(shared_loci)[:5]:
    # Get variant info from Open Targets
    # This would require converting rs_id to variantId (chr_pos_ref_alt)
    print(f"  {rs_id}: Check gnomAD frequencies")
```

---

## Tips & Tricks

### 1. Handling Large Studies

For traits with many studies, use filtering:

```python
# Focus on high-quality studies
result = compare_gwas_studies(
    tu, trait="height",
    min_sample_size=50000,  # Large studies only
    max_studies=10  # Top 10 by sample size
)

# Filter for summary stats availability
studies_with_sumstats = [s for s in result.studies if s.has_summary_stats]
```

### 2. Interpreting Heterogeneity

```python
meta_result = meta_analyze_locus(tu, "rs7903146", "type 2 diabetes")

if meta_result.heterogeneity_i2 > 50:
    print("⚠️  High heterogeneity detected!")
    print("Consider:")
    print("  - Ancestry-stratified analysis")
    print("  - Random-effects model")
    print("  - Investigation of outlier studies")
```

### 3. Checking Study Quality

```python
from python_implementation import get_study_quality_metrics

for study in result.studies:
    metrics = get_study_quality_metrics(study)

    if metrics["tier"] == "Tier 1 (High quality)":
        print(f"✓ {study.accession_id}: High quality")
    elif metrics["power_score"] == "low":
        print(f"⚠️  {study.accession_id}: Low power, use with caution")
```

### 4. Finding Disease IDs for Open Targets

```python
# Use MONDO IDs for Open Targets
disease_mappings = {
    "type 2 diabetes": "MONDO_0005148",
    "Alzheimer disease": "MONDO_0004975",
    "coronary artery disease": "MONDO_0005010",
    "breast cancer": "MONDO_0007254",
    "asthma": "MONDO_0004979"
}

# Search Open Targets studies
result = tu.run({
    "name": "OpenTargets_search_gwas_studies_by_disease",
    "arguments": {
        "diseaseIds": ["MONDO_0005148"],  # T2D
        "size": 50
    }
})
```

---

## Troubleshooting

### Problem: No studies found

```python
result = compare_gwas_studies(tu, "my rare disease")
# n_studies = 0
```

**Solution**: Try different trait names or use EFO terms:

```python
# Try broader terms
result = compare_gwas_studies(tu, "diabetes")  # Instead of specific type

# Or use GWAS Catalog search first
search_result = tu.run({
    "name": "gwas_search_studies",
    "arguments": {"disease_trait": "diabetes", "size": 100}
})

# Check available traits
traits = set(s["disease_trait"] for s in search_result["data"])
print(f"Available traits: {traits}")
```

### Problem: Heterogeneity too high (I² > 75%)

```python
meta_result = meta_analyze_locus(tu, "rs123456", "trait")
# I² = 89%
```

**Solution**: Perform ancestry-stratified analysis or describe results qualitatively rather than meta-analyzing.

### Problem: Low replication rate

```python
replication_results = assess_replication(tu, trait, disc_id, repl_id)
# Replication rate: 20%
```

**Possible causes**:
- Different populations/ancestries
- Winner's curse in discovery study
- Different phenotype definitions
- Insufficient power in replication cohort

---

## Next Steps

1. **Fine-Mapping**: Use Open Targets credible sets to narrow down causal variants
2. **Functional Analysis**: Investigate biological mechanisms of replicated loci
3. **PRS Development**: Build polygenic risk scores from validated associations
4. **Drug Discovery**: Use L2G scores to identify therapeutic targets

---

## Support

- **Documentation**: See full [SKILL.md](./SKILL.md) for detailed methodology
- **Issues**: Report bugs or request features on GitHub
- **Examples**: More examples in `test_skill_comprehensive.py`

---

**Last Updated**: 2026-02-13
