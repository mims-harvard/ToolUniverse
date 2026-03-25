---
name: tooluniverse-pharmacovigilance
description: Analyze drug safety signals from FDA adverse event reports, label warnings, and pharmacogenomic data. Calculates disproportionality measures (PRR, ROR), identifies serious adverse events, assesses pharmacogenomic risk variants. Use when asked about drug safety, adverse events, post-market surveillance, or risk-benefit assessment.
---

# Pharmacovigilance Safety Analyzer

Systematic drug safety analysis using FAERS adverse event data, FDA labeling, PharmGKB pharmacogenomics, and clinical trial safety signals.

**KEY PRINCIPLES**:
1. **Report-first approach** - Create report file FIRST, update progressively
2. **Signal quantification** - Use disproportionality measures (PRR, ROR)
3. **Severity stratification** - Prioritize serious/fatal events
4. **Multi-source triangulation** - FAERS, labels, trials, literature
5. **Pharmacogenomic context** - Include genetic risk factors
6. **Actionable output** - Risk-benefit summary with recommendations
7. **English-first queries** - Always use English drug names in tool calls

---

## When to Use

Apply when user asks:
- "What are the safety concerns for [drug]?"
- "What adverse events are associated with [drug]?"
- "Is [drug] safe? What are the risks?"
- "Compare safety profiles of [drug A] vs [drug B]"
- "Pharmacovigilance analysis for [drug]"

---

## Critical Workflow Requirements

### Report-First Approach (MANDATORY)

1. Create `[DRUG]_safety_report.md` FIRST with all section headers and `[Researching...]` placeholders
2. Progressively update as data is gathered
3. Output separate data files: `[DRUG]_adverse_events.csv` and `[DRUG]_pharmacogenomics.csv`

### Citation Requirements (MANDATORY)

Every safety signal MUST include source tool, data period, PRR, case counts, and serious/fatal breakdown.

---

## Tool Parameter Reference (CRITICAL)

| Tool | WRONG Parameter | CORRECT Parameter |
|------|-----------------|-------------------|
| `FAERS_count_reactions_by_drug_event` | `drug` | `drug_name` |
| `FAERS_filter_serious_events` | American spelling (e.g., "Hemorrhage") | MedDRA British spelling (e.g., "Haemorrhage") |
| `FAERS_stratify_by_demographics` | Requiring `adverse_event` | `adverse_event` is optional (omit for all-event stratification) |
| `DailyMed_search_spls` | `name` | `drug_name` |
| `PharmGKB_search_drugs` | `drug` | `query` |
| `OpenFDA_search_drug_events` | `drug_name` | `search` |

---

## Workflow Overview

```
Phase 1: Drug Disambiguation
  -> Resolve drug name, get identifiers (ChEMBL, DrugBank)

Phase 2: Adverse Event Profiling (FAERS)
  -> Query FAERS, calculate PRR, stratify by seriousness

Phase 3: Label Warning Extraction
  -> DailyMed boxed warnings, contraindications, precautions

Phase 4: Pharmacogenomic Risk
  -> PharmGKB clinical annotations, high-risk genotypes

Phase 5: Clinical Trial Safety
  -> ClinicalTrials.gov Phase 3/4 safety data

Phase 5.5: Pathway & Mechanism Context
  -> KEGG drug metabolism, target pathway analysis

Phase 5.6: Literature Intelligence
  -> PubMed, BioRxiv/MedRxiv, OpenAlex citation analysis

Phase 6: Signal Prioritization
  -> Rank by PRR x severity x frequency

Phase 7: Report Synthesis
```

---

## Phase 1: Drug Disambiguation

1. Search DailyMed via `DailyMed_search_spls(drug_name=...)` for NDC, SPL setid, generic name
2. Search ChEMBL via `ChEMBL_search_drugs(query=...)` for molecule ID, max phase
3. Document: generic name, brand names, drug class, mechanism, approval date

## Phase 2: Adverse Event Profiling (FAERS)

1. Query `FAERS_count_reactions_by_drug_event(drug_name=..., limit=50)` for top events
2. For each event, get detailed breakdown (serious, fatal, hospitalization counts)
3. Calculate PRR: `(A/B) / (C/D)` where A=drug+event, B=drug+any, C=event+any_other, D=total_other
4. Apply signal thresholds: PRR > 2.0 (signal), > 3.0 (strong signal), case count >= 3

**Severity classification**:
- Fatal (highest priority), Life-threatening, Hospitalization, Disability, Other serious, Non-serious

### FAERS `filter_serious_events` -- MedDRA Spelling (CRITICAL)

`FAERS_filter_serious_events` uses **MedDRA preferred terms** which follow British
English spelling conventions. Common examples:

| Incorrect (American) | Correct (MedDRA/British) |
|----------------------|--------------------------|
| HEMORRHAGE | Haemorrhage |
| ANEMIA | Anaemia |
| EDEMA | Oedema |
| DIARRHEA | Diarrhoea |
| LEUKOPENIA | Leucopenia |
| ESOPHAGITIS | Oesophagitis |

The `adverse_event` parameter should use the **exact MedDRA preferred term spelling**.
Using American English spelling or uppercase will return zero results or incorrect matches.
When in doubt, first query `FAERS_count_reactions_by_drug_event` to see the exact event
names as they appear in the FAERS database, then use those exact strings.

**Additional FAERS notes:**
- `adverse_event` is now correctly appended to the OpenFDA query in `_filter_serious_events`
- `FAERS_stratify_by_demographics`: `adverse_event` is optional -- when omitted, stratification
  covers all events for the drug. Sex codes: 0=Unknown, 1=Male, 2=Female

See [SIGNAL_DETECTION.md](SIGNAL_DETECTION.md) for detailed disproportionality formulas and example output tables.

## Phase 3: Label Warning Extraction

1. Get label via `DailyMed_get_spl_by_set_id(setid=...)`
2. Extract: boxed warnings, contraindications, warnings/precautions, drug interactions
3. Categorize severity: Boxed Warning > Contraindication > Warning > Precaution

## Phase 4: Pharmacogenomic Risk

1. Search `PharmGKB_search_drug(query=...)` for clinical annotations
2. Document actionable variants with evidence levels (1A/1B/2A/2B/3)
3. Note CPIC/DPWG guideline status

**PGx Evidence Levels**:
| Level | Description | Action |
|-------|-------------|--------|
| 1A | CPIC/DPWG guideline, implementable | Follow guideline |
| 1B | CPIC/DPWG guideline, annotation | Consider testing |
| 2A | VIP annotation, moderate evidence | May inform |
| 2B | VIP annotation, weaker evidence | Research |
| 3 | Low-level annotation | Not actionable |

## Phase 5: Clinical Trial Safety

1. Search `search_clinical_trials(intervention=..., phase="Phase 3", status="Completed")`
2. Extract serious AE rates, discontinuation rates, deaths
3. Compare drug vs placebo rates

## Phase 5.5: Pathway & Mechanism Context

1. Query KEGG for drug metabolism pathways
2. Analyze target pathways for mechanistic basis of AEs
3. Document pathway-AE relationships

## Phase 5.6: Literature Intelligence

1. PubMed: `PubMed_search_articles(query='"[drug]" AND (safety OR adverse OR toxicity)')`
2. BioRxiv/MedRxiv: Search for recent preprints (flag as not peer-reviewed)
3. OpenAlex: Citation analysis for key safety papers

## Phase 6: Signal Prioritization

**Signal Score** = PRR x Severity_Weight x log10(Case_Count + 1)

Severity weights: Fatal=10, Life-threatening=8, Hospitalization=5, Disability=5, Other serious=3, Non-serious=1

Categorize signals:
- **Critical** (immediate attention): High PRR + fatal outcomes
- **Moderate** (monitor): Moderate PRR + serious outcomes
- **Known/Expected** (manage clinically): Low PRR, in label

---

## Output Report

Save as `[DRUG]_safety_report.md`. See [REPORT_TEMPLATES.md](REPORT_TEMPLATES.md) for the full report structure and example outputs.

---

## Evidence Grading

| Tier | Criteria | Example |
|------|----------|---------|
| T1 | PRR >10, fatal outcomes, boxed warning | Lactic acidosis |
| T2 | PRR 3-10, serious outcomes | Hepatotoxicity |
| T3 | PRR 2-3, moderate concern | Hypoglycemia |
| T4 | PRR <2, known/expected | GI side effects |

---

## Fallback Chains

| Primary Tool | Fallback 1 | Fallback 2 |
|--------------|------------|------------|
| `FAERS_count_reactions_by_drug_event` | `OpenFDA_search_drug_events` | Literature search |
| `DailyMed_search_spls` | `OpenFDA_search_drug_labels` | DailyMed website |
| `PharmGKB_search_drugs` | `CPIC_list_guidelines` | Literature search |
| `search_clinical_trials` | `ClinicalTrials.gov` API | PubMed for trial results |

---

## Completeness Checklist

See [CHECKLIST.md](CHECKLIST.md) for the full phase-by-phase verification checklist.

---

## References

- FAERS: https://www.fda.gov/drugs/questions-and-answers-fdas-adverse-event-reporting-system-faers
- DailyMed: https://dailymed.nlm.nih.gov
- PharmGKB: https://www.pharmgkb.org
- ClinicalTrials.gov: https://clinicaltrials.gov
- OpenFDA: https://open.fda.gov
- KEGG Drug: https://www.genome.jp/kegg/drug
- Tool documentation: [TOOLS_REFERENCE.md](TOOLS_REFERENCE.md)
