---
name: tooluniverse-gwas-study-explorer
description: Compare GWAS studies, perform meta-analyses, and assess replication across cohorts. Integrates NHGRI-EBI GWAS Catalog and Open Targets Genetics to compare study designs, effect sizes, ancestry diversity, and heterogeneity statistics. Use when comparing GWAS studies for a trait, performing meta-analysis of genetic loci, assessing replication across cohorts, or exploring the genetic architecture of complex diseases.
---


# GWAS Study Deep Dive & Meta-Analysis

**Compare GWAS studies, perform meta-analyses, and assess replication across cohorts**

---

## Overview

The GWAS Study Deep Dive & Meta-Analysis skill enables comprehensive comparison of genome-wide association studies (GWAS) for the same trait, meta-analysis of genetic loci across studies, and systematic assessment of replication and study quality. It integrates data from the NHGRI-EBI GWAS Catalog and Open Targets Genetics to provide a complete picture of the genetic architecture of complex traits.

### Key Capabilities

1. **Study Comparison**: Compare all GWAS studies for a trait, assessing sample sizes, ancestries, and platforms
2. **Meta-Analysis**: Aggregate effect sizes across studies and calculate heterogeneity statistics
3. **Replication Assessment**: Identify replicated vs novel findings across discovery and replication cohorts
4. **Quality Evaluation**: Assess statistical power, ancestry diversity, and data availability

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## Domain Reasoning: Comparing Studies for the Same Trait

When comparing GWAS studies for the same trait, ask: do they replicate? The same lead SNPs appearing in independent studies is strong evidence of a true association. Different lead SNPs at the same locus may reflect LD differences between populations — they may tag the same causal variant. Different loci entirely may reflect different study designs, phenotype definitions, or population ancestry. Before concluding that a finding failed to replicate, check whether the SNP was even genotyped or imputed in the replication cohort.

LOOK UP DON'T GUESS: effect sizes, p-values, allele frequencies, and LD structure for specific loci. Do not assume a SNP present in one study is present in another — use `gwas_get_associations_for_snp` to retrieve cross-study data. Do not infer LD blocks from genomic proximity; use credible sets from Open Targets for fine-mapping results.

---

## Use Cases

### 1. Comprehensive Trait Analysis
**Scenario**: "I want to understand all available GWAS data for type 2 diabetes"

**Workflow**:
- Search for all T2D studies in GWAS Catalog
- Filter by sample size and ancestry
- Extract top associations from each study
- Identify consistently replicated loci
- Assess ancestry-specific effects

**Outcome**: Complete landscape of T2D genetics with replicated findings and population-specific signals

### 2. Locus-Specific Meta-Analysis
**Scenario**: "Is the TCF7L2 association with T2D consistent across all studies?"

**Workflow**:
- Retrieve all TCF7L2 (rs7903146) associations for T2D
- Calculate combined effect size and p-value
- Assess heterogeneity (I² statistic)
- Generate forest plot data
- Interpret heterogeneity level

**Outcome**: Quantitative assessment of effect size consistency with heterogeneity interpretation

### 3. Replication Analysis
**Scenario**: "Which findings from the discovery cohort replicated in the independent sample?"

**Workflow**:
- Get top hits from discovery study
- Check for presence and significance in replication study
- Assess direction consistency
- Calculate replication rate
- Identify novel vs failed replication

**Outcome**: Systematic replication report with success rates and failed findings

### 4. Multi-Ancestry Comparison
**Scenario**: "Are T2D loci consistent across European and East Asian populations?"

**Workflow**:
- Filter studies by ancestry
- Compare top associations between populations
- Identify shared vs population-specific loci
- Assess allele frequency differences
- Evaluate transferability of genetic risk scores

**Outcome**: Ancestry-specific genetic architecture with transferability assessment

---

## Statistical Methods

### Meta-Analysis Approach

This skill implements standard GWAS meta-analysis methods:

**Fixed-Effects Model**:
- Used when heterogeneity is low (I² < 25%)
- Weights studies by inverse variance
- Assumes true effect size is the same across studies

**Random-Effects Model** (recommended when I² > 50%):
- Accounts for between-study variation
- More conservative than fixed-effects
- Better for diverse ancestries or methodologies

**Heterogeneity Assessment**:

The **I² statistic** measures the percentage of variance due to between-study heterogeneity:

```
I² = [(Q - df) / Q] × 100%

where Q = Cochran's Q statistic
      df = degrees of freedom (n_studies - 1)
```

**Interpretation Guidelines**:
- **I² < 25%**: Low heterogeneity → fixed-effects appropriate
- **I² = 25-50%**: Moderate heterogeneity → investigate sources
- **I² = 50-75%**: Substantial heterogeneity → random-effects preferred
- **I² > 75%**: Considerable heterogeneity → meta-analysis may not be appropriate

### Sources of Heterogeneity

Common reasons for high I²:

1. **Ancestry differences**: Different allele frequencies and LD structure
2. **Phenotype heterogeneity**: Trait definition varies across studies
3. **Platform differences**: Imputation quality and coverage
4. **Winner's curse**: Discovery studies overestimate effect sizes
5. **Cohort characteristics**: Age, sex, environmental factors

**Recommendations**:
- Perform subgroup analysis by ancestry
- Use meta-regression to investigate sources
- Consider excluding outlier studies
- Apply genomic control correction

---

## Study Quality Assessment

### Quality Metrics

The skill evaluates studies based on:

**1. Sample Size**:
- Power to detect associations (80% power requires n > 10,000 for OR=1.2)
- Precision of effect size estimates
- Ability to detect modest effects

**2. Ancestry Diversity**:
- Single-ancestry vs multi-ancestry
- Population stratification control
- Transferability of findings

**3. Data Availability**:
- Summary statistics available for meta-analysis
- Individual-level data vs summary-level
- Imputation quality scores

**4. Genotyping Quality**:
- Platform density and coverage
- Imputation reference panel
- Quality control measures

**5. Statistical Rigor**:
- Genome-wide significance threshold (p < 5×10⁻⁸)
- Multiple testing correction
- Replication in independent cohort

### Quality Tiers

**Tier 1 (High Quality)**:
- n ≥ 50,000
- Summary statistics available
- Multi-ancestry or large single-ancestry
- Imputed to high-quality reference
- Independent replication

**Tier 2 (Moderate Quality)**:
- n ≥ 10,000
- Standard GWAS platform
- Adequate power for common variants
- Some data availability

**Tier 3 (Limited)**:
- n < 10,000
- Limited power
- May miss modest effects
- Use with caution

---

## Best Practices

### Before Meta-Analysis

1. **Check phenotype consistency**: Ensure studies measure the same trait
2. **Verify ancestry overlap**: High heterogeneity expected if ancestries differ
3. **Harmonize alleles**: Align effect alleles across studies
4. **Quality control**: Exclude low-quality studies or associations

### Interpreting Results

1. **Genome-wide significance**: p < 5×10⁻⁸ (Bonferroni for ~1M independent tests)
2. **Replication threshold**: p < 0.05 in independent cohort
3. **Direction consistency**: Effect should be same direction across studies
4. **Heterogeneity**: I² > 50% suggests caution in interpretation

### Common Pitfalls

❌ **Don't**:
- Meta-analyze without checking heterogeneity
- Ignore ancestry differences
- Over-interpret nominal p-values
- Assume replication failure means false positive

✅ **Do**:
- Always report I² statistic
- Perform sensitivity analyses
- Consider ancestry-stratified analysis
- Account for winner's curse in discovery studies

---

## Limitations & Caveats

### Data Limitations

1. **Incomplete Overlap**: Studies may analyze different SNPs
2. **Cohort Overlap**: Some cohorts participate in multiple studies (inflates significance)
3. **Publication Bias**: Significant findings more likely to be published
4. **Winner's Curse**: Discovery studies overestimate effect sizes
5. **Imputation Quality**: Varies across studies and populations

### Statistical Limitations

1. **Heterogeneity**: High I² may preclude meaningful meta-analysis
2. **Sample Size Differences**: Large studies dominate fixed-effects models
3. **Allele Frequency Differences**: Same variant has different effects across ancestries
4. **Linkage Disequilibrium**: Fine-mapping needed to identify causal variants
5. **Gene-Environment Interactions**: Not captured in standard meta-analysis

### Interpretation Guidelines

**When I² > 75%**:
- Meta-analysis results should be interpreted with extreme caution
- Investigate sources of heterogeneity systematically
- Consider ancestry-specific or subgroup analyses
- Descriptive comparison may be more appropriate than meta-analysis

**When Studies Conflict**:
- Check for methodological differences
- Verify phenotype definitions match
- Investigate population stratification
- Consider conditional analysis

---

## Tools Used

### GWAS Catalog API
- `gwas_search_studies`: Find studies by trait
- `gwas_get_study_by_id`: Get detailed study metadata
- `gwas_get_associations_for_study`: Retrieve study associations
- `gwas_get_associations_for_snp`: Get SNP associations across studies
- `gwas_search_associations`: Search associations by trait

### Open Targets Genetics GraphQL API
- `OpenTargets_search_gwas_studies_by_disease`: Disease-based study search
- `OpenTargets_get_gwas_study`: Detailed study information with LD populations
- `OpenTargets_get_variant_credible_sets`: Fine-mapped loci for variant
- `OpenTargets_get_study_credible_sets`: All credible sets for study
- `OpenTargets_get_variant_info`: Variant annotation and allele frequencies

## Glossary

**Credible Set**: Set of variants likely to contain the causal variant (from fine-mapping)

**L2G (Locus-to-Gene)**: Score predicting which gene is affected by a GWAS locus
**License**: Open source (MIT)
