# Pharmacovigilance Safety Analyzer Checklist

Pre-delivery verification checklist for drug safety reports.

## Report Quality Checklist

### Structure & Format
- [ ] Report file created: `[DRUG]_safety_report.md`
- [ ] All 10 main sections present
- [ ] Executive summary completed (not `[Researching...]`)
- [ ] Data sources section populated

### Phase 1: Drug Identification
- [ ] Generic name documented
- [ ] Brand names listed
- [ ] Drug class identified
- [ ] ChEMBL ID or DrugBank ID obtained
- [ ] Mechanism of action stated
- [ ] Approval date noted

### Phase 2: FAERS Adverse Event Analysis
- [ ] FAERS data period stated (e.g., "Q1 2020 - Q4 2025")
- [ ] Total report count for drug provided
- [ ] ≥20 adverse events queried
- [ ] PRR calculated with 95% CI for top events
- [ ] Serious case counts included
- [ ] Fatal case counts included
- [ ] Signal thresholds applied (PRR >2, N ≥3)
- [ ] Top events ranked by frequency/signal strength

### Phase 3: FDA Label Warnings
- [ ] DailyMed SPL retrieved (or "Not available")
- [ ] Boxed warning extracted (or "None")
- [ ] Contraindications listed with rationale
- [ ] Key warnings and precautions summarized
- [ ] Drug interactions noted
- [ ] Source citation included

### Phase 4: Pharmacogenomics
- [ ] PharmGKB queried for drug
- [ ] Actionable variants listed (or "No actionable variants")
- [ ] Evidence levels assigned (1A, 1B, 2A, 2B, 3)
- [ ] Genes and variants specified
- [ ] Clinical recommendations stated
- [ ] CPIC/DPWG guideline status noted

### Phase 5: Clinical Trial Safety
- [ ] Phase 3/4 trials searched
- [ ] At least 3 trials summarized (or all available)
- [ ] Sample sizes provided
- [ ] Duration of studies noted
- [ ] Serious AE rates (drug vs placebo)
- [ ] Discontinuation rates compared
- [ ] Common AEs from trials listed

### Phase 6: Signal Prioritization
- [ ] Signals scored using formula (PRR × severity × frequency)
- [ ] Critical signals flagged (⚠️⚠️⚠️)
- [ ] Moderate signals identified
- [ ] Known/expected effects categorized
- [ ] Action recommendations for each signal

### Phase 7: Risk-Benefit Assessment
- [ ] Overall risk level stated
- [ ] Benefits summarized
- [ ] Risk factors identified
- [ ] Comparison to alternatives (if requested)

### Phase 8: Clinical Recommendations
- [ ] ≥3 monitoring recommendations
- [ ] Patient counseling points listed
- [ ] Contraindication checklist provided
- [ ] Pre-treatment assessment items

---

## Citation Requirements

### Every Section Must Include
- [ ] Source database name
- [ ] Tool used (in backticks)
- [ ] Data retrieval period (for FAERS)
- [ ] Specific identifiers where applicable

### Format Examples
```markdown
*Source: FAERS via `FAERS_count_reactions_by_drug_event` (Q1 2020 - Q4 2025)*
*Source: DailyMed via `DailyMed_search_spls` (setid: abc123)*
*Source: PharmGKB via `PharmGKB_search_drugs` (PA450360)*
*Source: ClinicalTrials.gov via `search_clinical_trials`*
```

---

## Signal Grading

### All Signals Must Have
- [ ] PRR value with 95% CI
- [ ] Case count (N)
- [ ] Serious/fatal breakdown
- [ ] Evidence tier assigned (T1-T4)

### Tier Definitions
| Tier | Symbol | Criteria |
|------|--------|----------|
| T1 | ⚠️⚠️⚠️ | PRR >10, fatal outcomes, or boxed warning |
| T2 | ⚠️⚠️ | PRR 3-10, serious outcomes |
| T3 | ⚠️ | PRR 2-3, moderate concern |
| T4 | ℹ️ | PRR <2, known/expected |

---

## Quantified Minimums

| Section | Minimum Requirement |
|---------|---------------------|
| Adverse events | Top 20 events with PRR |
| Serious AEs | All with fatal outcomes listed |
| Contraindications | All from label extracted |
| PGx variants | All level 1-2 variants |
| Clinical trials | ≥3 phase 3/4 trials |
| Monitoring recs | ≥3 specific recommendations |

---

## Safety Signal Metrics

### Required Calculations
- [ ] PRR (Proportional Reporting Ratio)
- [ ] 95% Confidence Interval for PRR
- [ ] Case count (total reports)
- [ ] Serious case percentage
- [ ] Fatal case count

### Signal Detection Criteria
| Criterion | Threshold | Status |
|-----------|-----------|--------|
| PRR | >2.0 | Signal |
| Chi-squared | >4.0 | Signal |
| N (cases) | ≥3 | Reportable |
| Lower 95% CI | >1.0 | Significant |

---

## Output Files

### Required
- [ ] `[DRUG]_safety_report.md` - Main report

### Optional (recommended)
- [ ] `[DRUG]_adverse_events.csv` - All AEs with metrics
- [ ] `[DRUG]_pharmacogenomics.csv` - PGx variants

### CSV Column Requirements
**adverse_events.csv**:
```
Adverse_Event,Report_Count,PRR,CI_Lower,CI_Upper,Serious_Count,Fatal_Count,Signal_Tier
```

**pharmacogenomics.csv**:
```
Gene,Variant,rs_ID,Phenotype,Evidence_Level,Recommendation
```

---

## Final Review

### Before Delivery
- [ ] No `[Researching...]` placeholders remaining
- [ ] All tables properly formatted
- [ ] No empty sections (use "Not available" if needed)
- [ ] Executive summary synthesizes key findings
- [ ] Recommendations are specific and actionable
- [ ] Risk-benefit conclusion stated

### Common Issues to Avoid
- [ ] PRR without confidence intervals
- [ ] Signals without case counts
- [ ] Missing serious/fatal breakdown
- [ ] PGx without evidence levels
- [ ] Recommendations without rationale
- [ ] Missing data period for FAERS

---

## Comparative Analysis (if requested)

### Drug Comparison Checklist
- [ ] Both drugs identified with same granularity
- [ ] Same FAERS time period used
- [ ] Head-to-head AE comparison table
- [ ] PRR comparison for shared AEs
- [ ] Class effect vs drug-specific noted
- [ ] Clear recommendation stated

---

## Urgent Findings Protocol

If any of these found, flag prominently in executive summary:
- [ ] Boxed warning not widely known
- [ ] Recent safety signal (new in last year)
- [ ] High fatality rate (>5% for serious AEs)
- [ ] Drug-drug interaction causing deaths
- [ ] Newly identified pharmacogenomic risk
- [ ] Recent FDA safety communication

### Flagging Format
```markdown
⚠️ **URGENT SAFETY ALERT** ⚠️

[Description of finding requiring immediate attention]

*First identified: [Date] | Source: [Database/Alert]*
```
