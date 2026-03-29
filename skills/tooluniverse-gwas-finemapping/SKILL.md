---
name: tooluniverse-gwas-finemapping
description: Identify and prioritize causal variants at GWAS loci using statistical fine-mapping and locus-to-gene predictions. Computes posterior probabilities for causal variants, links variants to genes via L2G predictions, annotates functional consequences, and suggests validation strategies. Use when asked to fine-map GWAS loci, prioritize causal variants, identify credible sets, or link GWAS signals to causal genes.
---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

# GWAS Fine-Mapping & Causal Variant Prioritization

Identify and prioritize causal variants at GWAS loci using statistical fine-mapping and locus-to-gene predictions.

## Overview

Genome-wide association studies (GWAS) identify genomic regions associated with traits, but linkage disequilibrium (LD) makes it difficult to pinpoint the causal variant. **Fine-mapping** uses Bayesian statistical methods to compute the posterior probability that each variant is causal, given the GWAS summary statistics.

**REASONING STRATEGY — Start Here**:
Fine-mapping asks: which variant at this locus is CAUSAL? Work through this chain:
1. **LD structure first** — variants in high LD (r² > 0.8) cannot be statistically distinguished from each other. Look up the LD block via Open Targets or the GWAS Catalog before assuming any single variant is the cause.
2. **Functional annotation breaks LD ties** — if two variants have similar posterior probabilities but one is coding (missense, stop-gain) or sits in an active regulatory element (promoter, enhancer), that variant is biologically prioritized. Functional evidence is the tiebreaker.
3. **eQTL colocalization is the key bridge** — a variant that is also a significant eQTL for a nearby gene in the relevant tissue (e.g., a pancreatic islet eQTL for a T2D locus) has a mechanistic story. Look up eQTL evidence via Open Targets L2G scores; don't assume the nearest gene is the effector gene.

This skill provides tools to:
- **Prioritize causal variants** using fine-mapping posterior probabilities
- **Link variants to genes** using locus-to-gene (L2G) predictions
- **Annotate variants** with functional consequences
- **Suggest validation strategies** based on fine-mapping results

## Key Concepts

### Credible Sets
A **credible set** is a minimal set of variants that contains the causal variant with high confidence (typically 95% or 99%). Each variant in the set has a **posterior probability** of being causal, computed using methods like:
- **SuSiE** (Sum of Single Effects)
- **FINEMAP** (Bayesian fine-mapping)
- **PAINTOR** (Probabilistic Annotation INtegraTOR)

### Posterior Probability
The probability that a specific variant is causal, given the GWAS data and LD structure. Higher posterior probability = more likely to be causal.

### Locus-to-Gene (L2G) Predictions
L2G scores integrate multiple data types to predict which gene is affected by a variant:
- Distance to gene (closer = higher score)
- eQTL evidence (expression changes)
- Chromatin interactions (Hi-C, promoter capture)
- Functional annotations (coding variants, regulatory regions)

L2G scores range from 0 to 1, with higher scores indicating stronger gene-variant links.

## Fine-Mapping Reasoning Framework (CRITICAL)

**LOOK UP DON'T GUESS** -- never assume a lead SNP is the causal variant. Always check LD structure, credible sets, and functional annotations via the tools below.

### Step 1: Lead SNP vs Causal Variant

The lead SNP (most significant p-value) is often NOT the causal variant. It is simply the best-tagged variant on the genotyping array. The causal variant may be:
- In perfect LD (r2 > 0.95) with the lead SNP but with a functional consequence
- A non-coding regulatory variant not on the array
- One of several independent signals at the locus (conditional analysis reveals multiple)

**Action**: Always call `OpenTargets_get_variant_credible_sets` for the lead SNP. If the posterior probability is < 0.5, the lead SNP is likely NOT causal -- examine other variants in the credible set.

### Step 2: LD Structure Interpretation

LD blocks define the resolution limit of fine-mapping:
- **Tight LD block (few variants, r2 > 0.9)**: Credible set will be small; functional annotation is the tiebreaker
- **Broad LD block (many variants)**: Credible set is large; statistical fine-mapping alone is insufficient -- need functional data (eQTL, chromatin, CRISPR)
- **Population matters**: LD patterns differ between European, African, East Asian populations. African populations have shorter LD blocks and better fine-mapping resolution. Check which population the GWAS was conducted in.

### Step 3: Credible Set Analysis

When interpreting a credible set:
1. **Size matters**: A 95% credible set with 1-3 variants = high resolution. With 50+ variants = low resolution, need more data.
2. **Posterior probability distribution**: If one variant has PP > 0.5, it is the strong favorite. If PP is spread evenly across many variants, no single causal variant can be identified statistically.
3. **Multiple credible sets at one locus**: Indicates multiple independent causal signals (allelic heterogeneity). Each set represents a different causal mechanism.

### Step 4: Colocalization Reasoning

Colocalization asks: do two association signals (e.g., GWAS + eQTL) share the SAME causal variant?
- **High L2G score (> 0.7) + eQTL in relevant tissue**: Strong evidence the variant affects disease THROUGH gene expression changes
- **High GWAS signal but no eQTL**: Variant may act through protein-coding change, splicing, or a tissue/cell-type not yet profiled
- **eQTL for distant gene (not nearest)**: The effector gene is NOT the nearest gene. **LOOK UP** the L2G score -- do not default to nearest gene

### Step 5: Prioritization Tiebreakers

When multiple variants have similar posterior probabilities:
1. Coding variant (missense, stop-gain) > regulatory > intronic > intergenic
2. In active chromatin mark (H3K27ac, H3K4me1) in disease-relevant tissue
3. Disrupts transcription factor binding motif
4. Conserved across species (PhyloP, GERP)
5. eQTL in disease-relevant tissue with consistent direction of effect

## Common Queries

- "Which variant at the TCF7L2 locus is likely causal for type 2 diabetes?" → Use `OpenTargets_get_variant_credible_sets` or `gwas_search_snps` with gene=TCF7L2
- "Fine-map rs429358 (APOE4)" → Use `OpenTargets_get_variant_info` then `OpenTargets_get_variant_credible_sets`
- "All causal loci from GWAS study GCST90029024" → Use `OpenTargets_get_study_credible_sets`
- "GWAS studies for Alzheimer's disease" → Use `OpenTargets_search_gwas_studies_by_disease` or `gwas_search_studies`

## Tools Used

### Open Targets Genetics (GraphQL)
- `OpenTargets_get_variant_info`: Variant details and allele frequencies
- `OpenTargets_get_variant_credible_sets`: Credible sets containing a variant
- `OpenTargets_get_credible_set_detail`: Detailed credible set information
- `OpenTargets_get_study_credible_sets`: All loci from a GWAS study
- `OpenTargets_search_gwas_studies_by_disease`: Find studies by disease

### GWAS Catalog (REST API)
- `gwas_search_snps`: Find SNPs by gene or rsID
- `gwas_get_snp_by_id`: Detailed SNP information
- `gwas_get_associations_for_snp`: All trait associations for a variant
- `gwas_search_studies`: Find studies by disease/trait

## Understanding Fine-Mapping Output

### Interpreting Posterior Probabilities
- **> 0.5**: Very likely causal (strong candidate)
- **0.1 - 0.5**: Plausible causal variant
- **0.01 - 0.1**: Possible but uncertain
- **< 0.01**: Unlikely to be causal

### Interpreting L2G Scores
- **> 0.7**: High confidence gene-variant link
- **0.5 - 0.7**: Moderate confidence
- **0.3 - 0.5**: Weak but possible link
- **< 0.3**: Low confidence

## Common Questions

**Q: Why don't all variants have credible sets?**
A: Fine-mapping requires:
1. GWAS summary statistics (not just top hits)
2. LD reference panel
3. Sufficient signal strength (p < 5e-8)
4. Computational resources

**Q: Can a variant be in multiple credible sets?**
A: Yes! A variant can be causal for multiple traits (pleiotropy) or appear in different studies for the same trait.

**Q: What if the top L2G gene is far from the variant?**
A: This suggests regulatory effects (enhancers, promoters). Check:
- eQTL evidence in relevant tissues
- Chromatin interaction data (Hi-C)
- Regulatory element annotations (Roadmap, ENCODE)

**Q: How do I choose between variants in a credible set?**
A: Prioritize by:
1. Posterior probability (higher = better)
2. Functional consequence (coding > regulatory > intergenic)
3. eQTL evidence
4. Evolutionary conservation
5. Experimental feasibility

## Limitations

1. **LD-dependent**: Fine-mapping accuracy depends on LD structure matching the study population
2. **Requires summary stats**: Not all studies provide full summary statistics
3. **Computational intensive**: Fine-mapping large studies takes significant resources
4. **Prior assumptions**: Bayesian methods depend on priors (number of causal variants, effect sizes)
5. **Missing data**: Not all GWAS loci have been fine-mapped in Open Targets

## Best Practices

1. **Start with study-level queries** when exploring a new disease
2. **Check multiple studies** for replication of signals
3. **Combine with functional data** (eQTLs, chromatin, CRISPR screens)
4. **Consider ancestry** - LD differs across populations
5. **Validate experimentally** - fine-mapping provides candidates, not proof

## References

1. Wang et al. (2020) "A simple new approach to variable selection in regression, with application to genetic fine mapping." *JRSS-B* (SuSiE)
2. Benner et al. (2016) "FINEMAP: efficient variable selection using summary data from genome-wide association studies." *Bioinformatics*
3. Ghoussaini et al. (2021) "Open Targets Genetics: systematic identification of trait-associated genes using large-scale genetics and functional genomics." *NAR*
4. Mountjoy et al. (2021) "An open approach to systematically prioritize causal variants and genes at all published human GWAS trait-associated loci." *Nat Genet*

## Related Skills

- **tooluniverse-gwas-explorer**: Broader GWAS analysis
- **tooluniverse-eqtl-colocalization**: Link variants to gene expression
- **tooluniverse-gene-prioritization**: Systematic gene ranking
