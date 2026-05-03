# Precision Oncology - Completeness Checklist

Use this checklist to verify report completeness before delivery.

## Pre-Execution Checklist

- [ ] User provided cancer type
- [ ] User provided molecular profile (mutations/fusions/amplifications)
- [ ] Prior therapy history obtained (or confirmed treatment-naive)
- [ ] Tool parameters verified (see SKILL.md Phase 0)

---

## Report Section Checklist

### Section 1: Variant Interpretation
- [ ] All reported variants included in table
- [ ] Each variant has significance assessment
- [ ] Each variant has evidence level (★★★/★★☆/★☆☆/☆☆☆)
- [ ] Clinical implication stated for each variant
- [ ] Sources cited (CIViC EID, ClinVar VCV, PMID)

### Section 2: Treatment Recommendations
- [ ] ≥1 first-line option with ★★★ evidence (or explanation why none)
- [ ] Dosing information included
- [ ] Key trial data cited (ORR, PFS, OS where available)
- [ ] Contraindications/cautions noted if applicable
- [ ] FDA approval status stated

### Section 3: Resistance Analysis
- [ ] Current resistance mechanism explained (if applicable)
- [ ] Structural basis described (if known)
- [ ] Future resistance mechanisms anticipated
- [ ] Monitoring strategy suggested
- [ ] "Not applicable" stated if treatment-naive

### Section 4: Clinical Trials
- [ ] ≥3 relevant trials listed (or "no matching trials")
- [ ] NCT IDs included
- [ ] Phase stated
- [ ] Status (Recruiting/Active) stated
- [ ] Biomarker requirement noted
- [ ] Access date noted

### Section 5: Next Steps
- [ ] Specific treatment recommendation made
- [ ] Follow-up plan stated
- [ ] Additional testing recommended if appropriate
- [ ] Timeline suggested (when to reassess)

---

## Executive Summary Checklist

- [ ] Summarizes key finding in 2-3 sentences
- [ ] States recommended treatment explicitly
- [ ] Evidence level mentioned
- [ ] Actionable (tells user what to DO)

---

## Data Quality Checklist

- [ ] All sources cited (CIViC, ClinVar, PMID, NCT, FDA)
- [ ] Evidence grades applied consistently
- [ ] No unsupported claims
- [ ] Data gaps acknowledged in relevant sections

---

## Tool Execution Checklist

| Tool Category | Executed | Fallback Used | Notes |
|---------------|----------|---------------|-------|
| CIViC variant lookup | [ ] | [ ] | |
| ClinVar lookup | [ ] | [ ] | |
| OpenTargets drugs | [ ] | [ ] | |
| ClinicalTrials.gov | [ ] | [ ] | |
| PubMed (resistance) | [ ] | [ ] | If applicable |
| NvidiaNIM (structure) | [ ] | [ ] | If needed |

---

## Final Quality Check

- [ ] Report is actionable (answers "what should we do?")
- [ ] No tool outputs shown directly (processed into narrative)
- [ ] Appropriate caveats for uncertainty
- [ ] Patient-specific (not generic disease info)
- [ ] Reviewed for clinical accuracy

---

## Data Gaps Documentation

If any tool failed or data unavailable:

| Section | Missing Data | Reason | Alternative |
|---------|--------------|--------|-------------|
| | | | |
| | | | |

---

## Sign-off

- Report generated: [ ] Yes
- Completeness verified: [ ] Yes
- Ready for delivery: [ ] Yes
