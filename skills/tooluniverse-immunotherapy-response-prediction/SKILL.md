---
name: tooluniverse-immunotherapy-response-prediction
description: Predict patient response to immune checkpoint inhibitors (ICIs) using multi-biomarker integration. Given a cancer type, somatic mutations, and optional biomarkers (TMB, PD-L1, MSI status), performs systematic analysis across 11 phases covering TMB classification, neoantigen burden estimation, MSI/MMR assessment, PD-L1 evaluation, immune microenvironment profiling, mutation-based resistance/sensitivity prediction, clinical evidence retrieval, and multi-biomarker score integration. Generates a quantitative ICI Response Score (0-100), response likelihood tier, specific ICI drug recommendations with evidence, resistance risk factors, and a monitoring plan. Use when oncologists ask about immunotherapy eligibility, checkpoint inhibitor selection, or biomarker-guided ICI treatment decisions.
---

# Immunotherapy Response Prediction

Predict patient response to immune checkpoint inhibitors (ICIs) using multi-biomarker integration. Transforms a patient tumor profile (cancer type + mutations + biomarkers) into a quantitative ICI Response Score with drug-specific recommendations, resistance risk assessment, and monitoring plan.

## Reasoning Before Searching

Not all tumors respond to checkpoint inhibitors. Reason through the biology before running tools:

- **TMB (tumor mutational burden)**: More somatic mutations produce more neoantigens, which are recognized by T cells. High TMB (>=10 mut/Mb, FDA-approved threshold for pembrolizumab) generally predicts better response — but this varies by cancer type (e.g., RCC responds despite low TMB).
- **MSI-H (microsatellite instability-high)**: Caused by defective DNA mismatch repair (MMR). MSI-H tumors have very high TMB and are pan-cancer approved for pembrolizumab. Check MLH1, MSH2, MSH6, PMS2 mutations.
- **PD-L1 expression**: The direct target of pembrolizumab/atezolizumab. High PD-L1 (TPS >=50% or CPS >=10 depending on cancer) predicts response in some cancers (NSCLC) but not all (melanoma, where TMB is more predictive).
- **Resistance factors** are equally important: STK11, KEAP1, JAK1/2 loss, B2M mutations can render an otherwise TMB-high tumor non-responsive.

Before calling any tool, determine which biomarkers are available for this patient and which are unknown. This determines which phases can be scored with data vs. must use cancer-type priors. Do not default to "moderate" for unknowns — flag them explicitly as missing.

**LOOK UP DON'T GUESS**: Never assume FDA approval for a biomarker-ICI combination — always verify with `fda_pharmacogenomic_biomarkers` or `FDA_get_indications_by_drug_name`. Cancer-specific thresholds differ from pan-cancer approvals.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Evidence-graded** - Every finding has an evidence tier (T1-T4)
3. **Quantitative output** - ICI Response Score (0-100) with transparent component breakdown
4. **Cancer-specific** - All thresholds and predictions are cancer-type adjusted
5. **Multi-biomarker** - Integrate TMB + MSI + PD-L1 + neoantigen + mutations
6. **Resistance-aware** - Always check for known resistance mutations (STK11, PTEN, JAK1/2, B2M)
7. **Drug-specific** - Recommend specific ICI agents with evidence
8. **Source-referenced** - Every statement cites the tool/database source
9. **English-first queries** - Always use English terms in tool calls

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks:
- "Will this patient respond to immunotherapy?"
- "Should I give pembrolizumab to this melanoma patient?"
- "Patient has NSCLC with TMB 25, PD-L1 80% - predict ICI response"
- "MSI-high colorectal cancer - which checkpoint inhibitor?"
- "Patient has BRAF V600E melanoma, TMB 15 - immunotherapy or targeted?"
- "Compare pembrolizumab vs nivolumab for this patient profile"

---

## Input Parsing

**Required**: Cancer type + at least one of: mutation list OR TMB value
**Optional**: PD-L1 expression, MSI status, immune infiltration data, HLA type, prior treatments, intended ICI

See [INPUT_REFERENCE.md](INPUT_REFERENCE.md) for input format examples, cancer type normalization, and gene symbol normalization tables.

---

## Workflow Overview

```
Input: Cancer type + Mutations/TMB + Optional biomarkers (PD-L1, MSI, etc.)

Phase 1: Input Standardization & Cancer Context
Phase 2: TMB Analysis
Phase 3: Neoantigen Analysis
Phase 4: MSI/MMR Status Assessment
Phase 5: PD-L1 Expression Analysis
Phase 6: Immune Microenvironment Profiling
Phase 7: Mutation-Based Predictors
Phase 8: Clinical Evidence & ICI Options
Phase 9: Resistance Risk Assessment
Phase 10: Multi-Biomarker Score Integration
Phase 11: Clinical Recommendations
```

---

## Phase 1: Input Standardization & Cancer Context

1. **Resolve cancer type** to EFO ID via `OpenTargets_get_disease_id_description_by_name`
2. **Parse mutations** into structured format: `{gene, variant, type}`
3. **Resolve gene IDs** via `MyGene_query_genes`
4. Look up cancer-specific ICI baseline ORR from the cancer context table (see [SCORING_TABLES.md](SCORING_TABLES.md))

## Phase 2: TMB Analysis

1. Classify TMB: Very-Low (<5), Low (5-9.9), Intermediate (10-19.9), High (>=20)
2. Check FDA TMB-H biomarker via `fda_pharmacogenomic_biomarkers(drug_name='pembrolizumab')`
3. Apply cancer-specific TMB thresholds (see [SCORING_TABLES.md](SCORING_TABLES.md))
4. Note: RCC responds to ICIs despite low TMB; TMB is less predictive in some cancers

## Phase 3: Neoantigen Analysis

1. Estimate neoantigen burden: missense_count * 0.3 + frameshift_count * 1.5
2. Check mutation impact via `UniProt_get_function_by_accession`
3. Query known epitopes via `iedb_search_epitopes`
4. POLE/POLD1 mutations indicate ultra-high neoantigen load

## Phase 4: MSI/MMR Status Assessment

1. Integrate MSI status if provided (MSI-H = 25 pts, MSS = 5 pts)
2. Check mutations in MMR genes: MLH1, MSH2, MSH6, PMS2, EPCAM
3. Check FDA MSI-H approvals via `fda_pharmacogenomic_biomarkers(biomarker='Microsatellite Instability')`

## Phase 5: PD-L1 Expression Analysis

1. Classify PD-L1: High (>=50%), Positive (1-49%), Negative (<1%)
2. Apply cancer-specific PD-L1 thresholds and scoring methods (TPS vs CPS)
3. Get baseline expression via `HPA_get_cancer_prognostics_by_gene(gene_name='CD274')`

## Phase 6: Immune Microenvironment Profiling

1. Query immune checkpoint gene expression for: CD274, PDCD1, CTLA4, LAG3, HAVCR2, TIGIT, CD8A, CD8B, GZMA, GZMB, PRF1, IFNG
2. Classify tumor: Hot (T cell inflamed), Cold (immune desert), Immune excluded, Immune suppressed
3. Run immune pathway enrichment via `enrichr_gene_enrichment_analysis`

## Phase 7: Mutation-Based Predictors

1. **Resistance mutations** (apply PENALTIES): STK11 (-10), PTEN (-5), JAK1/2 (-10 each), B2M (-15), KEAP1 (-5), MDM2/4 (-5), EGFR (-5)
2. **Sensitivity mutations** (apply BONUSES): POLE (+10), POLD1 (+5), BRCA1/2 (+3), ARID1A (+3), PBRM1 (+5 RCC only)
3. Check CIViC and OpenTargets for driver mutation ICI context
4. Check DDR pathway genes: ATM, ATR, CHEK1/2, BRCA1/2, PALB2, RAD50, MRE11

## Phase 8: Clinical Evidence & ICI Options

1. Query FDA indications for ICI drugs via `FDA_get_indications_by_drug_name`
2. Search clinical trials via `search_clinical_trials` (params: `condition`, `intervention`, `query_term`)
3. Search PubMed for biomarker-specific response data
4. Get drug mechanisms via `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`

See [SCORING_TABLES.md](SCORING_TABLES.md) for ICI drug profiles and ChEMBL IDs.

## Phase 9: Resistance Risk Assessment

1. Check CIViC for resistance evidence via `civic_search_evidence_items`
2. Assess pathway-level resistance: IFN-g signaling, antigen presentation, WNT/b-catenin, MAPK, PI3K/AKT/mTOR
3. Summarize risk: Low / Moderate / High

## Phase 10: Multi-Biomarker Score Integration

```
TOTAL SCORE = TMB_score + MSI_score + PDL1_score + Neoantigen_score + Mutation_bonus + Resistance_penalty

TMB_score:        5-30 points     MSI_score:        5-25 points
PDL1_score:       5-20 points     Neoantigen_score: 5-15 points
Mutation_bonus:   0-10 points     Resistance_penalty: -20 to 0 points

Floor: 0, Cap: 100
```

**Response Likelihood Tiers**:
- 70-100 HIGH (50-80% ORR): Strong ICI candidate
- 40-69 MODERATE (20-50% ORR): Consider ICI, combo preferred
- 0-39 LOW (<20% ORR): ICI alone unlikely effective

**Confidence**: HIGH (all 4 biomarkers), MODERATE-HIGH (3/4), MODERATE (2/4), LOW (1), VERY LOW (cancer only)

## Phase 11: Clinical Recommendations

1. **ICI drug selection** using cancer-specific algorithm (see [SCORING_TABLES.md](SCORING_TABLES.md))
2. **Monitoring plan**: CT/MRI q8-12wk, ctDNA at 4-6wk, thyroid/liver function, irAEs
3. **Alternative strategies** if LOW response: targeted therapy, chemotherapy, ICI+chemo combo, ICI+anti-angiogenic, ICI+CTLA-4 combo, clinical trials

---

## Output Report

Save as `immunotherapy_response_prediction_{cancer_type}.md`. See [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) for the full report structure.

---

## Tool Parameter Reference

**BEFORE calling ANY tool**, verify parameters. See [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) for verified tool parameters table.

Key reminders:
- `MyGene_query_genes`: use `query` (NOT `q`)
- `EnsemblVEP_annotate_rsid`: use `variant_id` (NOT `rsid`)
- `drugbank_*` tools: ALL 4 params required (`query`, `case_sensitive`, `exact_match`, `limit`)
- `cBioPortal_get_mutations`: `gene_list` is a STRING not array
- `ensembl_lookup_gene`: REQUIRES `species='homo_sapiens'`

---

## Evidence Tiers

| Tier | Description | Source Examples |
|------|-------------|----------------|
| T1 | FDA-approved biomarker/indication | FDA labels, NCCN guidelines |
| T2 | Phase 2-3 clinical trial evidence | Published trial data, PubMed |
| T3 | Preclinical/computational evidence | Pathway analysis, in vitro data |
| T4 | Expert opinion/case reports | Case series, reviews |

---

## References

- OpenTargets: https://platform.opentargets.org
- CIViC: https://civicdb.org
- FDA Drug Labels: https://dailymed.nlm.nih.gov
- DrugBank: https://go.drugbank.com
- PubMed: https://pubmed.ncbi.nlm.nih.gov
- IEDB: https://www.iedb.org
- HPA: https://www.proteinatlas.org
- cBioPortal: https://www.cbioportal.org
