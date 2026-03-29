---
name: tooluniverse-clinical-data-integration
description: Comprehensive drug safety review integrating FDA labels, FAERS adverse event reports, disproportionality analysis, pharmacogenomics, clinical trials, and literature. Use for regulatory assessments, post-market surveillance, drug safety reviews, adverse event investigation, and pharmacovigilance.
---

# Clinical Data Integration for Drug Safety

End-to-end drug safety review pipeline that integrates FDA label information, FAERS spontaneous reports, disproportionality signal detection, pharmacogenomic biomarkers, clinical trial data, and published literature. Designed for regulatory assessments, pharmacovigilance, and clinical decision support.

**Guiding principles**:
1. **Label is ground truth** -- FDA-approved labeling is the authoritative starting point for known safety information
2. **Signals need context** -- a FAERS signal without label or literature corroboration is hypothesis-generating, not confirmatory
3. **Disproportionality is not causation** -- PRR/ROR measure reporting patterns, not causal relationships
4. **Pharmacogenomics narrows risk** -- PGx biomarkers can identify which patients face elevated risk
5. **Progressive reporting** -- create the report file early; update section by section
6. **English-first queries** -- use English drug names in all tool calls; respond in the user's language

Clinical data integration starts with data harmonization. Different hospitals code the same diagnosis differently (ICD-10 vs SNOMED). Before merging datasets, verify the coding system. Missing data is informative — a missing lab value may mean the test wasn't ordered (patient was stable) not that the result was normal.

## LOOK UP, DON'T GUESS
When uncertain about any scientific fact, SEARCH databases first rather than reasoning from memory. A database-verified answer is always more reliable than a guess.

**Differentiation**: This skill emphasizes *regulatory-grade data integration* across the full drug lifecycle. For focused FAERS signal detection with quantitative scoring, see `tooluniverse-adverse-event-detection`. For general pharmacovigilance workflows, see `tooluniverse-pharmacovigilance`.

---

## COMPUTE, DON'T DESCRIBE
When analysis requires computation (statistics, data processing, scoring, enrichment), write and run Python code via Bash. Don't describe what you would do — execute it and report actual results. Use ToolUniverse tools to retrieve data, then Python (pandas, scipy, statsmodels, matplotlib) to analyze it.

## When to Use

Typical triggers:
- "Give me a full safety review for [drug]"
- "What does the FDA label say about [drug] and [event]?"
- "Are there FAERS signals for [drug]?"
- "What pharmacogenomic biomarkers exist for [drug]?"
- "Find clinical trials studying [drug] safety"
- "Post-market surveillance summary for [drug]"
- "Compare safety profiles of [drug A] and [drug B]"

---

## Core Data Sources

| Source | Type | Best For |
|--------|------|----------|
| **FDA Labels (DailyMed)** | Regulatory | Approved safety information, boxed warnings, drug interactions |
| **FAERS** | Spontaneous reports | Post-market adverse event signals, demographic patterns |
| **CPIC** | Guidelines | Pharmacogenomic dosing recommendations |
| **FDA PGx Biomarkers** | Regulatory | Approved pharmacogenomic labeling |
| **ClinicalTrials.gov** | Trial registry | Ongoing/completed safety trials |
| **PubMed** | Literature | Published safety studies, case reports |

---

## Workflow Overview

```
Phase 0: Drug Identity & Context
  Resolve drug name, get class, mechanism, indications
    |
Phase 1: FDA Label Extraction
  Boxed warnings, contraindications, adverse reactions, interactions
    |
Phase 2: FAERS Signal Detection
  Top adverse events, disproportionality (PRR/ROR), demographics
    |
Phase 3: Pharmacogenomics
  CPIC guidelines, FDA PGx biomarkers, genotype-specific risks
    |
Phase 4: Clinical Trials
  Safety-focused trials, risk evaluation programs
    |
Phase 5: Literature Evidence
  PubMed safety studies, case reports, meta-analyses
    |
Phase 6: Integrated Safety Report
  Synthesize all sources into a cohesive safety profile
```

---

## Phase Details

### Phase 0: Drug Identity & Context

**Objective**: Unambiguously identify the drug and establish baseline context.

**Tools**:
- `DailyMed_search_spls` -- search Structured Product Labels
  - Input: `query` (drug name)
  - Output: SPL list with set IDs, titles, labeler names
- `OpenFDA_get_approval_history` -- get approval dates and supplements
  - Input: `drug_name` (generic or brand name)
  - Output: approval dates, application numbers, supplement history

**Workflow**:
1. Search DailyMed to confirm the drug name and identify the correct SPL
2. Get approval history to establish how long the drug has been marketed
3. Note the therapeutic class, mechanism of action, and approved indications
4. Record brand names vs generic name for consistent FAERS queries

**Tip**: FAERS uses `medicinalproduct` which can be brand or generic. Try both forms in Phase 2.

### Phase 1: FDA Label Extraction

**Objective**: Extract all safety-relevant sections from the FDA-approved label.

**Tools**:
- `FDA_get_boxed_warning_info_by_drug_name` -- boxed (black box) warnings
  - Input: `drug_name`
  - Output: warning text, or `{error: {code: "NOT_FOUND"}}` if none exists (normal)
- `FDA_get_warnings_and_cautions_by_drug_name` -- warnings and precautions section
  - Input: `drug_name`
  - Output: full warnings text
- `DailyMed_parse_adverse_reactions` -- adverse reactions from label
  - Input: `setid` (NOT `set_id`; from Phase 0 DailyMed search)
  - Output: parsed adverse reaction tables and text
- `DailyMed_parse_drug_interactions` -- drug interaction section
  - Input: `setid` (NOT `set_id`)
  - Output: parsed interaction data

**Workflow**:
1. Check for boxed warnings first -- these represent the most serious safety concerns
2. Extract warnings and precautions
3. Parse adverse reactions (both clinical trial rates and post-marketing reports)
4. Extract drug interactions
5. A `NOT_FOUND` response for boxed warnings is normal and means no boxed warning exists

**Label section priority**: Boxed Warning > Contraindications > Warnings/Precautions > Adverse Reactions > Drug Interactions

### Phase 2: FAERS Signal Detection

**Objective**: Identify post-market safety signals from spontaneous reports.

**Tools**:
- `FAERS_count_reactions_by_drug_event` -- top adverse events by frequency
  - Input: `medicinalproduct` (drug name, NOT `drug_name`)
  - Output: `[{term, count}]`
- `FAERS_calculate_disproportionality` -- PRR, ROR, IC for drug-event pair
  - Input: `drug_name`, `adverse_event`
  - Output: `{metrics: {PRR: {value, ci_95_lower, ci_95_upper}, ROR: {...}, IC: {...}}, signal_detection: {signal_detected, signal_strength}}`
- `FAERS_filter_serious_events` -- filter by seriousness type
  - Input: `drug_name`, `seriousness_type` (all/death/hospitalization/disability/life_threatening)
  - Output: serious event breakdown
- `FAERS_stratify_by_demographics` -- age/sex/country stratification
  - Input: `drug_name`, `adverse_event` (optional), `stratify_by` (sex/age/country)
  - Output: demographic breakdown (sex codes: 0=Unknown, 1=Male, 2=Female)

**Workflow**:
1. Get top 20 adverse events by report count
2. For the top 10-15, calculate disproportionality (PRR, ROR, IC with 95% CI)
3. Signal criteria: PRR >= 2.0, lower CI > 1.0, N >= 3 reports
4. For detected signals, filter by seriousness (deaths, hospitalizations)
5. Stratify strong signals by demographics to identify at-risk populations

**Important notes**:
- `FAERS_count_reactions_by_drug_event` uses `medicinalproduct` param, not `drug_name`
- `FAERS_calculate_disproportionality` uses `drug_name` param
- MedDRA term levels differ between count and disproportionality tools; case counts may not match exactly

**FAERS signal interpretation** — what the numbers mean:

| Metric | Value | Interpretation |
|--------|-------|---------------|
| **PRR** (Proportional Reporting Ratio) | < 1.0 | Event reported LESS than expected (possible protective effect or underreporting) |
| | 1.0-2.0 | No signal or weak signal |
| | 2.0-5.0 | **Moderate signal** — warrants investigation |
| | > 5.0 | **Strong signal** — likely real association (but still not proof of causation) |
| **ROR** (Reporting Odds Ratio) | Similar to PRR but accounts for all other drugs | Same thresholds as PRR; slightly more robust |
| **IC** (Information Component) | < 0 | No signal |
| | 0-2 | Weak signal |
| | > 2 | **Strong signal** |

**Signal ≠ Causation**: A strong FAERS signal means the drug-event pair is reported more often than expected. This could be due to:
- True causal relationship (most important)
- Channeling bias (sicker patients get the drug)
- Notoriety bias (media attention increases reporting)
- Protopathic bias (drug prescribed for early symptoms of the event)

**How to assess signal credibility**:
1. Is the event in the FDA label? (Label confirmation = strongest evidence)
2. Is there a plausible mechanism? (Drug's pharmacology explains the event)
3. Is there a dose-response? (Higher doses → more events)
4. Is there temporal consistency? (Event occurs after drug start, resolves after stop)
5. Is there epidemiological confirmation? (Published case-control or cohort study)

### Phase 3: Pharmacogenomics

**Objective**: Identify genetic factors that modify drug safety.

**Tools**:
- `CPIC_list_guidelines` -- get CPIC pharmacogenomic guidelines
  - Input: optional `gene`, `drug` filters
  - Output: guidelines with gene-drug pairs, dosing recommendations
- `fda_pharmacogenomic_biomarkers` -- FDA-approved PGx biomarkers
  - Input: optional `drug_name`, `biomarker`, `limit` (default 10; use `limit=1000` for comprehensive results)
  - Output: `{count, shown, results}` with biomarker, drug, therapeutic area

**Workflow**:
1. Search CPIC for guidelines involving this drug
2. Query FDA PGx biomarkers with the drug name
3. For each PGx finding, note: the gene, the actionable alleles, and the clinical recommendation
4. Classify as: required testing (boxed warning), recommended testing, or informational

**Tip**: Use `limit=1000` with `fda_pharmacogenomic_biomarkers` to avoid missing entries (default limit is only 10).

### Phase 4: Clinical Trials

**Objective**: Find ongoing or completed trials studying drug safety.

**Tools**:
- `search_clinical_trials` -- search ClinicalTrials.gov
  - Input: `query_term` (required), optional `condition`, `intervention`, `pageSize`
  - Output: `{studies, nextPageToken, total_count}` or string if no results

**Workflow**:
1. Search for safety-focused trials: "[drug] safety" or "[drug] adverse events"
2. Search for Risk Evaluation and Mitigation Strategies (REMS) trials
3. Look for post-marketing requirement (PMR) studies
4. Note trial status (recruiting, completed, terminated) and primary endpoints

**Query tip**: Simple queries work best. Complex multi-word queries often return no results. Search "[drug name]" first, then filter by safety-related keywords in the results.

### Phase 5: Literature Evidence

**Objective**: Find published safety studies, case reports, and meta-analyses.

**Tools**:
- `PubMed_search_articles` -- search biomedical literature
  - Input: `query` (search term), optional `limit`
  - Output: list of articles (plain list of dicts, NOT `{articles: [...]}`)

**Workflow**:
1. Search: "[drug] adverse events" or "[drug] safety"
2. Search: "[drug] [specific adverse event]" for signals found in Phase 2
3. Look for systematic reviews and meta-analyses
4. Prioritize: meta-analyses > RCTs > cohort studies > case reports

### Phase 6: Integrated Safety Report

Synthesize all phases into a cohesive report:

1. **Drug Overview** -- identity, class, mechanism, approval date, indications
2. **Labeled Safety Information** -- boxed warnings, key contraindications, known adverse reactions
3. **Post-Market Signals** -- FAERS signals with disproportionality metrics, compared to label
   - Distinguish: *known and labeled* vs *known but under-labeled* vs *potential new signal*
4. **Pharmacogenomic Considerations** -- PGx biomarkers, testing recommendations
5. **Clinical Trial Safety Data** -- ongoing monitoring studies, REMS programs
6. **Literature Summary** -- key publications supporting or refining safety profile
7. **Integrated Assessment** -- overall risk characterization, populations at elevated risk, data gaps

**Evidence grading**:
- T1: FDA label / regulatory action (boxed warning, REMS)
- T2: Strong FAERS signal (PRR >= 5, multiple data sources agree)
- T3: Moderate signal or single-source evidence
- T4: Literature mention or computational prediction only

---

## Common Analysis Patterns

| Pattern | Description | Key Phases |
|---------|-------------|------------|
| **Full Safety Review** | Comprehensive regulatory-style review | All (0-6) |
| **Label vs Real-World** | Compare FDA label to FAERS signals | 0, 1, 2, 6 |
| **PGx Safety Assessment** | Focus on pharmacogenomic risk factors | 0, 1, 3, 5 |
| **Signal Investigation** | Deep-dive into a specific adverse event | 0, 1, 2, 5, 6 |
| **Drug Comparison** | Head-to-head safety comparison of two drugs | Run phases 0-2 for each, compare in Phase 6 |

---

## Edge Cases & Fallbacks

- **New drug with little FAERS data**: Rely on FDA label, clinical trials, and mechanism-based prediction
- **OTC drugs**: May have limited FAERS data; DailyMed still has OTC labels
- **Combination products**: Search FAERS for each active ingredient separately, then the combination
- **Brand vs generic discrepancies**: FAERS reports may use either; search both forms
- **No CPIC guideline**: Normal for most drugs; only ~30 gene-drug pairs have CPIC guidelines

---

## Limitations

- **FAERS reporting bias**: Spontaneous reports are voluntary; under-reporting is the norm
- **No denominator in FAERS**: Cannot calculate incidence rates, only disproportionality
- **Label lag**: FDA labels may not reflect the latest evidence; always supplement with FAERS and literature
- **PGx coverage**: CPIC and FDA PGx biomarkers cover a fraction of all drugs
- **ClinicalTrials.gov completeness**: Not all trials report results; some safety data is only in publications
