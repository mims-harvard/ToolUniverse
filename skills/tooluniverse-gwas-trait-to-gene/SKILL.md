---
name: tooluniverse-gwas-trait-to-gene
description: Discover genes associated with diseases and traits using GWAS data from the GWAS Catalog (500,000+ associations) and Open Targets Genetics (L2G predictions). Identifies genetic risk factors, prioritizes causal genes via locus-to-gene scoring, and assesses druggability. Use when asked to find genes associated with a disease or trait, discover genetic risk factors, translate GWAS signals to gene targets, or answer questions like "What genes are associated with type 2 diabetes?"
---

# GWAS Trait-to-Gene Discovery

**Discover genes associated with diseases and traits using genome-wide association studies (GWAS)**

## Overview

This skill enables systematic discovery of genes linked to diseases/traits by analyzing GWAS data from two major resources:
- **GWAS Catalog** (EBI/NHGRI): Curated catalog of published GWAS with >500,000 associations
- **Open Targets Genetics**: Fine-mapped GWAS signals with locus-to-gene (L2G) predictions

## Use Cases

**Clinical Research**
- "What genes are associated with type 2 diabetes?"
- "Find genetic risk factors for coronary artery disease"
- "Which genes contribute to Alzheimer's disease susceptibility?"

**Drug Target Discovery**
- Identify genes with strong genetic evidence for disease causation
- Prioritize targets based on L2G scores and replication across studies
- Find genes with genome-wide significant associations (p < 5e-8)

**Functional Genomics**
- Map disease-associated variants to candidate genes
- Analyze genetic architecture of complex traits
- Understand polygenic disease mechanisms

## Workflow

```
1. Trait Search → Search GWAS Catalog by disease/trait name
       ↓
2. SNP Aggregation → Collect genome-wide significant SNPs (p < 5e-8)
       ↓
3. Gene Mapping → Extract mapped genes from associations
       ↓
4. Evidence Ranking → Score by p-value, replication, fine-mapping
       ↓
5. Annotation (Optional) → Add L2G predictions from Open Targets
```

## Evidence Confidence Levels

- **High**: L2G score > 0.5 OR multiple studies with p < 5e-10
- **Medium**: 2+ studies with p < 5e-8
- **Low**: Single study or marginal significance

## Executable Workflow

```python
# Step 1: Search GWAS Catalog for trait associations
assocs = tu.run({"name": "gwas_get_associations_for_trait", "arguments": {"trait": "type 2 diabetes"}})
# CHECKPOINT: Verify associations returned before proceeding

# Step 2: Get SNP details for top hits
for snp_id in top_snp_ids:
    snp = tu.run({"name": "gwas_get_snp_by_id", "arguments": {"snp_id": snp_id}})
    # Extract mapped genes from association data

# Step 3: Enrich with Open Targets L2G predictions
studies = tu.run({"name": "OpenTargets_search_gwas_studies_by_disease", "arguments": {"disease_id": "MONDO_0005148"}})
# CHECKPOINT: Verify study data before querying credible sets

# Step 4: Get fine-mapping credible sets
for study in studies:
    credible = tu.run({"name": "OpenTargets_get_study_credible_sets", "arguments": {"study_id": study["id"]}})
    # Extract L2G scores for gene prioritization
```

## ToolUniverse Tools

**GWAS Catalog**: `gwas_get_associations_for_trait`, `gwas_search_snps`, `gwas_get_snp_by_id`, `gwas_get_study_by_id`, `gwas_search_associations`, `gwas_search_studies`, `gwas_get_associations_for_snp`, `gwas_get_variants_for_trait`, `gwas_get_studies_for_trait`, `gwas_get_snps_for_gene`, `gwas_get_associations_for_study`

**Open Targets Genetics**: `OpenTargets_search_gwas_studies_by_disease`, `OpenTargets_get_study_credible_sets`, `OpenTargets_get_variant_credible_sets`, `OpenTargets_get_variant_info`, `OpenTargets_get_gwas_study`, `OpenTargets_get_credible_set_detail`

## Parameters

**Required**
- `trait` - Disease/trait name (e.g., "type 2 diabetes", "coronary artery disease")

**Optional**
- `p_value_threshold` - Significance threshold (default: 5e-8)
- `min_evidence_count` - Minimum number of studies (default: 1)
- `max_results` - Maximum genes to return (default: 100)
- `use_fine_mapping` - Include L2G predictions (default: true)
- `disease_ontology_id` - Disease ontology ID for Open Targets (e.g., "MONDO_0005148")

## Output Schema

```python
{
  "genes": [
    {
      "symbol": str,              # Gene symbol (e.g., "TCF7L2")
      "min_p_value": float,       # Most significant p-value
      "evidence_count": int,      # Number of independent studies
      "snps": [str],              # Associated SNP rs IDs
      "studies": [str],           # GWAS study accessions
      "l2g_score": float | null,  # Locus-to-gene score (0-1)
      "credible_sets": int,       # Number of credible sets
      "confidence_level": str     # "High", "Medium", or "Low"
    }
  ],
  "summary": {
    "trait": str,
    "total_associations": int,
    "significant_genes": int,
    "data_sources": ["GWAS Catalog", "Open Targets"]
  }
}
```

## Example Results

**Type 2 Diabetes**
```
TCF7L2:  p=1.2e-98, 15 studies, L2G=0.82 → High confidence
KCNJ11:  p=3.4e-67, 12 studies, L2G=0.76 → High confidence
PPARG:   p=2.1e-45, 8 studies,  L2G=0.71 → High confidence
FTO:     p=5.6e-42, 10 studies, L2G=0.68 → High confidence
IRS1:    p=8.9e-38, 6 studies,  L2G=0.54 → High confidence
```

**Alzheimer's Disease**
```
APOE:    p=1.0e-450, 25 studies, L2G=0.95 → High confidence
BIN1:    p=2.3e-89,  18 studies, L2G=0.88 → High confidence
CLU:     p=4.5e-67,  16 studies, L2G=0.82 → High confidence
ABCA7:   p=6.7e-54,  14 studies, L2G=0.79 → High confidence
CR1:     p=8.9e-52,  13 studies, L2G=0.75 → High confidence
```

## Notes

- Use disease ontology IDs (e.g., `MONDO_0005148`) for precise trait matching
- For drug targets, use stricter thresholds: `p_value_threshold=5e-10`, `min_evidence_count=3`
- L2G scores provide better causal gene evidence than positional mapping alone
- Some ToolUniverse tools have oneOf validation issues — use `validate=False` if needed

## Related Skills

- `tooluniverse-gwas-snp-interpretation` — Interpret specific SNPs by rsID
- `tooluniverse-gwas-finemapping` — Fine-map GWAS loci to causal variants
- `tooluniverse-gwas-study-explorer` — Compare and meta-analyze GWAS studies
