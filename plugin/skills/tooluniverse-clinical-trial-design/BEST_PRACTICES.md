# Best Practices & Output Requirements

## Best Practices

### 1. Start with Report Template
Create full report structure FIRST, then populate:
```markdown
# Clinical Trial Feasibility Report: [INDICATION]
## 1. Executive Summary
[Researching...]
## 2. Disease Background
[Researching...]
[...all 14 sections...]
```

### 2. Use English for All Tool Calls
Even if user asks in another language:
- "EGFR+ NSCLC" not local-language equivalents
- "breast cancer" not translations
- Translate results back to user's language

### 3. Validate Biomarker Prevalence Across Sources
Cross-check ClinVar, gnomAD, COSMIC, and literature:
- ClinVar: Clinical significance
- gnomAD: Population frequency (for germline)
- COSMIC: Somatic mutation frequency in cancers
- Literature: Geographic/ethnic variation

### 4. Calculate Enrollment Funnel Explicitly
Show math for patient availability:
```
US NSCLC incidence: 200,000/year
x EGFR+ prevalence: 15% = 30,000
x L858R within EGFR+: 45% = 13,500
x Eligible (age, PS, prior Tx): 60% = 8,100
/ Competing trials: 3 = 2,700 available/year

For N=43, need 43/2,700 = 1.6% capture rate -> Achievable
```

### 5. Evidence Grade Every Key Claim
```markdown
EGFR L858R prevalence is 45% of EGFR+ NSCLC [A: PMID:12345, large
sequencing study n=1,500]. *Source: ClinVar, COSMIC*
```

### 6. Provide Regulatory Precedent Details
Not just "ORR is accepted" but:
```markdown
ORR is FDA-accepted for accelerated approval in NSCLC [A: FDA approvals]:
- Osimertinib (2015): ORR 57%, n=411, Tx-resistant EGFR+ (NCT01802632)
- Dacomitinib (2018): ORR 45%, n=452, 1L EGFR+ (NCT01774721)
- [3 more examples]
```

### 7. Address Feasibility Risks Proactively
For each HIGH risk, provide mitigation:
```markdown
Risk: Biomarker screen failure rate >70%
-> Mitigation: Liquid biopsy pre-screening (ctDNA EGFR, 7-day turnaround)
```

### 8. Separate Phase 1 and Phase 2 Components
If combined Phase 1/2:
- Phase 1: Safety, DLT, RP2D (N=12-18, 3+3 or BOIN)
- Phase 2: Efficacy, ORR (N=43, Simon 2-stage)
- Distinct success criteria for each phase

---

## Common Pitfalls to Avoid

### Don't: Show Tool Outputs to User
```markdown
# BAD
OpenTargets returned:
{
  "data": {
    "id": "EFO_0003060",
    "name": "non-small cell lung carcinoma"
  }
}
```

### Do: Present Synthesized Report
```markdown
# GOOD
## Disease Background
Non-small cell lung cancer (NSCLC) represents 85% of lung cancers, with
~200,000 new cases annually in the US [A: CDC WONDER]. EGFR mutations
occur in 15% of Caucasian and 50% of Asian patients [A: PMID:23816960].
*Source: OpenTargets, ClinVar*
```

### Don't: Make Unsupported Claims
```markdown
# BAD
ORR of 60% is expected based on preclinical data.
```

### Do: Ground in Evidence
```markdown
# GOOD
ORR of 30-40% is projected [B] based on:
- Similar EGFR TKI (erlotinib): 32% ORR in EGFR+ NSCLC (NCT00949650)
- Our drug's 2x IC50 potency vs. erlotinib (preclinical)
*Source: ClinicalTrials.gov, internal data*
```

### Don't: Ignore Geographic Variation
```markdown
# BAD
EGFR L858R prevalence: 7% of NSCLC
```

### Do: Specify Geography
```markdown
# GOOD
EGFR L858R prevalence [A: COSMIC, ClinVar]:
- Caucasian (US/EU): 6-7% of NSCLC
- East Asian: 20-25% of NSCLC
-> Trial site strategy: Include Asian sites for 2x enrollment
```

---

## Output Format Requirements

### Report File Naming
- `[INDICATION]_trial_feasibility_report.md`
- Example: `EGFR_L858R_NSCLC_trial_feasibility_report.md`

### Section Completeness
All 14 sections MUST be present (see REPORT_TEMPLATE.md for details):
1. Executive Summary
2. Disease Background
3. Patient Population Analysis (with funnel)
4. Biomarker Strategy
5. Endpoint Selection & Justification
6. Comparator Analysis
7. Safety Endpoints & Monitoring Plan
8. Study Design Recommendations
9. Enrollment & Site Strategy
10. Regulatory Pathway
11. Budget & Resource Considerations
12. Risk Assessment
13. Success Criteria & Go/No-Go Decision (with scorecard)
14. Recommendations & Next Steps

### Evidence Grading Required In
- Section 1 (Executive Summary): Key findings
- Section 4 (Biomarker): Prevalence claims
- Section 5 (Endpoints): Regulatory precedents
- Section 6 (Comparator): SOC efficacy data
- Section 7 (Safety): Toxicity frequencies
- Section 10 (Regulatory): Approval precedents
- Section 13 (Scorecard): All dimensions

### Feasibility Score Transparency
Show calculation:
```markdown
| Dimension | Weight | Raw Score | Weighted | Evidence |
|-----------|--------|-----------|----------|----------|
| Patient Availability | 30% | 8/10 | 24 | A: Epi data |
| Endpoint Precedent | 25% | 9/10 | 22.5 | A: FDA approvals |
| Regulatory Clarity | 20% | 7/10 | 14 | B: Pre-IND advised |
| Comparator Feasibility | 15% | 9/10 | 13.5 | A: Generic avail |
| Safety Monitoring | 10% | 8/10 | 8 | B: Class effects |
| **TOTAL** | **100%** | - | **82/100** | **HIGH** |
```
