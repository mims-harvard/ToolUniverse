# Clinical Trial Matching - Tools Reference

## Summary

This skill uses **40+ ToolUniverse tools** across 10 categories to perform comprehensive clinical trial matching.

## Tool Inventory

### Clinical Trial Tools (13 total, 11 primary)

| Tool | Purpose | Key Parameters | Response |
|------|---------|---------------|----------|
| `search_clinical_trials` | Main trial search | `query_term` (REQ), `condition`, `intervention`, `pageSize` | `{studies, nextPageToken, total_count}` |
| `clinical_trials_search` | Alternative search | `action="search_studies"` (REQ), `condition`, `intervention`, `limit` | `{total_count, studies}` |
| `clinical_trials_get_details` | Full trial details | `action="get_study_details"` (REQ), `nct_id` (REQ) | Full study object |
| `get_clinical_trial_eligibility_criteria` | Eligibility text | `nct_ids` (REQ array), `eligibility_criteria` (REQ) | `[{NCT ID, eligibility_criteria}]` |
| `get_clinical_trial_locations` | Site locations | `nct_ids` (REQ array), `location` (REQ) | `[{NCT ID, locations}]` |
| `get_clinical_trial_descriptions` | Title/summary | `nct_ids` (REQ array), `description_type` (REQ) | `[{NCT ID, brief_title, ...}]` |
| `get_clinical_trial_status_and_dates` | Status/dates | `nct_ids` (REQ array), `status_and_date` (REQ) | `[{NCT ID, overall_status, dates}]` |
| `get_clinical_trial_conditions_and_interventions` | Interventions | `nct_ids` (REQ array), `condition_and_intervention` (REQ) | `[{NCT ID, condition, arm_groups, interventions}]` |
| `get_clinical_trial_outcome_measures` | Outcomes | `nct_ids` (REQ array), `outcome_measures` | `[{NCT ID, outcomes}]` |
| `extract_clinical_trial_outcomes` | Result data | `nct_ids` (REQ array) | Outcome result data |
| `extract_clinical_trial_adverse_events` | AE data | `nct_ids` (REQ array) | Adverse event data |

### OpenTargets Tools (10 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `OpenTargets_get_disease_id_description_by_name` | Resolve disease | `diseaseName` |
| `OpenTargets_get_target_id_description_by_name` | Resolve target | `targetName` |
| `OpenTargets_get_drug_id_description_by_name` | Resolve drug | `drugName` |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | Drug MoA | `chemblId` |
| `OpenTargets_get_associated_drugs_by_target_ensemblID` | Drugs for target | `ensemblId`, `size` |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | Drugs for disease | `efoId`, `size` |
| `OpenTargets_get_approved_indications_by_drug_chemblId` | Approved indications | `chemblId` |
| `OpenTargets_get_drug_approval_status_by_chemblId` | Approval status | `chemblId` |
| `OpenTargets_target_disease_evidence` | Target-disease evidence | `ensemblId`, `efoId`, `size` |
| `OpenTargets_get_drug_description_by_chemblId` | Drug description | `chemblId` |

### CIViC Tools (6 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `civic_get_variants_by_gene` | Gene variants | `gene_id` (CIViC int), `limit` |
| `civic_get_variant` | Variant details | `variant_id` |
| `civic_search_evidence_items` | Evidence search | `query`, `limit` |
| `civic_search_therapies` | Therapy search | `query`, `limit` |
| `civic_search_diseases` | Disease search | `query`, `limit` |
| `civic_get_molecular_profile` | Molecular profile | `molecular_profile_id` |

### FDA Tools (5 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `fda_pharmacogenomic_biomarkers` | Biomarker-drug list | (none) |
| `FDA_get_indications_by_drug_name` | Drug indications | `drug_name`, `limit` |
| `FDA_get_mechanism_of_action_by_drug_name` | Drug MoA | `drug_name`, `limit` |
| `FDA_get_clinical_studies_info_by_drug_name` | Clinical studies | `drug_name`, `limit` |
| `FDA_get_adverse_reactions_by_drug_name` | Drug safety | `drug_name`, `limit` |

### Gene/Disease Resolution Tools (4 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `MyGene_query_genes` | Gene ID resolution | `query`, `species` |
| `ols_search_efo_terms` | Disease ontology | `query`, `limit` |
| `ols_get_efo_term` | Term details | `term_id` |
| `ols_get_efo_term_children` | Sub-diseases | `term_id` |

### Drug Information Tools (4 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | Drug targets | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQ) |
| `drugbank_get_indications_by_drug_name_or_drugbank_id` | Drug indications | `query`, `case_sensitive`, `exact_match`, `limit` (ALL REQ) |
| `ChEMBL_search_drugs` | Drug search | `query`, `limit` |
| `ChEMBL_get_drug_mechanisms` | Drug mechanisms | `drug_chembl_id__exact` |

### Literature Tools (2 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `PubMed_search_articles` | Literature search | `query`, `max_results` |
| `openalex_literature_search` | Literature search | `query`, `limit` |

### PharmGKB Tools (2 primary)

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `PharmGKB_search_genes` | Gene pharmacogenomics | `query` |
| `PharmGKB_get_clinical_annotations` | Clinical annotations | `query` |

## Critical Parameter Notes

1. **DrugBank tools**: ALL 4 parameters (`query`, `case_sensitive`, `exact_match`, `limit`) are REQUIRED
2. **`search_clinical_trials`**: `query_term` is REQUIRED even for disease-only searches
3. **`clinical_trials_search`**: `action` must be exactly `"search_studies"`
4. **`clinical_trials_get_details`**: `action` must be exactly `"get_study_details"`
5. **CIViC `civic_search_variants`**: Does NOT filter by query - returns alphabetically
6. **CIViC `civic_get_variants_by_gene`**: Takes CIViC gene ID (integer), NOT gene symbol
7. **OpenTargets drug lookup**: Use `drugName` (NOT `genericName`)
8. **Batch clinical trial tools**: Accept arrays of NCT IDs
9. **`fda_pharmacogenomic_biomarkers`**: Takes no parameters

## Response Structure Cheat Sheet

```
search_clinical_trials:
  {studies: [{NCT ID, brief_title, brief_summary, overall_status, condition: [], phase: []}], nextPageToken, total_count}

clinical_trials_search:
  {total_count, studies: [{nctId, title, status, conditions: []}]}

get_clinical_trial_eligibility_criteria:
  [{NCT ID, eligibility_criteria: "Inclusion Criteria:\n...\nExclusion Criteria:\n..."}]

get_clinical_trial_locations:
  [{NCT ID, locations: [{facility, city, state, country}]}]

get_clinical_trial_conditions_and_interventions:
  [{NCT ID, condition: [], arm_groups: [{label, type, description, interventionNames}], interventions: [{type, name, description}]}]

get_clinical_trial_status_and_dates:
  [{NCT ID, overall_status, start_date, primary_completion_date, completion_date}]

OpenTargets_get_drug_mechanisms_of_action_by_chemblId:
  {data: {drug: {id, name, mechanismsOfAction: {rows: [{mechanismOfAction, actionType, targetName, targets: [{id, approvedSymbol}]}]}}}}

OpenTargets_get_associated_drugs_by_target_ensemblID:
  {data: {target: {id, approvedSymbol, knownDrugs: {count, rows: [{drug: {id, name, isApproved}, phase, mechanismOfAction, disease: {id, name}}]}}}}

fda_pharmacogenomic_biomarkers:
  {count, shown, results: [{Drug, TherapeuticArea, Biomarker, LabelingSection}]}

MyGene_query_genes:
  {hits: [{symbol, entrezgene, ensembl: {gene}, name}]}

PubMed_search_articles:
  [{pmid, title, abstract, authors, journal, pub_date}]
```
