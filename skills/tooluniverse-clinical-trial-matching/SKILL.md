---
name: tooluniverse-clinical-trial-matching
description: AI-driven patient-to-trial matching for precision medicine and oncology. Given a patient profile (disease, molecular alterations, stage, prior treatments), discovers and ranks clinical trials from ClinicalTrials.gov using multi-dimensional matching across molecular eligibility, clinical criteria, drug-biomarker alignment, evidence strength, and geographic feasibility. Produces a quantitative Trial Match Score (0-100) per trial with tiered recommendations and a comprehensive markdown report. Use when oncologists, molecular tumor boards, or patients ask about clinical trial options for specific cancer types, biomarker profiles, or post-progression scenarios.
---

# Clinical Trial Matching for Precision Medicine

Transform patient molecular profiles and clinical characteristics into prioritized clinical trial recommendations. Searches ClinicalTrials.gov and cross-references with molecular databases (CIViC, OpenTargets, ChEMBL, FDA) to produce evidence-graded, scored trial matches.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, then populate progressively
2. **Patient-centric** - Every recommendation considers the individual patient's profile
3. **Molecular-first matching** - Prioritize trials targeting patient's specific biomarkers

## Molecular Matching Priority

Match patients to trials by molecular profile FIRST (specific mutations), then by disease stage, then by prior treatments. A patient with EGFR L858R should match to EGFR-targeted trials regardless of other factors.
4. **Evidence-graded** - Every recommendation has an evidence tier (T1-T4)
5. **Quantitative scoring** - Trial Match Score (0-100) for every trial
6. **Eligibility-aware** - Parse and evaluate inclusion/exclusion criteria
7. **Actionable output** - Clear next steps, contact info, enrollment status
8. **Source-referenced** - Every statement cites the tool/database source
9. **Completeness checklist** - Mandatory section showing analysis coverage
10. **English-first queries** - Always use English terms in tool calls. Respond in user's language

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Apply when user asks:
- "What clinical trials are available for my NSCLC with EGFR L858R?"
- "Patient has BRAF V600E melanoma, failed ipilimumab - what trials?"
- "Find basket trials for NTRK fusion"
- "Breast cancer with HER2 amplification, post-CDK4/6 inhibitor trials"
- "KRAS G12C colorectal cancer clinical trials"
- "Immunotherapy trials for TMB-high solid tumors"
- "Clinical trials near Boston for lung cancer"
- "What are my options after failing osimertinib for EGFR+ NSCLC?"

**NOT for** (use other skills instead):
- Single variant interpretation without trial focus -> Use `tooluniverse-cancer-variant-interpretation`
- Drug safety profiling -> Use `tooluniverse-adverse-event-detection`
- Target validation -> Use `tooluniverse-drug-target-validation`
- General disease research -> Use `tooluniverse-disease-research`

---

## Input Parsing

### Required Input
- **Disease/cancer type**: Free-text disease name (e.g., "non-small cell lung cancer", "melanoma")

### Strongly Recommended
- **Molecular alterations**: One or more biomarkers (e.g., "EGFR L858R", "KRAS G12C", "PD-L1 50%", "TMB-high")
- **Stage/grade**: Disease stage (e.g., "Stage IV", "metastatic", "locally advanced")
- **Prior treatments**: Previous therapies and outcomes (e.g., "failed platinum chemotherapy", "progressed on osimertinib")

### Optional
- **Performance status**: ECOG or Karnofsky score
- **Geographic location**: City/state for proximity filtering
- **Trial phase preference**: I, II, III, IV, or "any"
- **Intervention type**: drug, biological, device, etc.
- **Recruiting status preference**: recruiting, not yet recruiting, active

For biomarker parsing rules and gene symbol normalization, see [MATCHING_ALGORITHMS.md](./MATCHING_ALGORITHMS.md).

---

## Workflow Overview

```
Input: Patient profile (disease + biomarkers + stage + prior treatments)

Phase 1: Patient Profile Standardization
  - Resolve disease to EFO/ontology IDs (OpenTargets, OLS)
  - Parse molecular alterations to gene + variant
  - Resolve gene symbols to Ensembl/Entrez IDs (MyGene)
  - Classify biomarker actionability (FDA-approved vs investigational)

Phase 2: Broad Trial Discovery
  - Disease-based trial search (ClinicalTrials.gov)
  - Biomarker-specific trial search
  - Intervention-based search (for known drugs targeting patient's biomarkers)
  - Deduplicate and collect NCT IDs

Phase 3: Trial Characterization (batch, groups of 10)
  - Eligibility criteria, conditions/interventions, locations, status, descriptions

Phase 4: Molecular Eligibility Matching
  - Parse eligibility text for biomarker requirements
  - Match patient's molecular profile to trial requirements
  - Score molecular eligibility (0-40 points)

Phase 5: Drug-Biomarker Alignment
  - Identify trial intervention drugs and mechanisms (OpenTargets, ChEMBL)
  - FDA approval status for biomarker-drug combinations
  - Classify drugs (targeted therapy, immunotherapy, chemotherapy)

Phase 6: Evidence Assessment
  - FDA-approved biomarker-drug combinations
  - Clinical trial results (PubMed), CIViC evidence, PharmGKB
  - Evidence tier classification (T1-T4)

Phase 7: Geographic & Feasibility Analysis
  - Trial site locations, enrollment status, proximity scoring

Phase 8: Alternative Options
  - Basket trials, expanded access, related studies

Phase 9: Scoring & Ranking (0-100 composite score)
  - Tier classification: Optimal (80-100) / Good (60-79) / Possible (40-59) / Exploratory (0-39)

Phase 10: Report Synthesis
  - Executive summary, ranked trial list, evidence grading, completeness checklist
```

---

## Critical Tool Parameters

### Clinical Trial Search Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `search_clinical_trials` | `query_term` (REQ), `condition`, `intervention`, `pageSize` | Main search |
| `search_clinical_trials` | `action="search_studies"` (REQ), `condition`, `intervention`, `limit` | Alternative search |
| `get_clinical_trial_descriptions` | `action="get_study_details"` (REQ), `nct_id` (REQ) | Full trial details |

### Batch Trial Detail Tools (all take `nct_ids` array)

| Tool | Second Required Param | Returns |
|------|----------------------|---------|
| `get_clinical_trial_eligibility_criteria` | `eligibility_criteria="all"` | Eligibility text |
| `get_clinical_trial_locations` | `location="all"` | Site locations |
| `get_clinical_trial_conditions_and_interventions` | `condition_and_intervention="all"` | Arms/interventions |
| `get_clinical_trial_status_and_dates` | `status_and_date="all"` | Status/dates |
| `get_clinical_trial_descriptions` | `description_type="brief"` or `"full"` | Titles/summaries |
| `get_clinical_trial_outcome_measures` | `outcome_measures="all"` | Outcomes |

### Gene/Disease Resolution

| Tool | Key Parameters |
|------|---------------|
| `MyGene_query_genes` | `query`, `species` |
| `OpenTargets_get_disease_id_description_by_name` | `diseaseName` |
| `OpenTargets_get_target_id_description_by_name` | `targetName` |
| `ols_search_efo_terms` | `query`, `limit` |

### Drug Information

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `OpenTargets_get_drug_id_description_by_name` | `drugName` | Resolve drug to ChEMBL ID |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | Drug MoA and targets |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | `ensemblId`, `size` | Drugs for a target |
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQ) | Drug targets |
| `fda_pharmacogenomic_biomarkers` | (none) | FDA biomarker-drug list |
| `FDA_get_indications_by_drug_name` | `drug_name`, `limit` | FDA indications |

### Evidence Tools

| Tool | Key Parameters |
|------|---------------|
| `PubMed_search_articles` | `query`, `max_results` |
| `civic_get_variants_by_gene` | `gene_id` (CIViC int ID), `limit` |
| `PharmGKB_search_genes` | `query` |

### Known CIViC Gene IDs

EGFR=19, BRAF=5, ALK=1, ABL1=4, KRAS=30, TP53=45, ERBB2=20, NTRK1=197, NTRK2=560, NTRK3=561, PIK3CA=37, MET=52, ROS1=118, RET=122, BRCA1=2370, BRCA2=2371

### Critical Parameter Notes

1. **DrugBank tools**: ALL 4 parameters (`query`, `case_sensitive`, `exact_match`, `limit`) are REQUIRED
2. **`search_clinical_trials`**: `query_term` is REQUIRED even for disease-only searches
3. **`search_clinical_trials`**: `action` must be exactly `"search_studies"`
4. **CIViC `civic_search_variants`**: Does NOT filter by query - returns alphabetically
5. **CIViC `civic_get_variants_by_gene`**: Takes CIViC gene ID (integer), NOT gene symbol
6. **Batch clinical trial tools**: Accept arrays of NCT IDs, process in batches of 10

---

## Scoring Summary

**Trial Match Score (0-100)**:
- Molecular Match: 0-40 pts (exact variant=40, gene-level=30, pathway=20, none=10, excluded=0)
- Clinical Eligibility: 0-25 pts (all met=25, most=18, some=10, ineligible=0)
- Evidence Strength: 0-20 pts (FDA-approved=20, Phase III=15, Phase II=10, Phase I=5)
- Trial Phase: 0-10 pts (III=10, II=8, I/II=6, I=4)
- Geographic: 0-5 pts (local=5, same country=3, international=1)

**Recommendation Tiers**: Optimal (80-100), Good (60-79), Possible (40-59), Exploratory (0-39)

**Evidence Tiers**: T1 (FDA/guideline), T2 (Phase III), T3 (Phase I/II), T4 (computational)

For detailed scoring logic, see [SCORING_CRITERIA.md](./SCORING_CRITERIA.md).

---

## Parallelization Strategy

**Group 1** (Phase 1 - simultaneous):
- `MyGene_query_genes` per gene, `OpenTargets` disease search, `ols_search_efo_terms`, `fda_pharmacogenomic_biomarkers`

**Group 2** (Phase 2 - simultaneous):
- `search_clinical_trials` by disease, biomarker, and intervention; `search_clinical_trials` alternative

**Group 3** (Phase 3 - simultaneous):
- All batch detail tools (eligibility, interventions, locations, status, descriptions)

**Group 4** (Phases 5-6 - per drug):
- Drug resolution, MoA, FDA indications, PubMed evidence

---

## Error Handling

1. Wrap every tool call in try/except
2. Check for empty results and string error responses
3. Use fallback tools when primary fails (e.g., OLS if OpenTargets fails)
4. Document failures in completeness checklist
5. Never let one failure block the entire analysis

---

## Reference Files

| File | Contents |
|------|----------|
| [TOOLS_REFERENCE.md](./TOOLS_REFERENCE.md) | Full tool inventory with parameters and response structures |
| [MATCHING_ALGORITHMS.md](./MATCHING_ALGORITHMS.md) | Patient profile standardization, biomarker parsing, molecular eligibility matching, drug-biomarker alignment code |
| [SCORING_CRITERIA.md](./SCORING_CRITERIA.md) | Detailed scoring tables, molecular match logic, drug-biomarker alignment scoring |
| [REPORT_TEMPLATE.md](./REPORT_TEMPLATE.md) | Full markdown report template with all sections |
| [TRIAL_SEARCH_PATTERNS.md](./TRIAL_SEARCH_PATTERNS.md) | Search functions, batch retrieval, parallelization, common use patterns, edge cases |
| [EXAMPLES.md](./EXAMPLES.md) | Worked examples for different matching scenarios |
| [QUICK_START.md](./QUICK_START.md) | Quick-start guide for common workflows |
