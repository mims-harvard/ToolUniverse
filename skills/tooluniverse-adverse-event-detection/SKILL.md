---
name: tooluniverse-adverse-event-detection
description: Detect and analyze adverse drug event signals using FDA FAERS data, drug labels, disproportionality analysis (PRR, ROR, IC), and biomedical evidence. Generates quantitative safety signal scores (0-100) with evidence grading. Use for post-market surveillance, pharmacovigilance, drug safety assessment, adverse event investigation, and regulatory decision support.
---

# Adverse Drug Event Signal Detection & Analysis

Automated pipeline for detecting, quantifying, and contextualizing adverse drug event signals using FAERS disproportionality analysis, FDA label mining, mechanism-based prediction, and literature evidence. Produces a quantitative Safety Signal Score (0-100) for regulatory and clinical decision-making.

**KEY PRINCIPLES**:
1. **Signal quantification first** - Every adverse event must have PRR/ROR/IC with confidence intervals
2. **Serious events priority** - Deaths, hospitalizations, life-threatening events always analyzed first
3. **Multi-source triangulation** - FAERS + FDA labels + OpenTargets + DrugBank + literature
4. **Context-aware assessment** - Distinguish drug-specific vs class-wide vs confounding signals
5. **Report-first approach** - Create report file FIRST, update progressively
6. **Evidence grading mandatory** - T1 (regulatory/boxed warning) through T4 (computational)
7. **English-first queries** - Always use English drug names in tool calls, respond in user's language

**Reference files** (in this directory):
- `PHASE_DETAILS.md` - Detailed tool calls, code examples, and output templates per phase
- `REPORT_TEMPLATE.md` - Full report template and completeness checklist
- `TOOL_REFERENCE.md` - Tool parameter reference and fallback chains
- `QUICK_START.md` - Quick examples and common drug names

---

## When to Use

Apply when user asks:
- "What are the safety signals for [drug]?"
- "Detect adverse events for [drug]"
- "Is [drug] associated with [adverse event]?"
- "What are the FAERS signals for [drug]?"
- "Compare safety of [drug A] vs [drug B] for [adverse event]"
- "What are the serious adverse events for [drug]?"
- "Are there emerging safety signals for [drug]?"
- "Post-market surveillance report for [drug]"
- "Pharmacovigilance signal detection for [drug]"

**Differentiation from tooluniverse-pharmacovigilance**: This skill focuses specifically on **signal detection and quantification** using disproportionality analysis (PRR, ROR, IC) with statistical rigor, produces a quantitative **Safety Signal Score (0-100)**, and performs **comparative safety analysis** across drug classes.

---

## Workflow Overview

```
Phase 0: Input Parsing & Drug Disambiguation
  Parse drug name, resolve to ChEMBL ID, DrugBank ID
  Identify drug class, mechanism, and approved indications
    |
Phase 1: FAERS Adverse Event Profiling
  Top adverse events by frequency
  Seriousness and outcome distributions
  Demographics (age, sex, country)
    |
Phase 2: Disproportionality Analysis (Signal Detection)
  Calculate PRR, ROR, IC with 95% CI for each AE
  Apply signal detection criteria
  Classify signal strength (Strong/Moderate/Weak/None)
    |
Phase 3: FDA Label Safety Information
  Boxed warnings, contraindications
  Warnings and precautions, adverse reactions
  Drug interactions, special populations
    |
Phase 4: Mechanism-Based Adverse Event Context
  Target-based AE prediction (OpenTargets safety)
  Off-target effects, ADMET predictions
  Drug class effects comparison
    |
Phase 5: Comparative Safety Analysis
  Compare to drugs in same class
  Identify unique vs class-wide signals
  Head-to-head disproportionality comparison
    |
Phase 6: Drug-Drug Interactions & Risk Factors
  Known DDIs causing AEs
  Pharmacogenomic risk factors (PharmGKB)
  FDA PGx biomarkers
    |
Phase 7: Literature Evidence
  PubMed safety studies, case reports
  OpenAlex citation analysis
  Preprint emerging signals (EuropePMC)
    |
Phase 8: Risk Assessment & Safety Signal Score
  Calculate Safety Signal Score (0-100)
  Evidence grading (T1-T4) for each signal
  Clinical significance assessment
    |
Phase 9: Report Synthesis & Recommendations
  Monitoring recommendations
  Risk mitigation strategies
  Completeness checklist
```

---

## Phase Summaries

### Phase 0: Input Parsing & Drug Disambiguation
Resolve drug name to ChEMBL ID, DrugBank ID. Get mechanism of action, blackbox warning status, targets, and approved indications.
- **Tools**: `OpenTargets_get_drug_chembId_by_generic_name`, `OpenTargets_get_drug_mechanisms_of_action_by_chemblId`, `OpenTargets_get_drug_blackbox_status_by_chembl_ID`, `drugbank_get_safety_by_drug_name_or_drugbank_id`, `drugbank_get_targets_by_drug_name_or_drugbank_id`, `OpenTargets_get_drug_indications_by_chemblId`

### Phase 1: FAERS Adverse Event Profiling
Query FAERS for top adverse events, seriousness distribution, outcomes, demographics, and death-related events. Filter serious events by type (death, hospitalization, life-threatening). Get MedDRA hierarchy rollup.
- **Tools**: `FAERS_count_reactions_by_drug_event`, `FAERS_count_seriousness_by_drug_event`, `FAERS_count_outcomes_by_drug_event`, `FAERS_count_patient_age_distribution`, `FAERS_count_death_related_by_drug`, `FAERS_count_reportercountry_by_drug_event`, `FAERS_filter_serious_events`, `FAERS_rollup_meddra_hierarchy`

### Phase 2: Disproportionality Analysis (Signal Detection)
**CRITICAL PHASE**. For each top adverse event (at least 15-20), calculate PRR, ROR, IC with 95% CI. Classify signal strength. Stratify strong signals by demographics.
- **Tools**: `FAERS_calculate_disproportionality`, `FAERS_stratify_by_demographics`
- **MedDRA term level note**: `FAERS_count_reactions_by_drug_event` filters by MedDRA Lowest Level Term (`reactionmeddraverse`) while `FAERS_calculate_disproportionality` uses Preferred Terms. Case counts can differ dramatically — always use disproportionality analysis as the primary signal metric, not raw counts.
- **Signal criteria**: PRR >= 2.0 AND lower CI > 1.0 AND N >= 3
- **Strength**: Strong (PRR >= 5), Moderate (PRR 3-5), Weak (PRR 2-3)
- See `PHASE_DETAILS.md` for full signal classification table

### Phase 3: FDA Label Safety Information
Extract boxed warnings, contraindications, warnings/precautions, adverse reactions, drug interactions, and special population info. Note: `{error: {code: "NOT_FOUND"}}` is normal when a section does not exist.
- **Tools**: `FDA_get_boxed_warning_info_by_drug_name`, `FDA_get_contraindications_by_drug_name`, `FDA_get_warnings_by_drug_name`, `FDA_get_adverse_reactions_by_drug_name`, `FDA_get_drug_interactions_by_drug_name`, `FDA_get_pregnancy_or_breastfeeding_info_by_drug_name`, `FDA_get_geriatric_use_info_by_drug_name`, `FDA_get_pediatric_use_info_by_drug_name`, `FDA_get_pharmacogenomics_info_by_drug_name`

### Phase 4: Mechanism-Based Adverse Event Context
Get target safety profile, OpenTargets adverse events, ADMET toxicity predictions (if SMILES available), and drug warnings.
- **Tools**: `OpenTargets_get_target_safety_profile_by_ensemblID`, `OpenTargets_get_drug_adverse_events_by_chemblId`, `ADMETAI_predict_toxicity`, `ADMETAI_predict_CYP_interactions`, `OpenTargets_get_drug_warnings_by_chemblId`

### Phase 5: Comparative Safety Analysis
Head-to-head comparison with class members using `FAERS_compare_drugs`. Aggregate class AEs. Identify class-wide vs drug-specific signals.
- **Tools**: `FAERS_compare_drugs`, `FAERS_count_additive_adverse_reactions`, `FAERS_count_additive_seriousness_classification`

### Phase 6: Drug-Drug Interactions & Risk Factors
Extract DDIs from FDA label, DrugBank, and DailyMed. Query PharmGKB for pharmacogenomic risk factors and dosing guidelines. Check FDA PGx biomarkers.
- **Tools**: `FDA_get_drug_interactions_by_drug_name`, `drugbank_get_drug_interactions_by_drug_name_or_id`, `DailyMed_parse_drug_interactions`, `PharmGKB_search_drugs`, `PharmGKB_get_drug_details`, `PharmGKB_get_dosing_guidelines`, `fda_pharmacogenomic_biomarkers`

### Phase 7: Literature Evidence
Search PubMed, OpenAlex, and EuropePMC for safety studies, case reports, and preprints.
- **Tools**: `PubMed_search_articles`, `openalex_search_works`, `EuropePMC_search_articles`

### Phase 8: Risk Assessment & Safety Signal Score
Calculate Safety Signal Score (0-100) from four components: FAERS signal strength (0-35), serious AEs (0-30), FDA label warnings (0-25), literature evidence (0-10). Grade each signal T1-T4. See `PHASE_DETAILS.md` for scoring rubric.

### Phase 9: Report Synthesis
Generate comprehensive markdown report with executive summary, all phase outputs, monitoring recommendations, risk mitigation strategies, patient counseling points, and completeness checklist. See `REPORT_TEMPLATE.md` for full template.

---

## Common Analysis Patterns

| Pattern | Description | Phases |
|---------|-------------|--------|
| **Full Safety Profile** | Comprehensive report for regulatory/safety reviews | All (0-9) |
| **Specific AE Investigation** | "Does [drug] cause [event]?" | 0, 2, 3, 7 |
| **Drug Class Comparison** | Compare 3-5 drugs for specific AE | 0, 2, 5 |
| **Emerging Signal Detection** | Screen for signals not in FDA label | 1, 2, 3, 7 |
| **PGx Risk Assessment** | Genetic risk factors for AEs | 0, 6 |
| **Pre-Approval Assessment** | New drugs with limited FAERS data | 4, 7 |

---

## Edge Cases

- **No FAERS reports**: Skip Phases 1-2; rely on FDA label, mechanism predictions, literature
- **Generic vs Brand name**: Try both in FAERS; use `OpenTargets_get_drug_chembId_by_generic_name` to resolve
- **Drug combinations**: Use `FAERS_count_additive_adverse_reactions` for aggregate class analysis
- **Confounding by indication**: Compare AE profile to the disease being treated; note limitation in report
- **Drugs with boxed warnings**: Score component automatically 25/25 for label warnings; prioritize boxed warning events
