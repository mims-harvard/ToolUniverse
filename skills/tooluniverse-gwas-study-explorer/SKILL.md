---
name: tooluniverse-gwas-study-explorer
description: Compare GWAS studies, perform meta-analyses, and assess replication across cohorts. Integrates NHGRI-EBI GWAS Catalog and Open Targets Genetics to compare study designs, effect sizes, ancestry diversity, and heterogeneity statistics. Use when comparing GWAS studies for a trait, performing meta-analysis of genetic loci, assessing replication across cohorts, or exploring the genetic architecture of complex diseases.
---

# GWAS Study Deep Dive & Meta-Analysis

Compare GWAS studies, perform meta-analyses, and assess replication across cohorts.

---

## Use Cases

### 1. Comprehensive Trait Analysis
Search all GWAS data for a trait, filter by sample size and ancestry, extract top associations, and identify replicated loci.

### 2. Locus-Specific Meta-Analysis
Retrieve all associations for a specific variant, calculate combined effect sizes, and assess heterogeneity across studies.

### 3. Replication Analysis
Compare discovery and replication cohorts: check significance, direction consistency, and replication rate.

### 4. Multi-Ancestry Comparison
Compare top associations across populations, identify shared vs population-specific loci, and assess genetic risk score transferability.

---

## Workflow

### Step 1: Discover studies

```python
# Search for GWAS studies on type 2 diabetes
studies = tu.run({"name": "gwas_search_studies", "arguments": {"query": "type 2 diabetes"}})

# Or search via Open Targets by disease
ot_studies = tu.run({"name": "OpenTargets_search_gwas_studies_by_disease", "arguments": {"disease": "type 2 diabetes"}})
```

**Checkpoint**: Verify studies returned match your trait of interest and note sample sizes.

### Step 2: Get study details and associations

```python
# Get detailed metadata for a specific study
study = tu.run({"name": "gwas_get_study_by_id", "arguments": {"study_id": "GCST007517"}})

# Get all associations for that study
assocs = tu.run({"name": "gwas_get_associations_for_study", "arguments": {"study_id": "GCST007517"}})
```

**Checkpoint**: Confirm associations include p-values, effect sizes, and risk alleles.

### Step 3: Cross-study variant comparison

```python
# Get all associations for a specific SNP across studies
snp_assocs = tu.run({"name": "gwas_get_associations_for_snp", "arguments": {"snp_id": "rs7903146"}})

# Get fine-mapped credible sets for a variant
cred_sets = tu.run({"name": "OpenTargets_get_variant_credible_sets", "arguments": {"variant_id": "7_44196069_C_T"}})
```

**Checkpoint**: Verify effect direction consistency across studies before meta-analysis.

### Step 4: Annotate and interpret

```python
# Get variant annotation and allele frequencies
variant = tu.run({"name": "OpenTargets_get_variant_info", "arguments": {"variant_id": "7_44196069_C_T"}})

# Get all credible sets for a study
study_creds = tu.run({"name": "OpenTargets_get_study_credible_sets", "arguments": {"study_id": "GCST007517"}})
```

**Checkpoint**: Compare allele frequencies across populations before cross-ancestry conclusions.

---

## Tools Used

### GWAS Catalog API
- `gwas_search_studies` — find studies by trait
- `gwas_get_study_by_id` — detailed study metadata
- `gwas_get_associations_for_study` — all associations for a study
- `gwas_get_associations_for_snp` — SNP associations across studies
- `gwas_search_associations` — search associations by trait

### Open Targets Genetics GraphQL API
- `OpenTargets_search_gwas_studies_by_disease` — disease-based study search
- `OpenTargets_get_gwas_study` — study info with LD populations
- `OpenTargets_get_variant_credible_sets` — fine-mapped loci for variant
- `OpenTargets_get_study_credible_sets` — all credible sets for study
- `OpenTargets_get_variant_info` — variant annotation and allele frequencies
