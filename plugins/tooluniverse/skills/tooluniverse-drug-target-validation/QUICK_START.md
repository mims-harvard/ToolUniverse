# Drug Target Validation - Quick Start Guide

## Overview

This skill validates drug target hypotheses using computational evidence from 60+ ToolUniverse tools. It produces a **Target Validation Score (0-100)** with a GO/NO-GO recommendation.

## Basic Usage

### Use Case 1: Full Target Validation (Disease-Specific)
```
Is KRAS a druggable target for pancreatic cancer?
```
**What happens**: Full 10-phase analysis with disease-specific evidence, produces validation score and GO/NO-GO recommendation.

### Use Case 2: General Target Druggability Assessment
```
Assess the druggability of BTK as a therapeutic target
```
**What happens**: Focuses on druggability, chemical matter, structural tractability, and clinical precedent without disease-specific filtering.

### Use Case 3: Target Safety Assessment
```
What are the safety risks of inhibiting IDH1?
```
**What happens**: Emphasizes safety phase - expression in critical tissues, knockout phenotypes, known adverse events, paralogs.

### Use Case 4: Chemical Starting Points
```
What compounds are available for PCSK9 validation?
```
**What happens**: Deep dive into chemical matter - ChEMBL activities, BindingDB ligands, PubChem bioassays, chemical probes.

### Use Case 5: Target Comparison
```
Compare PD-1 vs PD-L1 as immunotherapy targets
```
**What happens**: Runs validation pipeline for both targets, produces side-by-side comparison of scores.

### Use Case 6: Novel Target Evaluation
```
Is TEAD4 a viable target for solid tumors? Consider small molecule approach.
```
**What happens**: Full validation with modality-specific analysis, extra focus on structural tractability for small molecules.

## Output

Every analysis produces a markdown report file with:

1. **Executive Summary** with GO/NO-GO recommendation
2. **Validation Scorecard** (0-100 composite score)
3. **10 Detailed Sections** covering all evidence dimensions
4. **Validation Roadmap** with recommended experiments
5. **Risk Assessment** with mitigation strategies
6. **Completeness Checklist** showing analysis coverage

## Priority Tiers

| Score | Tier | Meaning |
|-------|------|---------|
| 80-100 | Tier 1 | Highly validated - proceed with confidence |
| 60-79 | Tier 2 | Good target - needs focused validation |
| 40-59 | Tier 3 | Moderate risk - significant validation needed |
| 0-39 | Tier 4 | High risk - consider alternatives |

## Evidence Grades

- **[T1]**: Direct mechanistic evidence (crystal structure, patient mutations, FDA-approved drug)
- **[T2]**: Functional studies (CRISPR KO, mouse model, biochemical assay)
- **[T3]**: Association (GWAS hit, DepMap essentiality, expression correlation)
- **[T4]**: Annotation (database entry, computational prediction, review article)

## Example Report Structure

```
EGFR_NSCLC_validation_report.md

Executive Summary
  Score: 90/100 | Tier 1 | GO
  Strong genetic + clinical validation for NSCLC

Validation Scorecard
  Disease Association:   28/30
  Druggability:          24/25
  Safety Profile:        14/20
  Clinical Precedent:    15/15
  Validation Evidence:    9/10

[10 detailed sections with tool outputs and evidence]

Validation Roadmap
  - Recommended experiments
  - Tool compounds
  - Biomarker strategy
  - Risk mitigations
```

## Key Databases Queried

| Database | Information | Tools |
|----------|------------|-------|
| OpenTargets | Disease associations, tractability, safety | 15+ tools |
| ChEMBL | Bioactivity, compounds, mechanisms | 8+ tools |
| PDB/AlphaFold | 3D structures, binding pockets | 12+ tools |
| STRING/IntAct | Protein interactions | 6+ tools |
| GTEx/HPA | Tissue expression | 10+ tools |
| GWAS Catalog | Genetic associations | 5+ tools |
| FDA/DrugBank | Approved drugs, safety | 10+ tools |
| ClinicalTrials.gov | Clinical development | 2+ tools |
| PubMed/EuropePMC | Literature evidence | 6+ tools |
| gnomAD | Genetic constraint | 2+ tools |
| DepMap | Cancer essentiality | 3+ tools |
| Reactome | Biological pathways | 5+ tools |
