# Precision Medicine Stratification - Quick Start

## Basic Usage

### Cancer patient with actionable mutation
```
Stratify this breast cancer patient: BRCA1 pathogenic variant, ER+/HER2-, stage IIA, age 45. What is her risk level and recommended treatment?
```

### Metabolic disease with pharmacogenomics
```
Precision medicine stratification for type 2 diabetes patient: HbA1c 8.5%, CYP2C19 *2/*2 poor metabolizer, also on clopidogrel for CAD stent. Age 62, male.
```

### Cardiovascular risk assessment
```
Stratify cardiovascular risk: LDL 190 mg/dL, SLCO1B1*5 heterozygous, family history of MI at age 48. Age 50, male. What statin should I use?
```

### NSCLC with comprehensive molecular data
```
Precision medicine report for NSCLC patient: EGFR L858R mutation, TMB 25 mut/Mb, PD-L1 80%, stage IV, age 58. No EGFR T790M resistance.
```

### Rare disease evaluation
```
Stratify this Marfan syndrome patient: FBN1 c.4082G>A variant, tall stature, aortic root dilation 4.2cm, age 28. What is the risk tier?
```

### Alzheimer's risk assessment
```
Precision medicine risk assessment: APOE e4/e4 genotype, family history of Alzheimer's in both parents, age 55. What is the genetic risk and prevention strategy?
```

## What You Get

The skill produces a comprehensive markdown report with:

1. **Precision Medicine Risk Score** (0-100) with transparent component breakdown
   - Genetic Risk (0-35): Germline variants, PRS, gene-disease associations
   - Clinical Risk (0-30): Stage, biomarkers, comorbidities
   - Molecular Features (0-25): Driver mutations, molecular subtype, actionable targets
   - Pharmacogenomic Risk (0-10): CYP metabolizer status, HLA alleles

2. **Risk Tier Assignment**: LOW (0-24) / INTERMEDIATE (25-49) / HIGH (50-74) / VERY HIGH (75-100)

3. **Disease-Specific Stratification**: Cancer molecular subtype, metabolic risk integration, CVD risk score, rare disease genotype-phenotype correlation

4. **Pharmacogenomic Profile**: Drug metabolism phenotype, FDA PGx biomarkers, dosing recommendations

5. **Treatment Algorithm**: 1st-line, 2nd-line, 3rd-line/investigational with evidence

6. **Clinical Trial Matches**: Biomarker-driven and precision medicine trials

7. **Monitoring Plan**: Biomarker surveillance, imaging schedule, risk reassessment

8. **Outcome Predictions**: Prognosis, treatment response, projected timeline

## Input Requirements

### Required
- **Disease/condition**: Any disease name (cancer, metabolic, CVD, neurological, rare, autoimmune)
- **At least one of**: Germline variants, somatic mutations, gene names, or clinical biomarkers

### Optional (improves accuracy)
- Age, sex, ethnicity
- Disease stage/grade
- Clinical biomarkers (HbA1c, LDL, PSA, tumor markers)
- Pharmacogenomic genotypes (CYP2D6, CYP2C19, SLCO1B1, etc.)
- Comorbidities
- Current medications
- Family history
- Prior treatments and responses
- Stratification goal (risk assessment, treatment selection, prognosis, prevention)

## Supported Disease Categories

| Category | Examples | Key Outputs |
|----------|----------|-------------|
| **Cancer** | Breast, lung, colorectal, melanoma, prostate | Molecular subtype, targeted therapy, TMB/MSI status |
| **Metabolic** | Type 2 diabetes, obesity, NAFLD, MODY | HbA1c risk, genetic subtype, complication risk |
| **Cardiovascular** | CAD, heart failure, AF, FH | ASCVD risk, statin PGx, anticoagulant selection |
| **Neurological** | Alzheimer, Parkinson, epilepsy | APOE risk, genetic risk, drug PGx |
| **Rare/Monogenic** | Marfan, CF, sickle cell, Huntington | Variant pathogenicity, penetrance, genotype-phenotype |
| **Autoimmune** | RA, lupus, MS, Crohn's | HLA associations, biologics selection, PGx |
