# Treatment Algorithms & Evidence Grading

## Evidence Grading

| Tier | Symbol | Criteria | Example |
|------|--------|----------|---------|
| T1 | Three stars | FDA-approved, CIViC Level A, OncoKB Level 1-2 | Osimertinib for T790M |
| T2 | Two stars | Phase 2/3 data, CIViC Level B-C, OncoKB Level 3A | Combination trials |
| T3 | One star | Preclinical, CIViC Level D, OncoKB Level 4 | Novel mechanisms |
| T4 | No stars | Computational only, CIViC Level E | Docking predictions |

### CIViC Evidence Level Mapping

| CIViC Level | Tier | Meaning |
|-------------|------|---------|
| A | T1 | FDA-approved, guideline |
| B | T2 | Clinical evidence |
| C | T2 | Case study |
| D | T3 | Preclinical |
| E | T4 | Inferential |

### OncoKB Level Mapping

| OncoKB Level | Tier | Description |
|--------------|------|-------------|
| LEVEL_1 | T1 | FDA-recognized biomarker |
| LEVEL_2 | T1 | Standard care |
| LEVEL_3A | T2 | Compelling clinical evidence |
| LEVEL_3B | T2 | Different tumor type |
| LEVEL_4 | T3 | Biological evidence |
| LEVEL_R1 | Resistance | FDA-approved resistance marker |
| LEVEL_R2 | Resistance | Compelling resistance evidence |

---

## Treatment Prioritization

| Priority | Criteria |
|----------|----------|
| **1st Line** | FDA-approved for indication + biomarker (T1) |
| **2nd Line** | Clinical trial evidence, guideline-recommended (T2) |
| **3rd Line** | Off-label with mechanistic rationale (T3) |

---

## Fallback Chains

| Primary | Fallback | Use When |
|---------|----------|----------|
| CIViC variant | OncoKB (literature) | Variant not in CIViC |
| OpenTargets drugs | ChEMBL activities | No approved drugs found |
| ClinicalTrials.gov | WHO ICTRP | US trials insufficient |
| NvidiaNIM_alphafold2 | AlphaFold DB | API unavailable |

---

## Cancer Type Mappings

### TCGA Project Codes

| Cancer Type | TCGA Project |
|-------------|-------------|
| Lung adenocarcinoma | TCGA-LUAD |
| Breast | TCGA-BRCA |
| Colorectal | TCGA-COAD |
| Melanoma | TCGA-SKCM |
| Glioblastoma | TCGA-GBM |
| Pancreatic | TCGA-PAAD |

### HPA Cancer Cell Lines

| Cancer Type | Cell Line |
|-------------|-----------|
| Lung | a549 |
| Breast | mcf7 |
| Liver | hepg2 |
| Cervical | hela |
| Prostate | pc3 |

### OncoTree Tumor Type Codes (common)

| Cancer | Code |
|--------|------|
| Melanoma | MEL |
| Non-Small Cell Lung Cancer | NSCLC |
| Lung Adenocarcinoma | LUAD |
| Breast Cancer | BRCA |
| Colorectal Cancer | COADREAD |
| Pancreatic | PAAD |

---

## DepMap Interpretation Guide

- Effect score < -0.5 = strongly essential for cell survival
- Compare cancer-type-specific vs pan-cancer scores for selectivity
- Pan-essential genes (e.g., MYC) are challenging therapeutic targets
- Cancer-selective genes are better drug targets

| Score Range | Interpretation |
|-------------|----------------|
| < -1.0 | Strongly essential |
| -0.5 to -1.0 | Essential |
| -0.5 to 0 | Weakly essential |
| > 0 | Not essential |
