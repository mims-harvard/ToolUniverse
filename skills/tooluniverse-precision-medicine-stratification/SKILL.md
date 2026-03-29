---
name: tooluniverse-precision-medicine-stratification
description: Comprehensive patient stratification for precision medicine by integrating genomic, clinical, and therapeutic data. Given a disease/condition, genomic data (germline variants, somatic mutations, expression), and optional clinical parameters, performs multi-phase analysis covering disease disambiguation, genetic risk assessment, disease-specific molecular stratification, pharmacogenomic profiling, comorbidity/DDI risk, pathway analysis, clinical evidence and guideline mapping, clinical trial matching, and integrated outcome prediction. Generates a quantitative Precision Medicine Risk Score (0-100) with risk tier assignment, treatment algorithm, pharmacogenomic guidance, clinical trial matches, and monitoring plan.
---

# Precision Medicine Patient Stratification

Transform patient genomic and clinical profiles into actionable risk stratification, treatment recommendations, and personalized therapeutic strategies.

## Reasoning Before Searching

Stratification means splitting patients into groups that respond differently to a treatment or have different prognoses. Ask these questions before running any tools:

1. **What molecular feature predicts response?** Candidates: somatic mutation (e.g., EGFR L858R), germline variant (e.g., BRCA1 LoF), expression level (e.g., HER2 overexpression), germline pharmacogenomic variant (e.g., CYP2C19 PM), or composite biomarker (e.g., TMB-H + MSI-H).
2. **Is the predictive feature actionable?** Knowing it must change treatment — either the drug choice, dose, or monitoring plan. A variant with prognostic value but no therapeutic consequence is not a stratification biomarker.
3. **What is the evidence level for the stratifier?** FDA-approved companion diagnostic (T1) vs. exploratory (T4) changes how much weight to place on the finding.

Route to the correct Phase 3 path BEFORE running Phase 2 tools — cancer, metabolic, CVD, rare disease, and autoimmune pipelines require different stratifiers.

**LOOK UP DON'T GUESS**: Never assume a variant is pathogenic, never assume a gene is relevant to a disease, never assign metabolizer status without PharmGKB or CPIC evidence.

**KEY PRINCIPLES**:
1. **Report-first** - Create report file FIRST, then populate progressively
2. **Disease-specific logic** - Cancer vs metabolic vs rare disease pipelines diverge at Phase 3
3. **Multi-level integration** - Germline + somatic + expression + clinical data layers
4. **Evidence-graded** - Every finding has an evidence tier (T1-T4)
5. **Quantitative output** - Precision Medicine Risk Score (0-100)
6. **Source-referenced** - Every statement cites the tool/database source
7. **English-first queries** - Always use English terms in tool calls

**Reference files** (same directory):
- `TOOLS_REFERENCE.md` - Tool parameters, response formats, phase-by-phase tool lists
- `SCORING_REFERENCE.md` - Scoring matrices, risk tiers, pathogenicity tables, PGx tables
- `REPORT_TEMPLATE.md` - Output report template, treatment algorithms, completeness requirements
- `EXAMPLES.md` - Six worked examples (cancer, metabolic, NSCLC, CVD, rare, neuro)
- `QUICK_START.md` - Sample prompts and output summary

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks about patient risk stratification, treatment selection, prognosis prediction, or personalized therapeutic strategy for any disease with genomic/clinical data.

**NOT for** (use other skills instead):
- Single variant interpretation -> `tooluniverse-variant-interpretation`
- Immunotherapy-specific prediction -> `tooluniverse-immunotherapy-response-prediction`
- Drug safety profiling only -> `tooluniverse-adverse-event-detection`
- Target validation -> `tooluniverse-drug-target-validation`
- Clinical trial search only -> `tooluniverse-clinical-trial-matching`
- Drug-drug interaction only -> `tooluniverse-drug-drug-interaction`
- PRS calculation only -> `tooluniverse-polygenic-risk-score`

---

## Input Parsing

### Required
- **Disease/condition**: Free-text disease name
- **At least one of**: Germline variants, somatic mutations, gene list, or clinical biomarkers

### Optional (improves stratification)
- Age, sex, ethnicity, disease stage, comorbidities, prior treatments, family history
- Current medications (for DDI and PGx), stratification goal

### Disease Type Classification

Classify into one category (determines Phase 3 routing):

| Category | Examples |
|----------|----------|
| **CANCER** | Breast, lung, colorectal, melanoma |
| **METABOLIC** | Type 2 diabetes, obesity, NAFLD |
| **CARDIOVASCULAR** | CAD, heart failure, AF |
| **NEUROLOGICAL** | Alzheimer, Parkinson, epilepsy |
| **RARE/MONOGENIC** | Marfan, CF, sickle cell, Huntington |
| **AUTOIMMUNE** | RA, lupus, MS, Crohn's |

---

## Critical Tool Parameter Notes

See `TOOLS_REFERENCE.md` for full details. Key gotchas:

- **MyGene_query_genes**: param is `query` (NOT `q`)
- **EnsemblVEP_annotate_rsid**: param is `variant_id` (NOT `rsid`)
- **ensembl_lookup_gene**: REQUIRES `species='homo_sapiens'`
- **DrugBank tools**: ALL require 4 params: `query`, `case_sensitive`, `exact_match`, `limit`
- **cBioPortal_get_mutations**: `gene_list` is a STRING (space-separated), not array
- **PubMed_search_articles**: Returns a plain list of dicts, NOT `{articles: [...]}`
- **fda_pharmacogenomic_biomarkers**: Use `limit=1000` for all results
- **gnomAD**: May return "Service overloaded" - skip gracefully
- **OpenTargets**: Always nested `{data: {entity: {field: ...}}}` structure

---

## Workflow Overview

```
Phase 1: Disease Disambiguation & Profile Standardization
Phase 2: Genetic Risk Assessment
Phase 3: Disease-Specific Molecular Stratification (routes by disease type)
Phase 4: Pharmacogenomic Profiling
Phase 5: Comorbidity & Drug Interaction Risk
Phase 6: Molecular Pathway Analysis
Phase 7: Clinical Evidence & Guidelines
Phase 8: Clinical Trial Matching
Phase 9: Integrated Scoring & Recommendations
```

---

## Phase 1: Disease Disambiguation & Profile Standardization

1. **Resolve disease to EFO ID** using `OpenTargets_get_disease_id_description_by_name`
2. **Classify disease type** (CANCER/METABOLIC/CVD/NEUROLOGICAL/RARE/AUTOIMMUNE)
3. **Parse genomic data** into structured format (gene, variant, type)
4. **Resolve gene IDs** using `MyGene_query_genes` to get Ensembl/Entrez IDs

## Phase 2: Genetic Risk Assessment

1. **Germline variant pathogenicity**: `ClinVar_search_variants`, `EnsemblVEP_annotate_rsid`/`_hgvs`
2. **Gene-disease association**: `OpenTargets_target_disease_evidence`
3. **GWAS polygenic risk**: `gwas_get_associations_for_trait`, `OpenTargets_search_gwas_studies_by_disease`
4. **Population frequency**: `gnomad_get_variant`
5. **Gene constraint**: `gnomad_get_gene_constraints` (pLI, LOEUF scores)

Scoring: See `SCORING_REFERENCE.md` for genetic risk score component (0-35 points).

## Phase 3: Disease-Specific Molecular Stratification

### CANCER PATH
1. **Molecular subtyping**: `cBioPortal_get_mutations`, `HPA_get_cancer_prognostics_by_gene`
2. **TMB/MSI/HRD**: `fda_pharmacogenomic_biomarkers` for FDA cutoffs
3. **Prognostic stratification**: Combine stage + molecular features

### METABOLIC PATH
1. **Genetic risk integration**: `GWAS_search_associations_by_gene`, `OpenTargets_target_disease_evidence`
2. **Complication risk**: Based on HbA1c, duration, existing complications

### CVD PATH
1. **FH gene check**: `ClinVar_search_variants` for LDLR, APOB, PCSK9
2. **Statin PGx**: `PharmGKB_get_clinical_annotations` for SLCO1B1

### RARE DISEASE PATH
1. **Causal variant identification**: `ClinVar_search_variants`
2. **Genotype-phenotype**: `UniProt_get_disease_variants_by_accession`

Scoring: See `SCORING_REFERENCE.md` for disease-specific tables.

## Phase 4: Pharmacogenomic Profiling

1. **Drug-metabolizing enzymes**: `PharmGKB_get_clinical_annotations`, `PharmGKB_get_dosing_guidelines`
2. **FDA PGx biomarkers**: `fda_pharmacogenomic_biomarkers` (use `limit=1000`)
3. **Treatment-specific PGx**: `PharmGKB_get_drug_details`

Scoring: See `SCORING_REFERENCE.md` for PGx risk score (0-10 points).

## Phase 5: Comorbidity & Drug Interaction Risk

1. **Disease overlap**: `OpenTargets_get_associated_targets_by_disease_efoId`
2. **DDI check**: `drugbank_get_drug_interactions_by_drug_name_or_id`, `FDA_get_drug_interactions_by_drug_name`
3. **PGx-amplified DDI**: If PM genotype + CYP inhibitor, flag compounded risk

## Phase 6: Molecular Pathway Analysis

1. **Pathway enrichment**: `enrichr_gene_enrichment_analysis` (libs: `KEGG_2021_Human`, `Reactome_2022`, `GO_Biological_Process_2023`)
2. **Reactome mapping**: `ReactomeAnalysis_pathway_enrichment`, `Reactome_map_uniprot_to_pathways`
3. **Network analysis**: `STRING_get_interaction_partners`, `STRING_functional_enrichment`
4. **Druggable targets**: `OpenTargets_get_target_tractability_by_ensemblID`

## Phase 7: Clinical Evidence & Guidelines

1. **Guidelines search**: `PubMed_Guidelines_Search` (fallback: `PubMed_search_articles`)
2. **FDA-approved therapies**: `OpenTargets_get_associated_drugs_by_disease_efoId`, `FDA_get_indications_by_drug_name`
3. **Biomarker-drug evidence**: `civic_search_evidence_items`, `civic_search_assertions`

## Phase 8: Clinical Trial Matching

1. **Biomarker-driven trials**: `search_clinical_trials` with condition + intervention
2. **Precision medicine trials**: `search_clinical_trials` for basket/umbrella trials

## Phase 9: Integrated Scoring & Recommendations

### Score Components (total 0-100)
- **Genetic Risk** (0-35): Pathogenicity + gene-disease association + PRS
- **Clinical Risk** (0-30): Stage/biomarkers/comorbidities
- **Molecular Features** (0-25): Driver mutations, subtypes, actionable targets
- **Pharmacogenomic Risk** (0-10): Metabolizer status, HLA alleles

### Risk Tiers
| Score | Tier | Management |
|-------|------|------------|
| 75-100 | VERY HIGH | Intensive treatment, subspecialty referral, clinical trial |
| 50-74 | HIGH | Aggressive treatment, close monitoring |
| 25-49 | INTERMEDIATE | Standard guideline-based care, PGx-guided dosing |
| 0-24 | LOW | Surveillance, prevention, risk factor modification |

### Output
Generate report per `REPORT_TEMPLATE.md`. See `SCORING_REFERENCE.md` for detailed scoring matrices.

---

## Common Use Patterns

See `EXAMPLES.md` for six detailed worked examples:
1. **Cancer + actionable mutation**: Breast cancer, BRCA1, ER+/HER2- -> Score ~55-65 (HIGH)
2. **Metabolic + PGx concern**: T2D, CYP2C19 PM on clopidogrel -> Score ~55-65 (HIGH)
3. **NSCLC comprehensive**: EGFR L858R, TMB 25, PD-L1 80% -> Score ~75-85 (VERY HIGH)
4. **CVD risk**: LDL 190, SLCO1B1*5, family hx MI -> Score ~50-60 (HIGH)
5. **Rare disease**: Marfan, FBN1 variant -> Score ~55-65 (HIGH)
6. **Neurological risk**: APOE e4/e4, family hx Alzheimer's -> Score ~60-72 (HIGH)
