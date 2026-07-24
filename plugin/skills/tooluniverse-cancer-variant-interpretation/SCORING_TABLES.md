# Cancer Variant Interpretation - Evidence Grading & Scoring

## Evidence Level Mapping (CIViC)

| CIViC Level | Tier | Meaning | Clinical Action |
|-------------|------|---------|-----------------|
| A | T1 (highest) | FDA-approved, guideline | Standard of care |
| B | T2 | Clinical evidence | Strong recommendation |
| C | T2 | Case study | Consider with caution |
| D | T3 | Preclinical | Research context only |
| E | T4 | Inferential | Computational evidence |

## Treatment Prioritization

| Priority | Criteria | Tier |
|----------|----------|------|
| **1st Line** | FDA-approved for exact indication + biomarker | T1 |
| **2nd Line** | FDA-approved for different indication, same biomarker | T1-T2 |
| **3rd Line** | Phase 3 clinical trial data | T2 |
| **4th Line** | Phase 1-2 data, off-label with evidence | T3 |
| **5th Line** | Preclinical or computational only | T4 |

## Evidence Grading System

| Tier | Symbol | Criteria | Examples |
|------|--------|----------|---------|
| **T1** | [T1] | FDA-approved therapy, Level A CIViC evidence, phase 3 trial | Osimertinib for EGFR T790M |
| **T2** | [T2] | Phase 2/3 clinical data, Level B CIViC evidence | Combination trial data |
| **T3** | [T3] | Preclinical data, Level D CIViC, case reports | Novel mechanisms, in vitro |
| **T4** | [T4] | Computational prediction, pathway inference | Docking, pathway analysis |

## Clinical Actionability Scoring

| Score | Criteria |
|-------|----------|
| **HIGH** | FDA-approved targeted therapy exists for this exact mutation + cancer type |
| **MODERATE** | Approved therapy exists for different cancer type with same mutation, OR phase 2-3 trial data |
| **LOW** | Only preclinical evidence or pathway-based rationale |
| **UNKNOWN** | Insufficient data to assess actionability |

## Fallback Chains

| Primary Tool | Fallback | Use When |
|-------------|----------|----------|
| CIViC variant lookup | PubMed literature search | Gene not found in CIViC (search doesn't filter) |
| OpenTargets drugs | ChEMBL drug search | No OpenTargets drug hits |
| FDA indications | DrugBank drug info | Drug not in FDA database |
| cBioPortal TCGA study | cBioPortal pan-cancer | Specific cancer study not available |
| GTEx expression | Ensembl gene lookup | GTEx returns empty |
| Reactome pathways | UniProt function | Pathway mapping fails |

## Quantified Minimums

| Section | Requirement |
|---------|-------------|
| Gene IDs | At least Ensembl + UniProt resolved |
| Clinical evidence | CIViC queried + PubMed literature search |
| Mutation prevalence | At least 1 cBioPortal study |
| Therapeutic options | All approved drugs listed (OpenTargets) + FDA label for top drugs |
| Resistance | Literature search performed + known patterns documented |
| Clinical trials | At least 1 search query executed |
| Prognostic impact | PubMed literature search performed |
| Pathway context | Reactome pathway mapping attempted |

## Common Use Cases

### Use Case 1: Oncologist Evaluating Treatment Options

**Input**: "EGFR L858R in lung adenocarcinoma"

**Expected Output**: Report showing osimertinib as 1st-line [T1], with FDA label details, resistance pattern (T790M), clinical trials for combination therapies, and prognostic context.

### Use Case 2: Molecular Tumor Board Preparation

**Input**: "BRAF V600E, colorectal cancer"

**Expected Output**: Report noting that BRAF V600E is actionable in melanoma but requires combination therapy in CRC (encorafenib + cetuximab), with different resistance patterns than melanoma.

### Use Case 3: Clinical Trial Matching

**Input**: "KRAS G12C, any cancer type"

**Expected Output**: Report with sotorasib/adagrasib as approved options [T1], comprehensive trial listing for KRAS G12C inhibitors, resistance patterns (Y96D, etc.), and mutation prevalence across cancer types.

### Use Case 4: Resistance Mechanism Investigation

**Input**: "EGFR T790M after osimertinib failure"

**Expected Output**: Report focused on C797S resistance mutation, available 4th-generation TKI trials, amivantamab/lazertinib combinations, and bypass pathway mechanisms (MET amplification, HER2 activation).

### Use Case 5: VUS Interpretation

**Input**: "PIK3CA E545K"

**Expected Output**: Report showing this is a known hotspot oncogenic mutation (not a VUS), with alpelisib as FDA-approved therapy for HR+/HER2- breast cancer, and prevalence data across cancer types.
