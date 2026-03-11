---
name: tooluniverse-polygenic-risk-score
description: Build and interpret polygenic risk scores (PRS) for complex diseases using GWAS summary statistics. Calculates genetic risk profiles, interprets PRS percentiles, and assesses disease predisposition across conditions including type 2 diabetes, coronary artery disease, and Alzheimer's disease. Use when asked to calculate polygenic risk scores, interpret genetic risk for complex diseases, build custom PRS from GWAS data, or answer questions like "What is my genetic predisposition to breast cancer?"
---

# Polygenic Risk Score (PRS) Builder

Build and interpret polygenic risk scores for complex diseases using GWAS data.

## Overview

**Use when asked to:**
- Calculate genetic risk for complex diseases (T2D, CAD, Alzheimer's, breast cancer)
- Build PRS models from GWAS summary statistics
- Interpret PRS percentiles and risk categories

**Scope:** PRS is probabilistic, not diagnostic. Does not replace clinical assessment or account for non-genetic factors.

## Methodology

### PRS Formula

```
PRS = Σ (dosage_i × effect_size_i)
```

- **dosage_i**: Effect allele count (0, 1, or 2)
- **effect_size_i**: Beta coefficient or ln(OR) from GWAS

### Standardization

```
z-score = (PRS - population_mean) / population_std
```

### Thresholds

| Threshold | P-value | Use case |
|-----------|---------|----------|
| Genome-wide significance | p < 5e-8 | Default, conservative |
| Relaxed | p < 1e-5 | More SNPs, more noise |

### Effect Sizes

- **Continuous traits**: Use beta directly
- **Binary traits**: Convert OR to log-odds (beta = ln(OR))

## Data Sources

| Source | Tools |
|--------|-------|
| GWAS Catalog (EMBL-EBI) | `gwas_get_associations_for_trait`, `gwas_get_snp_by_id` |
| Open Targets Genetics | `OpenTargets_search_gwas_studies_by_disease`, `OpenTargets_get_variant_info` |

## Workflow

### Step 1: Retrieve GWAS Associations

```python
# Get all genome-wide significant associations for a trait
assocs = tu.run({"name": "gwas_get_associations_for_trait", "arguments": {"trait": "type 2 diabetes"}})
```

**Checkpoint:** Verify associations returned. If empty, try broader trait terms or check Open Targets:
```python
studies = tu.run({"name": "OpenTargets_search_gwas_studies_by_disease", "arguments": {"disease": "type 2 diabetes mellitus"}})
```

### Step 2: Extract SNP Details and Effect Sizes

```python
# For each significant SNP, get variant details
for snp_id in significant_snps:
    snp = tu.run({"name": "gwas_get_snp_by_id", "arguments": {"snp_id": snp_id}})
    # Extract: effect_allele, beta/OR, p-value, risk_allele_frequency
```

**Checkpoint:** Confirm each SNP has a valid effect size (beta or OR). Exclude SNPs with missing effect sizes.

### Step 3: Filter and QC

Apply quality filters before scoring:
- Exclude rare variants (MAF < 0.01)
- Remove ambiguous A/T and G/C SNPs (strand ambiguity)
- Convert all ORs to log-odds for consistency

**Checkpoint:** Log how many SNPs pass QC vs. total retrieved. If <10 SNPs remain, consider relaxing the p-value threshold.

### Step 4: Calculate Score

```python
# Weighted sum across passing variants
prs = sum(dosage[snp] * effect_size[snp] for snp in passing_snps)

# Standardize to z-score
z_score = (prs - population_mean) / population_std
```

### Step 5: Interpret Risk

Map z-score to percentile and risk category:

| Percentile | Category | Interpretation |
|------------|----------|----------------|
| < 20th | Low risk | Below-average genetic predisposition |
| 20-80th | Average risk | Typical genetic predisposition |
| 80-95th | Elevated risk | Moderately increased predisposition |
| > 95th | High risk | Substantially increased predisposition |

**Checkpoint:** Always report the number of SNPs used, the p-value threshold applied, and the GWAS ancestry. Flag if ancestry of target individual differs from GWAS population.

