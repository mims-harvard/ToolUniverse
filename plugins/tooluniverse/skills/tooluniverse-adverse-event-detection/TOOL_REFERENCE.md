# Adverse Event Detection - Tool Parameter Reference

Verified parameter names, response formats, and fallback chains for all tools used in this skill.

---

## FAERS Tools (OpenFDA-based)

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `FAERS_count_reactions_by_drug_event` | `medicinalproduct` (REQUIRED), `patientsex`, `patientagegroup`, `occurcountry` | Returns [{term, count}] |
| `FAERS_count_seriousness_by_drug_event` | `medicinalproduct` (REQUIRED), `patientsex`, `patientagegroup`, `occurcountry` | Returns [{term: "Serious"/"Non-serious", count}] |
| `FAERS_count_outcomes_by_drug_event` | `medicinalproduct` (REQUIRED), `patientsex`, `patientagegroup`, `occurcountry` | Returns [{term: "Fatal"/"Recovered"/..., count}] |
| `FAERS_count_patient_age_distribution` | `medicinalproduct` (REQUIRED) | Returns [{term: "Elderly"/"Adult"/..., count}] |
| `FAERS_count_death_related_by_drug` | `medicinalproduct` (REQUIRED) | Returns [{term: "alive"/"death", count}] |
| `FAERS_count_reportercountry_by_drug_event` | `medicinalproduct` (REQUIRED), `patientsex`, `patientagegroup`, `serious` | Returns [{term: "US"/"GB"/..., count}] |
| `FAERS_search_adverse_event_reports` | `medicinalproduct`, `limit` (max 100), `skip` | Returns individual case reports with patient/drug/reaction data |
| `FAERS_search_reports_by_drug_and_reaction` | `medicinalproduct` (REQUIRED), `reactionmeddrapt` (REQUIRED), `limit`, `skip`, `patientsex`, `serious` | Returns individual reports filtered by specific reaction |
| `FAERS_search_serious_reports_by_drug` | `medicinalproduct` (REQUIRED), `seriousnessdeath`, `seriousnesshospitalization`, `seriousnesslifethreatening`, `seriousnessdisabling`, `limit` | Returns serious event reports |

## FAERS Analytics Tools (operation-based)

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `FAERS_calculate_disproportionality` | `operation`="calculate_disproportionality", `drug_name` (REQUIRED), `adverse_event` (REQUIRED) | Returns PRR, ROR, IC with 95% CI and signal detection |
| `FAERS_analyze_temporal_trends` | `operation`="analyze_temporal_trends", `drug_name` (REQUIRED), `adverse_event` (optional) | Returns yearly counts and trend direction |
| `FAERS_compare_drugs` | `operation`="compare_drugs", `drug1` (REQUIRED), `drug2` (REQUIRED), `adverse_event` (REQUIRED) | Returns PRR/ROR/IC for both drugs side-by-side |
| `FAERS_filter_serious_events` | `operation`="filter_serious_events", `drug_name` (REQUIRED), `seriousness_type` (death/hospitalization/disability/life_threatening/all) | Returns top serious reactions with counts |
| `FAERS_stratify_by_demographics` | `operation`="stratify_by_demographics", `drug_name` (REQUIRED), `adverse_event` (REQUIRED), `stratify_by` (sex/age/country) | Returns stratified counts and percentages. Sex codes: 0=Unknown, 1=Male, 2=Female |
| `FAERS_rollup_meddra_hierarchy` | `operation`="rollup_meddra_hierarchy", `drug_name` (REQUIRED) | Returns top 50 preferred terms with counts |

## FAERS Aggregate Tools (multi-drug)

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `FAERS_count_additive_adverse_reactions` | `medicinalproducts` (REQUIRED, array), `patientsex`, `patientagegroup`, `occurcountry`, `serious`, `seriousnessdeath` | Aggregates AE counts across multiple drugs |
| `FAERS_count_additive_seriousness_classification` | `medicinalproducts` (REQUIRED, array), `patientsex`, `patientagegroup`, `occurcountry` | Aggregates seriousness across multiple drugs |
| `FAERS_count_additive_reaction_outcomes` | `medicinalproducts` (REQUIRED, array) | Aggregates outcomes across multiple drugs |

## FDA Label Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `FDA_get_boxed_warning_info_by_drug_name` | `drug_name` | Returns `{error: {code: "NOT_FOUND"}}` if no boxed warning |
| `FDA_get_contraindications_by_drug_name` | `drug_name` | Returns `{meta: {total: N}, results: [{contraindications: [...]}]}` |
| `FDA_get_adverse_reactions_by_drug_name` | `drug_name` | Returns `{meta: {total: N}, results: [{adverse_reactions: [...]}]}` |
| `FDA_get_warnings_by_drug_name` | `drug_name` | Returns `{meta: {total: N}, results: [{warnings: [...]}]}` |
| `FDA_get_drug_interactions_by_drug_name` | `drug_name` | Returns `{meta: {total: N}, results: [{drug_interactions: [...]}]}` |
| `FDA_get_pharmacogenomics_info_by_drug_name` | `drug_name` | Returns PGx info from label |
| `FDA_get_pregnancy_or_breastfeeding_info_by_drug_name` | `drug_name` | Returns pregnancy info |
| `FDA_get_geriatric_use_info_by_drug_name` | `drug_name` | Returns geriatric use info |
| `FDA_get_pediatric_use_info_by_drug_name` | `drug_name` | Returns pediatric info |

## OpenTargets Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `OpenTargets_get_drug_chembId_by_generic_name` | `drugName` | Returns `{data: {search: {hits: [{id, name, description}]}}}` |
| `OpenTargets_get_drug_adverse_events_by_chemblId` | `chemblId` | Returns `{data: {drug: {adverseEvents: {count, rows: [{name, meddraCode, count, logLR}]}}}}` |
| `OpenTargets_get_drug_blackbox_status_by_chembl_ID` | `chemblId` | Returns `{data: {drug: {hasBeenWithdrawn, blackBoxWarning}}}` |
| `OpenTargets_get_drug_warnings_by_chemblId` | `chemblId` | Returns drug warnings (may be empty) |
| `OpenTargets_get_drug_mechanisms_of_action_by_chemblId` | `chemblId` | Returns `{data: {drug: {mechanismsOfAction: {rows: [...]}}}}` |
| `OpenTargets_get_drug_indications_by_chemblId` | `chemblId` | Returns approved and investigational indications |
| `OpenTargets_get_target_safety_profile_by_ensemblID` | `ensemblId` | Returns `{data: {target: {safetyLiabilities: [...]}}}` |

## DrugBank Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `drugbank_get_safety_by_drug_name_or_drugbank_id` | `query`, `case_sensitive` (bool), `exact_match` (bool), `limit` | Returns toxicity, food interactions |
| `drugbank_get_targets_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` | Returns drug targets |
| `drugbank_get_drug_interactions_by_drug_name_or_id` | `query`, `case_sensitive`, `exact_match`, `limit` | Returns DDIs |
| `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` | `query`, `case_sensitive`, `exact_match`, `limit` | Returns pharmacology |

## PharmGKB Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `PharmGKB_search_drugs` | `query` | Returns `{data: [{id, name, smiles}]}` |
| `PharmGKB_get_drug_details` | `drug_id` (e.g., "PA448500") | Returns detailed drug info |
| `PharmGKB_get_dosing_guidelines` | `guideline_id`, `gene` (both optional) | Returns dosing guidelines |
| `PharmGKB_get_clinical_annotations` | `annotation_id`, `gene_id` (both optional) | Returns clinical annotations |
| `fda_pharmacogenomic_biomarkers` | `drug_name`, `biomarker`, `limit` | Returns `{count, results: [...]}` |

## ADMETAI Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `ADMETAI_predict_toxicity` | `smiles` (REQUIRED, array of strings) | Predicts hepatotoxicity, cardiotoxicity, etc. |
| `ADMETAI_predict_CYP_interactions` | `smiles` (REQUIRED, array) | Predicts CYP inhibition/substrate |

## Literature Tools

| Tool | Key Parameters | Notes |
|------|---------------|-------|
| `PubMed_search_articles` | `query`, `limit` | Returns list of article dicts |
| `openalex_search_works` | `query`, `limit` | Returns works with citation counts |
| `EuropePMC_search_articles` | `query`, `source` ("PPR" for preprints), `pageSize` | Returns articles including preprints |
| `search_clinical_trials` | `query_term` (REQUIRED), `condition`, `intervention`, `pageSize` | Returns clinical trials |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `FAERS_calculate_disproportionality` | Manual calculation from `FAERS_count_*` data | Literature PRR values |
| `FAERS_count_reactions_by_drug_event` | `FAERS_rollup_meddra_hierarchy` | OpenTargets adverse events |
| `FDA_get_boxed_warning_info_by_drug_name` | `OpenTargets_get_drug_blackbox_status_by_chembl_ID` | DrugBank safety |
| `FDA_get_contraindications_by_drug_name` | `FDA_get_warnings_by_drug_name` | DrugBank safety |
| `OpenTargets_get_drug_chembId_by_generic_name` | `ChEMBL_search_drugs` | Manual search |
| `PharmGKB_search_drugs` | `fda_pharmacogenomic_biomarkers` | FDA label PGx section |
| `PubMed_search_articles` | `openalex_search_works` | `EuropePMC_search_articles` |
