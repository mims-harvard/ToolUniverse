# Reviewed Dynamic REST ALS Validation

## Decision Question

Which active or upcoming US ALS studies are returned by the reviewed ClinicalTrials.gov search, and can a second generated operation retrieve the selected study consistently?

## Result

- Returned records: **20**
- Provider total matching records: **113**
- Additional page available: **yes**
- Deterministic follow-up record: **NCT01772602**
- Detail identifier matched search: **true**

## Cohort Summary

- Statuses: `{"ACTIVE_NOT_RECRUITING": 5, "NOT_YET_RECRUITING": 3, "RECRUITING": 12}`
- Phases: `{"NA": 4, "NOT_APPLICABLE": 8, "PHASE1": 4, "PHASE2": 3, "PHASE3": 2}`
- Intervention types: `{"BEHAVIORAL": 2, "BIOLOGICAL": 1, "COMBINATION_PRODUCT": 1, "DEVICE": 4, "DIETARY_SUPPLEMENT": 1, "DRUG": 14, "GENETIC": 1, "OTHER": 6}`
- Most represented US states: `[["California", 21], ["Pennsylvania", 16], ["Texas", 14], ["Florida", 13], ["New York", 11], ["Massachusetts", 9], ["Missouri", 8], ["Maryland", 7], ["Illinois", 7], ["Washington", 7]]`

## Returned Studies

| NCT ID | Status | Phase | Title | US locations |
| --- | --- | --- | --- | ---: |
| NCT04715399 | RECRUITING | N/A | UPenn Observational Research Repository on Neurodegenerative Disease | 1 |
| NCT01772602 | RECRUITING | N/A | The National Amyotrophic Lateral Sclerosis Registry | 1 |
| NCT07204977 | ACTIVE_NOT_RECRUITING | PHASE1 | Acamprosate in C9orf72 Hexanucleotide Repeat Expansion Amyotrophic Lateral Sclerosis (ACALS) | 1 |
| NCT04220021 | ACTIVE_NOT_RECRUITING | PHASE2 | Safety and Therapeutic Potential of the FDA-approved Drug Metformin for C9orf72 ALS/FTD | 1 |
| NCT02567136 | RECRUITING | N/A | Imaging Biomarkers in ALS | 1 |
| NCT05137665 | RECRUITING | N/A | Target ALS Biomarker Study; Longitudinal Biofluids, Clinical Measures, and At Home Measures | 10 |
| NCT07224256 | RECRUITING | NA | VOICE: An Early Feasibility Study of a Precise Robotically Implanted Brain-Computer Interface for Communication Restoration | 1 |
| NCT04244630 | RECRUITING | PHASE2 | Mitochondrial Capacity Boost in ALS (MICABO-ALS) Trial | 1 |
| NCT04875416 | ACTIVE_NOT_RECRUITING | N/A | Phenotype, Genotype and Biomarkers 2 | 3 |
| NCT07589764 | NOT_YET_RECRUITING | PHASE1 | A Widely Inclusive, Hybrid-Decentralized Pilot Trial Utilizing β-hydroxy-β-methylbutyrate to Lower IGFBP7 Levels in People With ALS | 2 |
| NCT06581861 | RECRUITING | N/A | PREVENT ALL ALS Study | 31 |
| NCT04297683 | ACTIVE_NOT_RECRUITING | PHASE2, PHASE3 | HEALEY ALS Platform Trial - Master Protocol | 81 |
| NCT06578195 | RECRUITING | N/A | ASSESS ALL ALS Study | 36 |
| NCT06968468 | NOT_YET_RECRUITING | NA | Resiliency Intervention for Patients With ALS and Their Care-Partners | 1 |
| NCT07290062 | RECRUITING | PHASE1 | A Study to Investigate the Safety and Pharmacodynamics of a Single Intrathecal Injection (IT) of INS1202 in Participants With Amyotrophic Lateral Sclerosis (ALS) | 5 |
| NCT06094205 | RECRUITING | NA | Feasibility of the BrainGate2 Neural Interface System in Persons With Tetraplegia (BG-Speech-02) | 1 |
| NCT07209943 | NOT_YET_RECRUITING | NA | Augmented Reality BCI Longitudinal Study for Persons With ALS, Stroke, TBI and SCI Utilizing Cognixion + Apple Vision Pro | 1 |
| NCT07233148 | RECRUITING | N/A | Healing ALS Registry Observational Study (HAROS) | 1 |
| NCT05695521 | ACTIVE_NOT_RECRUITING | PHASE1 | Regulatory T Cells for Amyotrophic Lateral Sclerosis | 3 |
| NCT07322003 | RECRUITING | PHASE3 | Pridopidine Phase 3 Study to Evaluate Efficacy and Safety in ALS | 18 |

## Execution Evidence

- `VSDReviewedClinicalTrialsSearch`: `79852cdcc0dc7695b4e430313b1574721303fb78b0dff1cd3eadcbcd66c9be1c`
- `VSDReviewedClinicalTrialDetails`: `3b4dd7f5717bd0f2dcf1d50c85a09a71c1b00ba44c7bccbfcf339bf0a53dbfa6`
- Search payload: `dbefbe106f242d10a0b52277d89cd4264b7fe52851b6f50ffbe65efcf23da6a9`
- Detail payload: `4dd3ccee9977ba69c9e8c35c179fdc25f212d39b101cc0c9e0a8e8fd7ca30c44`
- Both calls used HTTPS GET, zero redirects, bounded JSON decoding, pinned DNS, schema validation, and the ToolUniverse `run_one_function()` path.

## Interpretation Boundary

This is an API execution and record-consistency proof, not trial matching, eligibility assessment, or treatment advice.
