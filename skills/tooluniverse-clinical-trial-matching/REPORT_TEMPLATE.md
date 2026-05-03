# Report Template

Use the following markdown structure for the final clinical trial matching report.

## File Naming Convention

```
clinical_trial_matching_[DISEASE]_[BIOMARKER]_[DATE].md
```
Example: `clinical_trial_matching_NSCLC_EGFR_L858R_2026-02-15.md`

## Template

```markdown
# Clinical Trial Matching Report

**Patient**: [Disease type] with [biomarker(s)]
**Date**: [Current date]
**Trials Analyzed**: [N total] | **Top Matches**: [N with score >= 60]

---

## Executive Summary

**Top 3 Trial Recommendations**:

1. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   - Phase: [Phase], Status: [Status]
   - Why: [Key reason for match]

2. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   ...

3. **[NCT ID]** - [Brief title] (Score: XX/100, Tier N)
   ...

---

## Patient Profile Summary

| Parameter | Value | Standardized |
|-----------|-------|-------------|
| Disease | [input] | [EFO name] (EFO_XXXX) |
| Biomarker(s) | [input] | [gene: variant, type] |
| Stage | [input] | [standardized] |
| Prior Treatment | [input] | [standardized] |
| Performance Status | [input] | [ECOG score] |
| Location | [input] | [city, state] |

### Biomarker Actionability
| Biomarker | Actionability Level | FDA-Approved Drugs | Evidence |
|-----------|--------------------|--------------------|----------|
| [gene variant] | [FDA-approved/investigational] | [drugs] | [T1/T2/T3/T4] |

---

## Ranked Trial Matches

### Trial 1: [NCT ID] - [Title]

**Trial Match Score: XX/100** (Tier N: [Label])

| Component | Score | Details |
|-----------|-------|---------|
| Molecular Match | XX/40 | [explanation] |
| Clinical Eligibility | XX/25 | [explanation] |
| Evidence Strength | XX/20 | [explanation] |
| Trial Phase | XX/10 | [phase] |
| Geographic | XX/5 | [location info] |

**Trial Details**:
- **Phase**: [Phase]
- **Status**: [Recruiting/Active/etc.]
- **Sponsor**: [Sponsor]
- **Start Date**: [Date]
- **Estimated Completion**: [Date]

**Interventions**:
- [Drug name]: [Mechanism] | [Dosing info if available]
- [Comparator]: [Description]

**Molecular Eligibility Match**:
- Required biomarkers: [list]
- Patient match: [Exact/Gene-level/Pathway/None]
- Notes: [details]

**Clinical Eligibility Assessment**:
- Disease type: [Match/Mismatch]
- Stage: [Match/Mismatch/Unclear]
- Prior treatment: [Match/Mismatch/Unclear]
- Performance status: [Match/Mismatch/Unclear]

**Evidence for Efficacy**:
- FDA approval: [Yes/No for this indication]
- Clinical results: [Phase III/II/I data if available]
- Mechanism alignment: [Drug targets patient's biomarker: Yes/No]
- Literature: [Key references]

**Trial Sites** (first 5):
- [City, State, Country]
- ...

**Next Steps**: [Contact info, enrollment instructions]

[Repeat for each matched trial]

---

## Trials by Category

### Targeted Therapy Trials
[List trials with targeted agents matching patient's biomarkers]

### Immunotherapy Trials
[List immunotherapy trials, noting PD-L1/TMB/MSI requirements]

### Combination Therapy Trials
[List trials with drug combinations]

### Basket/Platform Trials
[List biomarker-agnostic or multi-arm trials]

---

## Additional Testing Recommendations

If the patient has not been tested for certain biomarkers, these trials would become relevant:

| Biomarker | Test Needed | Trials Unlocked | Priority |
|-----------|-------------|----------------|----------|
| [e.g., TMB] | [NGS panel] | [NCT IDs] | [High/Medium/Low] |

---

## Alternative Options

### Expanded Access Programs
[List any expanded access or compassionate use programs]

### Off-Label Options
[FDA-approved drugs for other indications with same biomarker]

---

## Evidence Grading Summary

| Evidence Tier | Count | Description |
|--------------|-------|-------------|
| T1 (FDA/Guideline) | N | FDA-approved biomarker-drug, clinical guideline |
| T2 (Clinical) | N | Phase III data, robust clinical evidence |
| T3 (Emerging) | N | Phase I/II, preclinical evidence |
| T4 (Exploratory) | N | Computational, mechanism inference |

---

## Completeness Checklist

| Analysis Step | Status | Source |
|--------------|--------|--------|
| Disease standardization | [Done/Partial/Failed] | [OpenTargets/OLS] |
| Gene resolution | [Done/Partial/Failed] | [MyGene] |
| Biomarker actionability | [Done/Partial/Failed] | [FDA biomarkers] |
| Disease trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Biomarker trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Intervention trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Eligibility parsing | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Drug mechanism analysis | [Done/Partial/Failed] | [OpenTargets/ChEMBL] |
| Evidence assessment | [Done/Partial/Failed] | [FDA/PubMed/CIViC] |
| Location analysis | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Basket trial search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Expanded access search | [Done/Partial/Failed] | [ClinicalTrials.gov] |
| Scoring & ranking | [Done/Partial/Failed] | [Composite] |

---

## Disclaimer

This report is for informational and research purposes only. Clinical trial eligibility is ultimately determined by the trial investigators based on complete medical records. Patients should discuss all options with their healthcare team. Trial availability and status may change; verify current status at [ClinicalTrials.gov](https://clinicaltrials.gov).

## Sources

All data sourced from:
- ClinicalTrials.gov (trial search, eligibility, locations, status)
- OpenTargets Platform (drug-target associations, disease ontology)
- CIViC (clinical variant interpretations)
- ChEMBL (drug mechanisms, targets)
- FDA (approved indications, pharmacogenomic biomarkers, drug labels)
- DrugBank (drug targets, indications)
- PharmGKB (pharmacogenomics)
- PubMed/NCBI (literature evidence)
- OLS/EFO (disease ontology)
- MyGene (gene identifier resolution)
```
