# Adverse Event Detection - Report Template

## Report File Structure

**File**: `[DRUG]_adverse_event_report.md`

```markdown
# Adverse Drug Event Signal Detection Report: [DRUG]

**Generated**: [Date] | **Drug**: [Generic Name] | **ChEMBL ID**: [ID]
**Safety Signal Score**: [XX/100] ([INTERPRETATION])

---

## Executive Summary

[2-3 paragraph summary of key findings]

**Key Safety Signals**:
1. [Strongest signal with PRR/ROR]
2. [Second signal]
3. [Third signal]

**Regulatory Status**: [Boxed warning Y/N] | [Withdrawn Y/N] | [Restrictions]

---

## 1. Drug Identification
[Phase 0 output]

## 2. FAERS Adverse Event Profile
[Phase 1 output]

## 3. Disproportionality Analysis
[Phase 2 output]

## 4. FDA Label Safety Information
[Phase 3 output]

## 5. Mechanism-Based Context
[Phase 4 output]

## 6. Comparative Safety Analysis
[Phase 5 output]

## 7. Drug-Drug Interactions & PGx Risk
[Phase 6 output]

## 8. Literature Evidence
[Phase 7 output]

## 9. Risk Assessment
[Phase 8 output]

## 10. Clinical Recommendations

### 10.1 Monitoring Recommendations
| Parameter | Frequency | Rationale |
|-----------|-----------|-----------|
| [Lab test] | [Frequency] | [Why] |

### 10.2 Risk Mitigation Strategies
| Risk | Mitigation | Evidence |
|------|-----------|----------|
| [Risk] | [Strategy] | [Source] |

### 10.3 Patient Counseling Points
- [Point 1]
- [Point 2]

### 10.4 Populations at Higher Risk
| Population | Risk Factor | Recommendation |
|-----------|-------------|----------------|
| [Group] | [Factor] | [Action] |

---

## 11. Completeness Checklist
[See below]

## 12. Data Sources
[All tools and databases used with timestamps]
```

---

## Completeness Checklist

### Phase 0: Drug Disambiguation
- [ ] Generic name resolved
- [ ] ChEMBL ID obtained
- [ ] DrugBank ID obtained
- [ ] Drug class identified
- [ ] Mechanism of action stated
- [ ] Primary target identified
- [ ] Blackbox/withdrawal status checked

### Phase 1: FAERS Profiling
- [ ] Top adverse events queried (>=15 events)
- [ ] Seriousness distribution obtained
- [ ] Outcome distribution obtained
- [ ] Age distribution obtained
- [ ] Death-related events counted
- [ ] Reporter country distribution obtained

### Phase 2: Disproportionality Analysis
- [ ] PRR calculated for >= 10 adverse events
- [ ] ROR with 95% CI for each event
- [ ] IC with 95% CI for each event
- [ ] Signal strength classified for each
- [ ] Demographics stratified for strong signals

### Phase 3: FDA Label
- [ ] Boxed warnings checked (or confirmed none)
- [ ] Contraindications extracted
- [ ] Warnings and precautions extracted
- [ ] Adverse reactions from label
- [ ] Drug interactions from label
- [ ] Special populations (pregnancy, geriatric, pediatric)

### Phase 4: Mechanism Context
- [ ] Target safety profile (OpenTargets)
- [ ] OpenTargets adverse events queried
- [ ] ADMET predictions (if SMILES available)

### Phase 5: Comparative Analysis
- [ ] At least 1 class comparison performed
- [ ] Class-wide vs drug-specific signals identified
- [ ] Aggregate class AEs computed (if applicable)

### Phase 6: DDIs & PGx
- [ ] DDIs from FDA label extracted
- [ ] PharmGKB queried
- [ ] Dosing guidelines checked
- [ ] FDA PGx biomarkers checked

### Phase 7: Literature
- [ ] PubMed searched (>=10 articles)
- [ ] OpenAlex citation analysis (if time permits)
- [ ] Key safety publications cited

### Phase 8: Risk Assessment
- [ ] Safety Signal Score calculated (0-100)
- [ ] Each signal evidence-graded (T1-T4)
- [ ] Score interpretation provided

### Phase 9: Report
- [ ] Report file created and saved
- [ ] Executive summary written
- [ ] Monitoring recommendations provided
- [ ] Risk mitigation strategies listed
- [ ] Patient counseling points included
- [ ] All sources cited
