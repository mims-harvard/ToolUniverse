# Precision Medicine Stratification - Scoring Reference

## Pathogenicity Classification (ACMG-aligned)

| Classification | ClinVar Term | Risk Score Points |
|---------------|-------------|-------------------|
| Pathogenic | Pathogenic | 25 (molecular component) |
| Likely pathogenic | Likely pathogenic | 20 |
| VUS | Uncertain significance | 10 (conservative) |
| Likely benign | Likely benign | 2 |
| Benign | Benign | 0 |

## PRS Estimation (from GWAS data)

| PRS Percentile | Risk Category | Score Points (0-35) |
|---------------|--------------|---------------------|
| >95th percentile | Very high genetic risk | 35 |
| 90-95th | High genetic risk | 30 |
| 75-90th | Elevated genetic risk | 25 |
| 50-75th | Average-high | 18 |
| 25-50th | Average-low | 12 |
| 10-25th | Below average | 8 |
| <10th | Low genetic risk | 5 |

**Note**: With user-provided variants only (not full genotype), estimate approximate PRS by counting known risk alleles and their effect sizes from GWAS catalog. Flag as "estimated - full genotyping recommended for precise PRS."

## Genetic Risk Score Component (0-35 points)

Combine pathogenicity + gene-disease association + PRS:
- Pathogenic variant in disease gene: 25+ points
- Strong GWAS associations (multiple risk alleles): up to 35 points
- VUS in relevant gene: 10-15 points
- No known pathogenic variants but some risk alleles: 5-15 points

---

## Cancer-Specific Subtype Definitions

| Cancer | Subtype System | Key Markers | High-Risk Features |
|--------|---------------|-------------|-------------------|
| Breast | Luminal A/B, HER2+, TNBC | ER, PR, HER2, Ki67 | TNBC, high Ki67, TP53 mut |
| NSCLC | Adenocarcinoma, squamous | EGFR, ALK, ROS1, KRAS, PD-L1 | KRAS G12C, no driver = chemoIO |
| CRC | MSI-H vs MSS, CMS1-4 | KRAS, BRAF, MSI, CMS | BRAF V600E, MSS |
| Melanoma | BRAF-mut, NRAS-mut, wild-type | BRAF, NRAS, KIT, NF1 | NRAS, uveal |
| Prostate | Luminal vs basal, BRCA status | AR, BRCA1/2, SPOP, TMPRSS2:ERG | BRCA2, neuroendocrine |

## Cancer Biomarker Thresholds

| Biomarker | High-Risk Threshold | Clinical Significance |
|-----------|-------------------|----------------------|
| TMB | >= 10 mut/Mb (FDA cutoff) | Pembrolizumab eligible (tissue-agnostic) |
| MSI-H | MSI-high or dMMR | Pembrolizumab/nivolumab eligible |
| HRD | HRD-positive | PARP inhibitor eligible |

## Cancer Prognostic Scoring (0-30 clinical)

| Stage | Low-Risk Molecular | High-Risk Molecular | Score |
|-------|-------------------|--------------------|-----------------------|
| I | Favorable subtype | Unfavorable subtype | 5-10 |
| II | Favorable subtype | Unfavorable subtype | 10-18 |
| III | Any | Any | 18-25 |
| IV | Any | Any | 25-30 |

---

## T2D Stratification

| Risk Factor | Low Risk | Moderate Risk | High Risk | Score Points |
|-------------|----------|---------------|-----------|-------------|
| HbA1c | <6.5% | 6.5-8.0% | >8.0% | 5-30 |
| Genetic risk | No risk alleles | 1-3 risk alleles | MODY gene/many risk alleles | 5-25 |
| Complications | None | Microalbuminuria | Retinopathy, neuropathy | 0-20 |
| Duration | <5 years | 5-15 years | >15 years | 0-10 |

## CVD Risk Integration

| Factor | Score Points |
|--------|-------------|
| LDL >190 mg/dL | 15 |
| FH gene mutation (LDLR/APOB/PCSK9) | 20 |
| ASCVD >20% 10-year risk | 30 |
| Family hx premature CVD | 10 |
| Lipoprotein(a) elevated | 8 |
| Multiple GWAS risk alleles | 5-15 |

## Rare Disease Risk Assessment

| Finding | Risk Level | Score Points |
|---------|-----------|-------------|
| Pathogenic variant in causal gene | Definitive | 30 |
| Likely pathogenic in causal gene | Strong | 25 |
| VUS in causal gene | Moderate | 15 |
| Family history + partial phenotype | Suggestive | 10 |
| Single phenotype feature only | Low | 5 |

---

## Key Pharmacogenes and Clinical Impact

| Gene | Star Alleles | Metabolizer Status | Clinical Impact | Score Points |
|------|-------------|-------------------|----------------|-------------|
| CYP2D6 | *4/*4, *5/*5 | Poor metabolizer | Codeine, tamoxifen, many antidepressants | 8 |
| CYP2C19 | *2/*2, *2/*3 | Poor metabolizer | Clopidogrel, voriconazole, PPIs | 8 |
| CYP2C9 | *2/*3, *3/*3 | Poor metabolizer | Warfarin, NSAIDs, phenytoin | 5 |
| SLCO1B1 | *5/*5 | Decreased function | Statin myopathy (simvastatin) | 5 |
| DPYD | *2A | DPD deficient | 5-FU/capecitabine severe toxicity | 10 |
| VKORC1 | -1639G>A | Warfarin sensitive | Lower warfarin dose needed | 5 |
| UGT1A1 | *28/*28 | Poor glucuronidator | Irinotecan toxicity | 5 |
| TPMT | *2, *3A, *3C | Poor metabolizer | Thiopurine toxicity | 8 |
| HLA-B*5701 | Present | N/A | Abacavir hypersensitivity | 10 |
| HLA-B*1502 | Present | N/A | Carbamazepine SJS/TEN | 10 |

## Pharmacogenomic Risk Score (0-10 points)

- Poor metabolizer for treatment-relevant CYP: 8-10 points
- Intermediate metabolizer: 4-5 points
- High-risk HLA allele: 8-10 points
- Drug target variant: 3-5 points
- Normal metabolizer, no actionable PGx: 0 points

## PGx-Amplified DDI Risk

| Interaction Type | Risk Level | Management |
|-----------------|-----------|------------|
| PGx PM + CYP inhibitor | Very high | Alternative drug or dose reduction |
| PGx IM + CYP inhibitor | High | Monitor closely, possible dose reduction |
| PGx normal + CYP inhibitor | Moderate | Standard monitoring |
| No interacting drugs | Low | Standard care |

---

## Druggable Pathways

| Pathway | Key Nodes | Drug Classes | Cancer Relevance |
|---------|-----------|-------------|-----------------|
| PI3K/AKT/mTOR | PIK3CA, AKT1, MTOR | PI3K inhibitors, mTOR inhibitors | Breast, endometrial |
| RAS/MAPK | KRAS, BRAF, MEK1/2 | KRAS G12C inhibitors, BRAF inhibitors | Lung, CRC, melanoma |
| DNA damage repair | BRCA1/2, ATM, PALB2 | PARP inhibitors | Breast, ovarian, prostate |
| Cell cycle | CDK4/6, RB1, CCND1 | CDK4/6 inhibitors | Breast |
| Immunocheckpoint | PD-1, PD-L1, CTLA-4 | ICIs | Pan-cancer |
| Wnt/beta-catenin | APC, CTNNB1, TCF | Wnt inhibitors (investigational) | CRC |

## Guideline References by Disease

| Disease Category | Guidelines | Key Stratification |
|-----------------|-----------|-------------------|
| Breast cancer | NCCN, ASCO, St. Gallen | Luminal A/B, HER2+, TNBC, BRCA status |
| NSCLC | NCCN, ESMO | Driver mutation status, PD-L1, TMB |
| CRC | NCCN | MSI, RAS/BRAF, sidedness |
| T2D | ADA Standards | HbA1c, CVD risk, CKD stage |
| CVD | ACC/AHA | ASCVD risk score, LDL goals, PGx |
| AF | ACC/AHA/HRS | CHA2DS2-VASc, anticoagulant selection |
| Rare disease | ACMG/AMP | Variant classification, genetic counseling |

---

## Precision Medicine Risk Score (0-100)

### Genetic Risk Component (0-35 points)

| Scenario | Points |
|----------|--------|
| Pathogenic variant in high-penetrance disease gene (BRCA1, LDLR, FBN1) | 30-35 |
| Multiple moderate-risk variants (GWAS hits + moderate penetrance) | 20-28 |
| High PRS (>90th percentile) with no known pathogenic variants | 25-30 |
| Single moderate-risk variant | 12-18 |
| VUS in relevant gene | 8-12 |
| Average PRS, no pathogenic variants | 5-10 |
| Low genetic risk (low PRS, no risk alleles) | 0-5 |

### Clinical Risk Component (0-30 points)

| Disease Type | Factor | Low (0-8) | Moderate (10-20) | High (22-30) |
|-------------|--------|-----------|------------------|-------------|
| Cancer | Stage | I | II-III | IV |
| T2D | HbA1c | <7% | 7-9% | >9% |
| CVD | ASCVD 10-yr | <10% | 10-20% | >20% |
| Neuro | Biomarker status | No biomarkers | Mild changes | Established |
| Rare | Phenotype match | Partial | Moderate | Full phenotype |

### Molecular Features Component (0-25 points)

| Feature | Points |
|---------|--------|
| Cancer: High-risk driver mutations (TP53+PIK3CA, KRAS G12C) | 20-25 |
| Cancer: Actionable mutation (EGFR, BRAF V600E) | 15-20 |
| Cancer: High TMB or MSI-H (favorable for ICI) | 10-15 |
| Metabolic: Monogenic form (MODY, FH) | 20-25 |
| Metabolic: Multiple metabolic risk variants | 10-15 |
| CVD: FH gene mutation | 20-25 |
| Rare: Complete genotype-phenotype match | 20-25 |
| VUS requiring further workup | 5-10 |

### Pharmacogenomic Risk Component (0-10 points)

| Finding | Points |
|---------|--------|
| Poor metabolizer for treatment-critical CYP + high-risk HLA | 10 |
| Poor metabolizer for treatment-critical CYP | 7-8 |
| Intermediate metabolizer for relevant CYP | 4-5 |
| Drug target variant (e.g., VKORC1 for warfarin) | 3-5 |
| No actionable PGx findings | 0-2 |

### Risk Tier Assignment

| Total Score | Risk Tier | Management Intensity |
|------------|-----------|---------------------|
| 75-100 | **VERY HIGH** | Intensive treatment, subspecialty referral, clinical trial enrollment |
| 50-74 | **HIGH** | Aggressive treatment, close monitoring, molecular tumor board |
| 25-49 | **INTERMEDIATE** | Standard treatment, guideline-based care, PGx-guided dosing |
| 0-24 | **LOW** | Surveillance, prevention, risk factor modification |

---

## Evidence Grading

| Tier | Level | Sources | Weight |
|------|-------|---------|--------|
| **T1** | Clinical/regulatory evidence | FDA labels, NCCN guidelines, PharmGKB Level 1A/1B, ClinVar pathogenic | Highest |
| **T2** | Strong experimental evidence | CIViC Level A/B, OpenTargets high-score, GWAS p<5e-8, clinical trials | High |
| **T3** | Moderate evidence | PharmGKB Level 2, CIViC Level C, GWAS suggestive, preclinical data | Moderate |
| **T4** | Computational/predicted | VEP predictions, pathway inference, network analysis, PRS estimates | Supportive |
