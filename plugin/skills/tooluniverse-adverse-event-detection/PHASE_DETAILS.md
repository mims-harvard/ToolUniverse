# Adverse Event Detection - Phase Details

Detailed tool calls, code examples, and output templates for each analysis phase.

---

## Phase 0: Input Parsing & Drug Disambiguation

### 0.1 Resolve Drug Identity

```python
# Step 1: Get ChEMBL ID from drug name
chembl_result = tu.tools.OpenTargets_get_drug_chembId_by_generic_name(drugName="atorvastatin")
# Response: {data: {search: {hits: [{id: "CHEMBL1487", name: "ATORVASTATIN", description: "..."}]}}}
chembl_id = chembl_result['data']['search']['hits'][0]['id']  # "CHEMBL1487"

# Step 2: Get drug mechanism of action
moa = tu.tools.OpenTargets_get_drug_mechanisms_of_action_by_chemblId(chemblId=chembl_id)
# Response: {data: {drug: {mechanismsOfAction: {rows: [{mechanismOfAction: "HMG-CoA reductase inhibitor", actionType: "INHIBITOR", targetName: "...", targets: [{id: "ENSG00000113161", approvedSymbol: "HMGCR"}]}]}}}}

# Step 3: Get blackbox warning status
blackbox = tu.tools.OpenTargets_get_drug_blackbox_status_by_chembl_ID(chemblId=chembl_id)
# Response: {data: {drug: {name: "ATORVASTATIN", hasBeenWithdrawn: false, blackBoxWarning: false}}}

# Step 4: Get DrugBank info (safety, toxicity)
drugbank = tu.tools.drugbank_get_safety_by_drug_name_or_drugbank_id(
    query="atorvastatin", case_sensitive=False, exact_match=False, limit=3
)
# Response: {results: [{drug_name: "Atorvastatin", drugbank_id: "DB01076", toxicity: "...", food_interactions: "..."}]}

# Step 5: Get DrugBank targets
targets = tu.tools.drugbank_get_targets_by_drug_name_or_drugbank_id(
    query="atorvastatin", case_sensitive=False, exact_match=False, limit=3
)

# Step 6: Get approved indications
indications = tu.tools.OpenTargets_get_drug_indications_by_chemblId(chemblId=chembl_id)
```

### 0.2 Output for Report

```markdown
## 1. Drug Identification

| Property | Value |
|----------|-------|
| **Generic Name** | Atorvastatin |
| **ChEMBL ID** | CHEMBL1487 |
| **DrugBank ID** | DB01076 |
| **Drug Class** | HMG-CoA reductase inhibitor (Statin) |
| **Mechanism** | HMG-CoA reductase inhibitor (target: HMGCR) |
| **Primary Target** | HMGCR (ENSG00000113161) |
| **Black Box Warning** | No |
| **Withdrawn** | No |

*Source: OpenTargets, DrugBank*
```

---

## Phase 1: FAERS Adverse Event Profiling

### 1.1 Query FAERS for Adverse Events

```python
# Get top adverse event reactions (returns list of {term, count})
reactions = tu.tools.FAERS_count_reactions_by_drug_event(medicinalproduct="ATORVASTATIN")

# Get seriousness classification
seriousness = tu.tools.FAERS_count_seriousness_by_drug_event(medicinalproduct="ATORVASTATIN")

# Get outcome distribution
outcomes = tu.tools.FAERS_count_outcomes_by_drug_event(medicinalproduct="ATORVASTATIN")

# Get age distribution
age_dist = tu.tools.FAERS_count_patient_age_distribution(medicinalproduct="ATORVASTATIN")

# Get death-related events
deaths = tu.tools.FAERS_count_death_related_by_drug(medicinalproduct="ATORVASTATIN")

# Get reporter country distribution
countries = tu.tools.FAERS_count_reportercountry_by_drug_event(medicinalproduct="ATORVASTATIN")
```

### 1.2 Get Serious Events Breakdown

```python
# Filter serious events - all types
serious_all = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events",
    drug_name="ATORVASTATIN",
    seriousness_type="all"
)

# Death-related serious events
serious_death = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events",
    drug_name="ATORVASTATIN",
    seriousness_type="death"
)

# Hospitalization-related
serious_hosp = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events",
    drug_name="ATORVASTATIN",
    seriousness_type="hospitalization"
)

# Life-threatening
serious_lt = tu.tools.FAERS_filter_serious_events(
    operation="filter_serious_events",
    drug_name="ATORVASTATIN",
    seriousness_type="life_threatening"
)
```

### 1.3 MedDRA Hierarchy Rollup

```python
meddra = tu.tools.FAERS_rollup_meddra_hierarchy(
    operation="rollup_meddra_hierarchy",
    drug_name="ATORVASTATIN"
)
```

### 1.4 Output for Report

```markdown
## 2. FAERS Adverse Event Profile

### 2.1 Overview
- **Total reports**: 326,261 (Serious: 242,757 | Non-serious: 83,504)
- **Fatal outcomes**: 22,128
- **Primary reporter countries**: US (170,963), GB (40,079), CA (16,492)

### 2.2 Top 10 Adverse Events by Frequency

| Rank | Adverse Event | Reports | % of Total |
|------|---------------|---------|------------|
| 1 | Fatigue | 19,171 | 5.9% |
| 2 | Diarrhoea | 17,127 | 5.2% |
| ... | ... | ... | ... |

### 2.3 Outcome Distribution

| Outcome | Count | Percentage |
|---------|-------|------------|
| Unknown | 162,310 | 39.6% |
| Fatal | 22,128 | 5.4% |

### 2.4 Age Distribution

| Age Group | Reports | Percentage |
|-----------|---------|------------|
| Elderly | 38,510 | 61.3% |
| Adult | 24,302 | 38.7% |

*Source: FAERS via FAERS_count_reactions_by_drug_event, FAERS_count_seriousness_by_drug_event*
```

---

## Phase 2: Disproportionality Analysis (Signal Detection)

### 2.1 Calculate Signal Metrics

**CRITICAL**: This is the core of the skill. For each top adverse event (at least top 15-20), calculate PRR, ROR, and IC with 95% confidence intervals.

```python
top_events = ["Rhabdomyolysis", "Myalgia", "Hepatotoxicity", "Diabetes mellitus",
              "Acute kidney injury", "Myopathy", "Pancreatitis"]

for event in top_events:
    result = tu.tools.FAERS_calculate_disproportionality(
        operation="calculate_disproportionality",
        drug_name="ATORVASTATIN",
        adverse_event=event
    )
    # Response structure:
    # {
    #   status: "success",
    #   drug_name: "ATORVASTATIN",
    #   adverse_event: "Rhabdomyolysis",
    #   contingency_table: {a_drug_and_event, b_drug_no_event, c_no_drug_event, d_no_drug_no_event},
    #   metrics: {
    #     ROR: {value: 4.825, ci_95_lower: 4.622, ci_95_upper: 5.037},
    #     PRR: {value: 4.79, ci_95_lower: 4.59, ci_95_upper: 4.998},
    #     IC: {value: 2.194, ci_95_lower: 2.136, ci_95_upper: 2.252}
    #   },
    #   signal_detection: {signal_detected: true, signal_strength: "Strong signal", criteria: "..."}
    # }
```

### 2.2 Signal Detection Criteria

**Proportional Reporting Ratio (PRR)**:
- PRR = (a/(a+b)) / (c/(c+d))
- Signal: PRR >= 2.0 AND lower 95% CI > 1.0 AND case count >= 3

**Reporting Odds Ratio (ROR)**:
- ROR = (a*d) / (b*c)
- Signal: Lower 95% CI > 1.0

**Information Component (IC)**:
- IC = log2(observed/expected)
- Signal: Lower 95% CI > 0

### 2.3 Signal Strength Classification

| Strength | PRR | ROR Lower CI | IC Lower CI | Clinical Action |
|----------|-----|-------------|-------------|-----------------|
| **Strong** | >= 5.0 | >= 3.0 | >= 2.0 | Immediate investigation required |
| **Moderate** | 3.0-4.9 | 2.0-2.9 | 1.0-1.9 | Active monitoring recommended |
| **Weak** | 2.0-2.9 | 1.0-1.9 | 0-0.9 | Routine monitoring, watch for trends |
| **No signal** | < 2.0 | < 1.0 | < 0 | Standard pharmacovigilance |

### 2.4 Demographic Stratification of Key Signals

```python
result = tu.tools.FAERS_stratify_by_demographics(
    operation="stratify_by_demographics",
    drug_name="ATORVASTATIN",
    adverse_event="Rhabdomyolysis",
    stratify_by="sex"  # Options: sex, age, country
)
```

**Note on sex codes**: group 0 = Unknown, group 1 = Male, group 2 = Female.

### 2.5 Output for Report

```markdown
## 3. Disproportionality Analysis (Signal Detection)

### 3.1 Signal Detection Summary

| Adverse Event | Cases (a) | PRR | PRR 95% CI | ROR | ROR 95% CI | IC | Signal |
|---------------|-----------|-----|------------|-----|------------|-----|--------|
| Rhabdomyolysis | 2,226 | 4.79 | 4.59-5.00 | 4.83 | 4.62-5.04 | 2.19 | **STRONG** |
| Myopathy | 1,234 | 6.12 | 5.72-6.55 | 6.18 | 5.77-6.62 | 2.54 | **STRONG** |

*Source: FAERS via FAERS_calculate_disproportionality, FAERS_stratify_by_demographics*
```

---

## Phase 3: FDA Label Safety Information

### 3.1 Extract Label Sections

```python
boxed = tu.tools.FDA_get_boxed_warning_info_by_drug_name(drug_name="atorvastatin")
contras = tu.tools.FDA_get_contraindications_by_drug_name(drug_name="atorvastatin")
warnings = tu.tools.FDA_get_warnings_by_drug_name(drug_name="atorvastatin")
adverse_rxns = tu.tools.FDA_get_adverse_reactions_by_drug_name(drug_name="atorvastatin")
interactions = tu.tools.FDA_get_drug_interactions_by_drug_name(drug_name="atorvastatin")
pregnancy = tu.tools.FDA_get_pregnancy_or_breastfeeding_info_by_drug_name(drug_name="atorvastatin")
geriatric = tu.tools.FDA_get_geriatric_use_info_by_drug_name(drug_name="atorvastatin")
pediatric = tu.tools.FDA_get_pediatric_use_info_by_drug_name(drug_name="atorvastatin")
pgx_label = tu.tools.FDA_get_pharmacogenomics_info_by_drug_name(drug_name="atorvastatin")
```

### 3.2 Handling No Results

**IMPORTANT**: FDA label tools return `{error: {code: "NOT_FOUND"}}` when a section does not exist. This is NORMAL for many drugs.

```python
if isinstance(boxed, dict) and 'error' in boxed:
    boxed_warning_text = "None (no boxed warning for this drug)"
else:
    boxed_warning_text = boxed['results'][0].get('boxed_warning', ['None'])[0]
```

---

## Phase 4: Mechanism-Based Adverse Event Context

### 4.1 Target Safety Profile

```python
target_id = "ENSG00000113161"  # HMGCR from Phase 0
safety = tu.tools.OpenTargets_get_target_safety_profile_by_ensemblID(ensemblId=target_id)

ot_aes = tu.tools.OpenTargets_get_drug_adverse_events_by_chemblId(chemblId="CHEMBL1487")
```

### 4.2 ADMET Predictions (if SMILES available)

```python
toxicity = tu.tools.ADMETAI_predict_toxicity(smiles=[smiles])
cyp = tu.tools.ADMETAI_predict_CYP_interactions(smiles=[smiles])
```

### 4.3 Drug Warnings from OpenTargets

```python
warnings = tu.tools.OpenTargets_get_drug_warnings_by_chemblId(chemblId="CHEMBL1487")
```

---

## Phase 5: Comparative Safety Analysis

### 5.1 Compare to Drug Class

```python
comparison = tu.tools.FAERS_compare_drugs(
    operation="compare_drugs",
    drug1="ATORVASTATIN",
    drug2="SIMVASTATIN",
    adverse_event="Rhabdomyolysis"
)

# Aggregate adverse events across drug class
class_drugs = ["ATORVASTATIN", "SIMVASTATIN", "ROSUVASTATIN", "PRAVASTATIN"]
class_aes = tu.tools.FAERS_count_additive_adverse_reactions(
    medicinalproducts=class_drugs
)
class_serious = tu.tools.FAERS_count_additive_seriousness_classification(
    medicinalproducts=class_drugs
)
```

---

## Phase 6: Drug-Drug Interactions & Risk Factors

### 6.1 Drug-Drug Interactions

```python
ddi_label = tu.tools.FDA_get_drug_interactions_by_drug_name(drug_name="atorvastatin")
ddi_db = tu.tools.drugbank_get_drug_interactions_by_drug_name_or_id(
    query="atorvastatin", case_sensitive=False, exact_match=False, limit=3
)
ddi_dailymed = tu.tools.DailyMed_parse_drug_interactions(drug_name="atorvastatin")
```

### 6.2 Pharmacogenomic Risk Factors

```python
pgx_search = tu.tools.PharmGKB_search_drugs(query="atorvastatin")
pgx_details = tu.tools.PharmGKB_get_drug_details(drug_id="PA448500")
dosing = tu.tools.PharmGKB_get_dosing_guidelines(gene="SLCO1B1")
fda_pgx = tu.tools.fda_pharmacogenomic_biomarkers(drug_name="atorvastatin", limit=10)
```

---

## Phase 7: Literature Evidence

### 7.1 Search Published Literature

```python
pubmed = tu.tools.PubMed_search_articles(
    query='atorvastatin adverse events safety rhabdomyolysis',
    limit=20
)
openalex = tu.tools.openalex_search_works(
    query="atorvastatin safety adverse events",
    limit=15
)
preprints = tu.tools.EuropePMC_search_articles(
    query="atorvastatin safety signal",
    source="PPR",
    pageSize=10
)
```

---

## Phase 8: Risk Assessment & Safety Signal Score

### 8.1 Safety Signal Score Calculation (0-100)

**Component 1: FAERS Signal Strength (0-35 points)**
```
If any signal has PRR >= 5 AND ROR lower CI >= 3: 35 points
If any signal has PRR 3-5 AND ROR lower CI 2-3: 20 points
If any signal has PRR 2-3 AND ROR lower CI 1-2: 10 points
If no signals detected: 0 points
```

**Component 2: Serious Adverse Events (0-30 points)**
```
Deaths reported with high count (>100): 30 points
Deaths reported with low count (1-100): 25 points
Life-threatening events: 20 points
Hospitalizations only: 15 points
Non-serious only: 0 points
```

**Component 3: FDA Label Warnings (0-25 points)**
```
Boxed warning present: 25 points
Drug withdrawn or restricted: 25 points
Contraindications present: 15 points
Warnings and precautions: 10 points
Adverse reactions only: 5 points
No label warnings: 0 points
```

**Component 4: Literature Evidence (0-10 points)**
```
Meta-analyses confirming safety signals: 10 points
Multiple RCTs with safety concerns: 7 points
Case reports/case series: 4 points
No published safety concerns: 0 points
```

**Total Score Interpretation:**
| Score Range | Interpretation | Action |
|-------------|---------------|--------|
| **75-100** | High concern | Serious safety signals; requires immediate regulatory attention |
| **50-74** | Moderate concern | Significant monitoring needed; consider risk mitigation |
| **25-49** | Low-moderate concern | Routine enhanced monitoring; standard risk management |
| **0-24** | Low concern | Standard safety profile; routine pharmacovigilance |

### 8.2 Evidence Grading

| Tier | Criteria | Example |
|------|----------|---------|
| **T1** | Boxed warning, confirmed by RCTs, PRR > 10 | Metformin: Lactic acidosis |
| **T2** | Label warning + FAERS signal (PRR 3-10) + published studies | Atorvastatin: Rhabdomyolysis |
| **T3** | FAERS signal (PRR 2-3) + case reports | Atorvastatin: Pancreatitis |
| **T4** | Computational prediction only (ADMET) or weak signal | ADMETAI hepatotoxicity prediction |
