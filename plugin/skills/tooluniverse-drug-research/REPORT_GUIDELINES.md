# Drug Research Report Guidelines

Detailed section-by-section instructions with output examples for each research path.

---

## Report Detail Requirements

Each section must be **comprehensive and detailed**:

- **Tables**: Use tables for structured data (targets, trials, adverse events)
- **Lists**: Use bullet points for features, findings, key points
- **Paragraphs**: Include narrative summaries that synthesize findings
- **Numbers**: Include specific values, counts, percentages (not vague terms)
- **Context**: Explain what the data means, not just what it is

**BAD** (too brief):
```markdown
### Clinical Trials
Multiple trials completed. Approved for diabetes.
```

**GOOD** (detailed with sources):
```markdown
### 5.2 Clinical Trial Landscape
| Phase | Total | Completed | Recruiting |
|-------|-------|-----------|------------|
| Phase 4 | 89 | 72 | 12 |
| Phase 3 | 156 | 134 | 15 |

**Total Registered Trials**: 515 (as of 2026-02-04)
*Source: ClinicalTrials.gov via `search_clinical_trials`*
```

---

## FDA Label Core Fields Bundle

**For approved drugs, ALWAYS retrieve these FDA label sections early** (after getting set_id from `DailyMed_search_spls`).

Call `DailyMed_get_spl_sections_by_setid(setid=set_id, sections=[...])` in batches:

**Phase 1 (Mechanism & Chemistry)**:
- `mechanism_of_action` -> Section 3.1
- `pharmacodynamics` -> Section 3.1
- `chemistry` -> Section 2.4

**Phase 2 (ADMET & PK)**:
- `clinical_pharmacology` -> Section 4
- `pharmacokinetics` -> Section 4.1-4.4
- `drug_interactions` -> Section 4.3, 6.5

**Phase 3 (Safety & Dosing)**:
- `warnings_and_cautions` -> Section 6.3
- `adverse_reactions` -> Section 6.1
- `dosage_and_administration` -> Section 6.6, 8.2

**Phase 4 (PGx & Clinical)**:
- `pharmacogenomics` -> Section 7
- `clinical_studies` -> Section 5.5
- `description` -> Section 2.5 (formulation)
- `inactive_ingredients` -> Section 2.5

---

## PATH 1: Chemical Properties & CMC

**Objective**: Full physicochemical profile, salt forms, formulation details.

**Tool Chain**:
1. `PubChem_get_compound_properties_by_CID(cid)` -> MW, formula, XLogP, TPSA, HBD, HBA, rotatable bonds
2. `ADMETAI_predict_physicochemical_properties(smiles=[smiles])` -> logP, Lipinski, QED, TPSA
3. `ADMETAI_predict_solubility_lipophilicity_hydration(smiles=[smiles])` -> Solubility, Lipophilicity
4. `DailyMed_get_spl_sections_by_setid(setid, sections=["chemistry"])` -> Salt forms, polymorphs
5. `DailyMed_get_spl_sections_by_setid(setid, sections=["description", "inactive_ingredients"])` -> Formulation

**Type Normalization**: Convert all numeric IDs to strings before API calls.

**Output Example** (Section 2.1):
```markdown
| Property | Value | Drug-Likeness | Source |
|----------|-------|---------------|--------|
| **Molecular Weight** | 129.16 g/mol | Pass (< 500) | PubChem |
| **LogP** | -2.64 | Pass (< 5) | ADMET-AI |
| **TPSA** | 91.5 A^2 | Pass (< 140) | PubChem |
| **H-Bond Donors** | 2 | Pass (<= 5) | PubChem |

**Lipinski Rule of Five**: PASS (0 violations)
**QED Score**: 0.74 (Good drug-likeness)
*Sources: PubChem, ADMET-AI*
```

**Formulation Comparison** (if multiple formulations exist):
```markdown
| Formulation | Tmax (h) | Cmax (ng/mL) | AUC | Half-life (h) | Dosing |
|-------------|----------|--------------|-----|---------------|--------|
| **IR** | 2.5 | 1200 | 8400 | 6.5 | 500 mg TID |
| **ER** | 7.0 | 950 | 8900 | 6.5 | 1000 mg QD |
*Source: DailyMed clinical pharmacology sections*
```

---

## PATH 2: Mechanism & Targets

**Objective**: FDA label MOA + experimental targets + selectivity.

**Tool Chain**:
1. `DailyMed_get_spl_sections_by_setid(setid, sections=["mechanism_of_action", "pharmacodynamics"])` -> Official FDA MOA [T1]
2. `ChEMBL_search_activities(molecule_chembl_id=chembl_id, limit=100)` -> Activity records
3. `ChEMBL_get_target(target_chembl_id)` for each unique target -> Target name, UniProt [T1]
4. `DGIdb_get_drug_info(drugs=[drug_name])` -> Target genes, interaction types [T2]
5. `PubChem_get_bioactivity_summary_by_CID(cid)` -> Assay summary [T2]

**CRITICAL**:
- **Avoid `ChEMBL_get_molecule_targets`** - returns unfiltered/irrelevant targets
- **Derive targets from activities**: Filter to pChEMBL >= 6.0 or IC50/EC50 <= 1 uM
- **Type normalization**: Convert all ChEMBL IDs to strings

**Output Example** (Section 3.2):
```markdown
| Target | UniProt | Type | Potency | Assays | Evidence | Source |
|--------|---------|------|---------|--------|----------|--------|
| PRKAA1 (AMPK a1) | Q13131 | Activator | EC50 ~10 uM | 12 | T1 | ChEMBL |
| SLC22A1 (OCT1) | O15245 | Substrate | Km ~1.5 mM | 5 | T2 | DGIdb |
*Source: ChEMBL activities filtered to pChEMBL >= 6.0*
```

---

## PATH 3: ADMET Properties

**Objective**: Full ADMET profile - predictions + FDA label PK.

**Primary Chain (ADMET-AI)**:
1. `ADMETAI_predict_bioavailability(smiles)` -> Bioavailability, HIA, PAMPA, Caco2, Pgp
2. `ADMETAI_predict_BBB_penetrance(smiles)` -> BBB probability
3. `ADMETAI_predict_CYP_interactions(smiles)` -> CYP1A2, 2C9, 2C19, 2D6, 3A4
4. `ADMETAI_predict_clearance_distribution(smiles)` -> Clearance, Half_Life, VDss, PPBR
5. `ADMETAI_predict_toxicity(smiles)` -> AMES, hERG, DILI, ClinTox, LD50

**Fallback Chain** (if ADMET-AI fails):
1. `DailyMed_get_spl_sections_by_setid(setid, sections=["clinical_pharmacology", "pharmacokinetics"])` [T1]
2. `DailyMed_get_spl_sections_by_setid(setid, sections=["drug_interactions"])` [T1]
3. `PubMed_search_articles(query="[drug] pharmacokinetics", max_results=10)` [T2]

**CRITICAL**: If ADMET-AI tools fail, automatically switch to fallback. Do NOT leave Section 4 as "predictions unavailable."

---

## PATH 4: Clinical Trials

**Objective**: Complete clinical development picture with accurate phase counts.

**Tool Chain**:
1. `search_clinical_trials(intervention=drug_name, pageSize=100)` -> Full result set
2. COMPUTE PHASE COUNTS from results (Phase 1/2/3/4 by status)
3. SELECT REPRESENTATIVE TRIALS (top 5 Phase 3, top 3 recruiting)
4. `get_clinical_trial_conditions_and_interventions(nct_ids=selected)` -> Details
5. `extract_clinical_trial_outcomes(nct_ids=completed_phase3)` -> Efficacy
6. `extract_clinical_trial_adverse_events(nct_ids=completed)` -> Safety
7. `fda_pharmacogenomic_biomarkers(drug_name)` -> Companion diagnostics [T1]
8. `PharmGKB_get_clinical_annotations(drug_id)` -> Response predictors [T2]

**CRITICAL**: Section 5.2 must show actual counts by phase/status in table format, not just a trial list.

**Output Example** (Section 5.6 - Biomarkers):
```markdown
#### FDA-Required Testing
| Biomarker | Requirement Level | Approved Test(s) | Evidence |
|-----------|------------------|------------------|----------|
| EGFR T790M | Required (NSCLC) | cobas v2 | T1 |
*Source: `fda_pharmacogenomic_biomarkers`*
```

---

## PATH 5: Post-Marketing Safety & Drug Interactions

**Objective**: Real-world safety signals + DDI guidance + dose modifications.

**FAERS Chain**:
1. `FAERS_count_reactions_by_drug_event(medicinalproduct)` -> Top 20 AEs [T1]
2. `FAERS_count_seriousness_by_drug_event(medicinalproduct)` -> Serious ratio [T1]
3. `FAERS_count_outcomes_by_drug_event(medicinalproduct)` -> Outcomes [T1]
4. `FAERS_count_death_related_by_drug(medicinalproduct)` -> Fatal count [T1]
5. `FAERS_count_patient_age_distribution(medicinalproduct)` -> Age groups [T1]

**DDI & Dose Modification Chain**:
6. `DailyMed_get_spl_sections_by_setid(setid, sections=["drug_interactions"])` -> DDI table [T1]
7. `DailyMed_get_spl_sections_by_setid(setid, sections=["dosage_and_administration", "warnings_and_cautions"])` -> Dose mods [T1]
8. `DailyMed_get_spl_by_setid(setid)` -> Drug-food interactions (search for grapefruit, alcohol, food, meal) [T1]
9. `search_clinical_trials(intervention="[drug] AND combination")` -> Approved combos [T1]

**CRITICAL FAERS Requirements**:
- Include date window (e.g., "Reports from 2004-2026")
- Report seriousness breakdown (not just top PTs)
- Add limitations paragraph: Small N, voluntary reporting, causality not established, reporting bias

**Output Example** (Section 6.6 - Dose Modifications):
```markdown
#### Renal Impairment
| eGFR (mL/min/1.73m^2) | Dosing |
|----------------------|--------|
| >=60 | No adjustment |
| 45-59 | Max 1000 mg/day |
| 30-44 | Max 500 mg/day |
| <30 | Contraindicated |
*Source: DailyMed SPL*
```

---

## PATH 6: Pharmacogenomics

**Primary Chain (PharmGKB)**:
1. `PharmGKB_search_drugs(query)` -> PharmGKB drug ID
2. `PharmGKB_get_drug_details(drug_id)` -> Cross-references, related genes
3. `PharmGKB_get_clinical_annotations(gene_id)` for each gene -> Variant-drug associations
4. `PharmGKB_get_dosing_guidelines(gene=gene_symbol)` -> CPIC/DPWG recommendations

**Fallback Chain**:
5. `DailyMed_get_spl_sections_by_setid(setid, sections=["pharmacogenomics", "clinical_pharmacology"])` [T1]
6. `PubMed_search_articles(query="[drug] pharmacogenomics", max_results=5)` [T2]

---

## PATH 7: Regulatory Status & Patents

**Tool Chain**:
1. `DailyMed_search_spls(drug_name)` -> SetID
2. `FDA_OrangeBook_search_drug(brand_name)` -> Application number [T1]
3. `FDA_OrangeBook_get_approval_history(appl_no)` -> Approval dates [T1]
4. `FDA_OrangeBook_get_exclusivity(brand_name)` -> Exclusivity types/dates [T1]
5. `FDA_OrangeBook_get_patent_info(brand_name)` -> Patent numbers [T1]
6. `FDA_OrangeBook_check_generic_availability(brand_name)` -> Generic entries [T1]
7. `DailyMed_get_spl_by_setid(setid)` -> Special populations (pediatric, geriatric, pregnancy, lactation, renal, hepatic) using LOINC codes [T1]

**CRITICAL**: Orange Book data is US-only. Document limitation for EMA/PMDA.

---

## PATH 8: Real-World Evidence

**Tool Chain**:
1. `search_clinical_trials(study_type="OBSERVATIONAL", intervention=drug_name)` -> RWE studies [T1]
2. `PubMed_search_articles(query="[drug] (real-world OR observational OR effectiveness)")` [T2]
3. `PubMed_search_articles(query="[drug] (registry OR post-marketing OR surveillance)")` [T2]
4. Compare clinical trial efficacy vs real-world effectiveness

---

## PATH 9: Comparative Analysis

**Tool Chain**:
1. Identify comparator drugs (user-provided or inferred from class)
2. For each comparator: abbreviated tool chain (PubChem, ChEMBL potency, trials, FAERS)
3. `search_clinical_trials(intervention="[drug] AND [comparator]")` -> Head-to-head trials [T1]
4. `PubMed_search_articles(query="[drug] vs [comparator]")` -> Meta-analyses [T2]
5. Create comparison tables: potency, selectivity, ADMET, efficacy, safety

---

## Type Normalization & Error Prevention

Many ToolUniverse tools require **string** inputs but may return integers/floats. Always convert IDs:

```python
chembl_ids = [str(id) for id in chembl_ids]
nct_ids = [str(id) for id in nct_ids]
pmids = [str(id) for id in pmids]
```

Pre-call checklist:
- All ID parameters are strings
- Lists contain strings, not ints/floats
- No None/null values in required fields
- Arrays are non-empty if required
