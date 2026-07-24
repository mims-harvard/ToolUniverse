# Clinical Trial Matching - Quick Start Guide

## Overview

This skill matches patients to optimal clinical trials based on their molecular profile, disease characteristics, and eligibility criteria. It searches ClinicalTrials.gov and cross-references molecular databases to produce evidence-graded, scored trial recommendations.

## Basic Usage

Simply describe your patient profile and ask for trial matches:

```
Find clinical trials for a patient with non-small cell lung cancer,
EGFR L858R mutation, Stage IV, who failed first-line osimertinib.
```

## Use Case Examples

### 1. Targeted Therapy Matching

```
Patient profile:
- Disease: Non-small cell lung cancer (adenocarcinoma)
- Biomarker: EGFR L858R mutation
- Stage: Stage IV, metastatic
- Prior treatment: Failed platinum-based chemotherapy
- ECOG: 0-1

Find the best clinical trial matches.
```

### 2. Immunotherapy Selection

```
Match clinical trials for:
- Melanoma, advanced/metastatic
- TMB-high (>10 mut/Mb)
- PD-L1 positive (TPS >= 50%)
- Failed ipilimumab/nivolumab combination
- ECOG 0
```

### 3. Basket Trial Identification

```
Find basket/tumor-agnostic trials for a patient with:
- Solid tumor (colorectal cancer)
- NTRK1 fusion detected by NGS
- No prior TRK inhibitor therapy
```

### 4. Post-Progression Options

```
Clinical trial options for:
- HR+/HER2- breast cancer
- Failed CDK4/6 inhibitor (palbociclib) + letrozole
- ESR1 Y537S mutation detected
- Bone and liver metastases
```

### 5. Novel Biomarker Trials

```
Find trials for:
- Colorectal cancer, Stage IV
- KRAS G12C mutation
- Failed FOLFOX + bevacizumab
- MSS (microsatellite stable)
```

### 6. Geographic Search

```
Find lung cancer clinical trials:
- Non-small cell lung cancer, any molecular subtype
- Prefer trials in Boston, Massachusetts area
- Currently recruiting
- Phase II or III only
```

## What You Get

For each patient, the skill produces:

1. **Executive Summary** - Top 3 trial recommendations with Trial Match Scores
2. **Patient Profile** - Standardized disease/biomarker information with EFO and gene IDs
3. **Biomarker Actionability** - FDA-approved vs investigational status
4. **Ranked Trial List** - Up to 10+ trials with detailed scoring breakdown:
   - Molecular Match (0-40 points)
   - Clinical Eligibility (0-25 points)
   - Evidence Strength (0-20 points)
   - Trial Phase (0-10 points)
   - Geographic Feasibility (0-5 points)
5. **Trial Details** - NCT ID, phase, status, interventions, eligibility, locations
6. **Drug-Biomarker Alignment** - Whether trial drugs target the patient's biomarkers
7. **Evidence Grading** - T1 (FDA-approved) through T4 (computational)
8. **Alternative Options** - Basket trials, expanded access, off-label options
9. **Additional Testing** - Biomarker tests that would unlock more trials
10. **Completeness Checklist** - What analyses were performed

## Trial Match Score Guide

| Score | Tier | Meaning |
|-------|------|---------|
| **80-100** | Optimal | Strongly recommend - patient's biomarker directly targeted |
| **60-79** | Good | Recommend - good disease and biomarker alignment |
| **40-59** | Possible | Consider - matches on some criteria, needs discussion |
| **0-39** | Exploratory | Backup - general disease trials or weak match |

## Tips for Best Results

1. **Be specific about biomarkers** - Include variant-level detail (e.g., "EGFR L858R" not just "EGFR mutation")
2. **Include prior treatments** - Post-progression trials need to know what failed
3. **Specify stage** - Many trials require specific disease stages
4. **Add geographic preference** - If location matters, include city/state
5. **Mention performance status** - ECOG score helps filter eligibility
6. **List multiple biomarkers** - Complex profiles help find the best-matched trials

## Data Sources

| Source | What It Provides |
|--------|-----------------|
| ClinicalTrials.gov | Trial search, eligibility, locations, status |
| OpenTargets | Drug-target associations, disease ontology |
| CIViC | Clinical variant interpretations |
| ChEMBL | Drug mechanisms and targets |
| FDA | Approved indications, biomarker labels |
| DrugBank | Drug targets and pharmacology |
| PharmGKB | Pharmacogenomics data |
| PubMed | Literature evidence |
| OLS/EFO | Disease ontology standardization |
| MyGene | Gene identifier resolution |

## Limitations

- Trial availability changes frequently; always verify current status at [ClinicalTrials.gov](https://clinicaltrials.gov)
- Eligibility assessment is approximate; final determination is by trial investigators
- Geographic distance calculations are approximate (state/city level, not exact)
- Report is for informational/research purposes only; discuss with healthcare team
- Some trials may have enrollment caps not reflected in public data
