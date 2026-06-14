# Precision Medicine Stratification - Report Template

Save the output report as `[PATIENT_ID]_precision_medicine_report.md` with this structure.

---

```markdown
# Precision Medicine Stratification Report

## Executive Summary
- **Patient Profile**: [Disease, key features]
- **Precision Medicine Risk Score**: [X]/100
- **Risk Tier**: [LOW / INTERMEDIATE / HIGH / VERY HIGH]
- **Key Finding**: [One-line summary of most actionable finding]
- **Primary Recommendation**: [One-line treatment recommendation]

## 1. Patient Profile
### Disease Classification
### Genomic Data Summary
### Clinical Parameters

## 2. Genetic Risk Assessment
### Germline Variant Analysis
### Gene-Disease Association Evidence
### Polygenic Risk Estimation
### Population Frequency Data

## 3. Disease-Specific Stratification
### [Cancer: Molecular Subtype / Metabolic: Risk Integration / etc.]
### Prognostic Markers
### Risk Group Assignment

## 4. Pharmacogenomic Profile
### Drug-Metabolizing Enzymes
### Drug Target Variants
### Treatment-Specific PGx Recommendations
### FDA PGx Biomarker Status

## 5. Comorbidity & Drug Interaction Risk
### Disease-Disease Overlap
### Drug-Drug Interactions
### PGx-Amplified DDI Risk

## 6. Dysregulated Pathways
### Key Pathways Affected
### Druggable Targets
### Network Analysis

## 7. Clinical Evidence & Guidelines
### Guideline-Based Classification
### FDA-Approved Therapies
### Biomarker-Drug Evidence

## 8. Clinical Trial Matches
### Biomarker-Driven Trials
### Precision Medicine Trials
### Risk-Adapted Trials

## 9. Integrated Risk Score
### Score Breakdown
| Component | Points | Max | Basis |
|-----------|--------|-----|-------|
| Genetic Risk | X | 35 | [Details] |
| Clinical Risk | X | 30 | [Details] |
| Molecular Features | X | 25 | [Details] |
| Pharmacogenomic Risk | X | 10 | [Details] |
| **TOTAL** | **X** | **100** | |

### Risk Tier: [TIER]
### Confidence Level: [HIGH/MODERATE/LOW]

## 10. Treatment Algorithm
### 1st Line Recommendation
### 2nd Line Options
### 3rd Line / Investigational
### PGx Dose Adjustments

## 11. Monitoring Plan
### Biomarker Surveillance
### Imaging Schedule
### Risk Reassessment Timeline

## 12. Outcome Predictions
### Disease-Specific Prognosis
### Treatment Response Prediction
### Projected Timeline

## Completeness Checklist
| Data Layer | Available | Analyzed | Key Finding |
|-----------|-----------|----------|-------------|
| Disease disambiguation | Y/N | Y/N | [EFO ID] |
| Germline variants | Y/N | Y/N | [Pathogenicity] |
| Somatic mutations | Y/N | Y/N | [Drivers] |
| Gene expression | Y/N | Y/N | [Subtype] |
| PGx genotypes | Y/N | Y/N | [Metabolizer status] |
| Clinical biomarkers | Y/N | Y/N | [Key values] |
| GWAS/PRS | Y/N | Y/N | [Risk percentile] |
| Pathway analysis | Y/N | Y/N | [Key pathways] |
| Clinical trials | Y/N | Y/N | [N matches] |
| Guidelines | Y/N | Y/N | [Guideline tier] |

## Evidence Sources
[List all databases and tools used with specific citations]
```

---

## Treatment Algorithm Templates

### Cancer Treatment Algorithm

```
IF actionable mutation present:
  1st line: Targeted therapy (e.g., EGFR TKI, BRAF inhibitor, PARP inhibitor)
  2nd line: Immunotherapy (if TMB-H or MSI-H) OR chemotherapy
  3rd line: Clinical trial OR alternative targeted therapy

IF no actionable mutation:
  IF TMB-H or MSI-H:
    1st line: Immunotherapy (pembrolizumab)
    2nd line: Chemotherapy
  ELSE:
    1st line: Standard chemotherapy (disease-specific)
    2nd line: Consider clinical trials

PGx adjustments:
  - DPYD deficient -> AVOID fluoropyrimidines or reduce dose 50%
  - UGT1A1 *28/*28 -> Reduce irinotecan dose
  - CYP2D6 PM + tamoxifen -> Switch to aromatase inhibitor
```

### Metabolic/CVD Treatment Algorithm

```
IF monogenic form (MODY, FH):
  Disease-specific therapy (e.g., sulfonylureas for HNF1A-MODY, PCSK9i for FH)

IF polygenic risk:
  Standard guidelines (ADA, ACC/AHA)
  PGx-guided drug selection:
    - CYP2C19 PM -> Alternative to clopidogrel (ticagrelor, prasugrel)
    - SLCO1B1 *5 -> Lower statin dose or alternative statin
    - VKORC1 variant -> Warfarin dose adjustment or DOAC
```

### Monitoring Plan

| Component | Frequency | Method |
|-----------|-----------|--------|
| Molecular biomarkers | Per guideline | Liquid biopsy, tissue biopsy |
| Clinical markers | 3-6 months | Labs, imaging |
| PGx-guided drug levels | As needed | TDM |
| Disease progression | Per stage/risk | Imaging, biomarkers |
| Comorbidity screening | Annually | Labs, risk calculators |

---

## Completeness Requirements

Minimum deliverables for a valid stratification report:
1. Disease resolved to EFO/ontology ID
2. At least one genetic risk assessment completed (germline OR somatic OR PRS)
3. Disease-specific stratification with risk group
4. At least one pharmacogenomic assessment (even if "no actionable findings")
5. Pathway analysis with at least one pathway identified
6. Treatment recommendation with evidence tier
7. At least one clinical trial match attempted
8. Precision Medicine Risk Score calculated with all available components
9. Risk tier assigned
10. Monitoring plan outlined
