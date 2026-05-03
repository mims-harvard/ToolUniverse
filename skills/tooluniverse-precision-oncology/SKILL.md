---
name: tooluniverse-precision-oncology
description: Provide actionable treatment recommendations for cancer patients based on molecular profile. Interprets tumor mutations, identifies FDA-approved therapies, finds resistance mechanisms, matches clinical trials. Use when oncologist asks about treatment options for specific mutations (EGFR, KRAS, BRAF, etc.), therapy resistance, or clinical trial eligibility.
---

# Precision Oncology Treatment Advisor

Provide actionable treatment recommendations for cancer patients based on their molecular profile using CIViC, ClinVar, OpenTargets, ClinicalTrials.gov, and structure-based analysis.

## Domain Reasoning

Treatment selection follows a strict evidence hierarchy: FDA-approved for this specific mutation in this cancer type ranks highest, followed by approval for this mutation in any cancer (tumor-agnostic), then active clinical trials, and finally off-label use. Skipping this hierarchy to recommend off-label therapies when an approved option exists is a clinical error. Always check current NCCN guidelines and recent literature, as approvals change rapidly — a drug that was investigational last year may now be first-line.

When looking up treatment for a specific mutation, search CIViC and OncoKB FIRST, not PubMed. These databases have curated evidence levels. PubMed is for when curated databases don't have the answer.

## Treatment Selection Reasoning

**Biomarker-to-drug logic** — When a biomarker is identified, the first-line targeted therapy follows established mappings. Always verify current approval status via OncoKB/CIViC, but use this as a starting framework:
- **NSCLC**: EGFR exon 19 del / L858R → osimertinib (1L); ALK fusion → alectinib/lorlatinib; ROS1 fusion → crizotinib/entrectinib; KRAS G12C → sotorasib/adagrasib; MET exon 14 skip → capmatinib/tepotinib; RET fusion → selpercatinib; BRAF V600E → dabrafenib+trametinib; NTRK fusion → larotrectinib/entrectinib (tumor-agnostic)
- **Breast**: HER2+ → trastuzumab+pertuzumab (1L), T-DXd (2L); HR+/HER2- → CDK4/6i (palbociclib/ribociclib) + AI; BRCA1/2 mut → olaparib/talazoparib; PIK3CA mut → alpelisib+fulvestrant
- **Colorectal**: BRAF V600E → encorafenib+cetuximab; MSI-H/dMMR → pembrolizumab (tumor-agnostic); KRAS/NRAS wild-type → cetuximab/panitumumab (anti-EGFR)
- **Melanoma**: BRAF V600E/K → dabrafenib+trametinib or encorafenib+binimetinib; wild-type → immunotherapy (nivolumab+ipilimumab)
- **Tumor-agnostic**: MSI-H/dMMR → pembrolizumab; NTRK fusion → larotrectinib; TMB-H (>=10 mut/Mb) → pembrolizumab; RET fusion → selpercatinib

**Resistance mechanism reasoning** — When a patient progresses on targeted therapy, distinguish primary resistance (never responded — check if the mutation was truly the driver, or if co-mutations like TP53/RB1 abrogate response) from acquired resistance (responded then progressed — on-target mutations or bypass activation). Common patterns:
- **EGFR TKIs**: 1st/2nd-gen resistance → T790M (50-60%); osimertinib resistance → C797S (10-25%), MET amp (15-20%), HER2 amp, histologic transformation (SCLC ~5%)
- **ALK TKIs**: crizotinib resistance → ALK secondary mutations (L1196M, G1269A); alectinib resistance → G1202R (solvent front); lorlatinib resistance → compound mutations
- **BRAF inhibitors**: MAPK reactivation (MEK mutations, BRAF amplification, NRAS mutations), PI3K/AKT bypass
- **Anti-HER2**: HER2 truncation (p95HER2), PIK3CA activation, HER3 upregulation
- **Immunotherapy (anti-PD1)**: B2M loss (MHC-I loss), JAK1/2 loss-of-function (IFN-gamma signaling escape), WNT/beta-catenin activation (T-cell exclusion)
For resistance workup: query `civic_search_evidence_items` with the drug name + "resistance", then `PubMed_search_articles` for recent mechanisms.

## LOOK UP DON'T GUESS

- FDA approval status for a mutation-drug pair: query `OncoKB_annotate_variant` and `civic_search_variants`; never assume approval status from memory.
- Active clinical trials: search `search_clinical_trials` with the specific condition and mutation; do not cite trials from memory.
- Resistance mechanisms for specific drugs: query `civic_search_evidence_items` and `PubMed_search_articles`; do not assume resistance pathways.
- Variant frequency in TCGA: retrieve from `GDC_get_mutation_frequency` or `cBioPortal_get_mutations`; do not estimate prevalence.

---

**KEY PRINCIPLES**:
1. **Report-first** - Create report file FIRST, update progressively
2. **Evidence-graded** - Every recommendation has evidence level
3. **Actionable output** - Prioritized treatment options, not data dumps
4. **Clinical focus** - Answer "what should we do?" not "what exists?"
5. **English-first queries** - Always use English terms in tool calls (mutations, drug names, cancer types), even if the user writes in another language. Only try original-language terms as a fallback. Respond in the user's language

---

## When to Use

- "Patient has [cancer] with [mutation] - what treatments?"
- "What are options for EGFR-mutant lung cancer?"
- "Patient failed [drug], what's next?"
- "Clinical trials for KRAS G12C?"
- "Why isn't [drug] working anymore?"

---

## Phase 0: Tool Verification

| Tool | WRONG | CORRECT |
|------|-------|---------|
| `civic_get_variant` | `variant_name` | `variant_id` (numeric, e.g., 4170) |
| `civic_get_evidence_item` | `variant_id` | `id` (numeric) |
| `OpenTargets_*` | `ensemblID` | `ensemblId` (camelCase) |
| `search_clinical_trials` | `disease` | `condition` |

---

## Workflow Overview

```
Input: Cancer type + Molecular profile (mutations, fusions, amplifications)

Phase 1: Profile Validation -> Resolve gene IDs (Ensembl, UniProt, ChEMBL)
Phase 2: Variant Interpretation -> CIViC, ClinVar, COSMIC, GDC/TCGA, DepMap, OncoKB, cBioPortal, HPA
Phase 2.5: Tumor Expression -> CELLxGENE cell-type expression, ChIPAtlas regulatory context
Phase 3: Treatment Options -> OpenTargets + DailyMed (approved), ChEMBL (off-label)
Phase 3.5: Pathway & Network -> KEGG/Reactome pathways, IntAct interactions
Phase 4: Resistance Analysis -> CIViC + PubMed + NvidiaNIM structure analysis
Phase 5: Clinical Trials -> ClinicalTrials.gov search + eligibility
Phase 5.5: Literature -> PubMed, BioRxiv/MedRxiv preprints, OpenAlex citations
Phase 6: Report Synthesis -> Executive summary + prioritized recommendations
```

---

## Key Tools by Phase

### Phase 1: Profile Validation
- `MyGene_query_genes` - Resolve gene to Ensembl ID
- `UniProt_search` - Get UniProt accession
- `ChEMBL_search_targets` - Get ChEMBL target ID

### Phase 2: Variant Interpretation
- `civic_search_variants` / `civic_get_variant` - CIViC evidence
- `COSMIC_get_mutations_by_gene` / `COSMIC_search_mutations` - Somatic mutations
- `GDC_get_mutation_frequency` / `GDC_get_ssm_by_gene` - TCGA patient data
- `GDC_get_gene_expression` / `GDC_get_cnv_data` - Expression and CNV
- `GDC_get_survival` - Kaplan-Meier survival data by project and optional gene mutation filter
- `GDC_get_clinical_data` - TCGA clinical metadata (stage, vital status, treatment, demographics)
- `Progenetix_cnv_search` - Copy number variation biosamples by genomic region and cancer type (NCIt code)
- `DepMap_get_gene_dependencies` / `PharmacoDB_get_experiments` - Target essentiality
- `OncoKB_annotate_variant` / `OncoKB_get_gene_info` - Actionability
- `cBioPortal_get_mutations` / `cBioPortal_get_cancer_studies` - Cross-study data
- `HPA_search_genes_by_query` / `HPA_get_comparative_expression_by_gene_and_cellline` - Expression

### Phase 2.5: Tumor Expression
- `CELLxGENE_get_expression_data` / `CELLxGENE_get_cell_metadata` - Cell-type expression

### Phase 3: Treatment Options
- `OpenTargets_get_associated_drugs_by_target_ensemblID` - Approved drugs (param: `ensemblId`, camelCase)
- `DGIdb_get_drug_gene_interactions` - Drug-gene interactions (param: `genes` as array, e.g., `["EGFR"]`). Comprehensive; covers inhibitors, antibodies, and investigational agents.
- `DailyMed_search_spls` - FDA label details
- `ChEMBL_get_drug_mechanisms` - Drug mechanism

### Phase 3.5: Pathway & Network
- `kegg_find_genes` / `kegg_get_gene_info` - KEGG pathways
- `reactome_disease_target_score` - Reactome disease relevance
- `intact_get_interaction_network` - Protein interactions

### Phase 4: Resistance Analysis
- `civic_search_evidence_items` - Search by known resistance mutations individually (e.g., `molecular_profile="EGFR C797S"`, `molecular_profile="MET Amplification"`). The `significance` field in results indicates Resistance/Sensitivity — filter on it after retrieval.
- `PubMed_search_articles` - Resistance literature (e.g., "osimertinib resistance C797S combination therapy")
- `alphafold_get_prediction` / `get_diffdock_info` - Structure-based analysis (AlphaFold for structure, DiffDock for docking)

### Phase 5: Clinical Trials
- `search_clinical_trials` - Find trials (param: `condition`, NOT `disease`)
- `get_clinical_trial_eligibility_criteria` - Eligibility details

### Phase 5.5: Safety & Pharmacogenomics
- `FAERS_search_adverse_event_reports` - Real-world adverse events (param: `medicinalproduct`). Check for serious AEs, death rates, common toxicities.
- `FAERS_count_death_related_by_drug` - Mortality signal for a drug
- `FDA_get_warnings_and_cautions_by_drug_name` - FDA label safety info
- `CPIC_list_guidelines` - Check for relevant PGx guidelines (e.g., DPYD for fluoropyrimidines in chemo regimens, UGT1A1 for irinotecan). No CPIC guidelines exist for EGFR TKIs.
- `fda_pharmacogenomic_biomarkers` - FDA-labeled PGx biomarkers for the drug

> **OncoKB demo mode**: Without `ONCOKB_API_TOKEN` env var, OncoKB only covers BRAF, TP53, ROS1. For other genes (EGFR, KRAS, ALK, etc.), set the API key or use CIViC as the primary evidence source.

### Phase 6: Literature
- `PubMed_search_articles` - Published evidence (use `limit`, `mindate`, `maxdate` for date filtering)
- `BioRxiv_list_recent_preprints` / `MedRxiv_get_preprint` - Preprints (flag as NOT peer-reviewed)
- `openalex_search_works` - Citation analysis

---

## Cross-Skill References

For CYP interaction with cancer drugs, run: `python3 skills/tooluniverse-drug-drug-interaction/scripts/pharmacology_ref.py --type cyp_substrate --drug drugname`

---

## References

- [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md) - Complete tool documentation with parameters and examples
- [API_USAGE_PATTERNS.md](API_USAGE_PATTERNS.md) - Detailed code examples for each phase
- [TREATMENT_ALGORITHMS.md](TREATMENT_ALGORITHMS.md) - Evidence grading, treatment prioritization, cancer type mappings, DepMap interpretation
- [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) - Report template with output tables
- [EXAMPLES.md](EXAMPLES.md) - Worked examples (EGFR NSCLC, T790M resistance, KRAS G12C, no actionable mutations)
- [CHECKLIST.md](CHECKLIST.md) - Quality and completeness checklist
