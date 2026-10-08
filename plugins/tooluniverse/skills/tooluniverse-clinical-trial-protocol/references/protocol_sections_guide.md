# Protocol Sections Guide

Nine sections, modeled on ICH E6(R2) Good Clinical Practice guidance and standard FDA protocol structure. For each section: what it must contain, and which real ToolUniverse tool grounds each claim.

## 1. Background & Rationale

- Disease/condition burden, unmet need, mechanism-of-action rationale for the intervention.
- Prior clinical experience with this intervention or its class.

Tools: `PubMed_search_articles` (disease burden, mechanism literature), `search_clinical_trials` / `ClinicalTrials_search_by_intervention` (prior trials of this intervention or class), `OpenFDA_get_approval_history` or `OpenFDADevice_get_classification` (regulatory history of the intervention or predicate).

## 2. Objectives & Endpoints (Primary / Secondary)

- Primary objective and its endpoint, restated from the feasibility report (Step 1).
- Secondary and exploratory endpoints, each with a precedent citation.

Tools: `get_clinical_trial_outcome_measures` and `search_clinical_trials` (endpoint precedent in similar trials), `OpenFDA_get_approval_history` (whether this endpoint has supported prior approvals in this indication).

## 3. Study Design

- Design type (randomized/single-arm, parallel/crossover, blinding), phase, arms, allocation ratio.
- Duration and visit schedule at a high level.

Tools: `ClinicalTrials_get_study` on 2-3 close precedent trials to confirm design conventions in this indication; `get_clinical_trial_status_and_dates` for typical trial duration.

## 4. Study Population & Eligibility Criteria

- Key inclusion/exclusion criteria, biomarker requirements, prior-therapy restrictions.

Tools: `get_clinical_trial_eligibility_criteria` on precedent trials (pull real criteria language rather than inventing it), `get_clinical_trial_conditions_and_interventions`.

## 5. Intervention Details

- Dose, route, schedule, duration of treatment; for devices, model/configuration and procedure details.
- Comparator/control arm details and sourcing.

Drug tools: `FDA_OrangeBook_search_drug`, `drugbank_get_pharmacology_by_drug_name_or_drugbank_id` (if already resolved from the feasibility report), `FDAGSRS_search_substances` (substance identity).
Device tools: `OpenFDADevice_get_classification`, `OpenFDADevice_search_udi`, `OpenFDADevice_search_510k` or `OpenFDADevice_search_pma` (predicate/precedent device details).

## 6. Study Assessments & Schedule of Events

- Screening, baseline, on-treatment, and follow-up assessments; imaging/lab schedule; endpoint assessment timing.

Tools: `get_clinical_trial_outcome_measures` and `ClinicalTrials_get_study` on precedent trials for realistic assessment cadence.

## 7. Statistical Analysis Plan (including Sample Size Justification)

- Primary analysis method for the endpoint type (proportion, continuous, or time-to-event).
- Sample size and power, computed with `scripts/sample_size_calculator.py` using effect-size assumptions sourced from precedent trials (Step 3 tool calls) or the feasibility report — never guessed.
- Interim analysis plan and multiplicity adjustment if applicable.

Tools: none beyond the sample-size calculator itself; the effect-size inputs to the calculator MUST be sourced from `search_clinical_trials` / `get_clinical_trial_outcome_measures` precedent data or the prior feasibility report.

## 8. Safety Monitoring & Adverse Event Reporting

- Expected adverse events based on mechanism/class, dose-limiting toxicity definition if applicable, stopping rules, safety monitoring committee.

Tools: `extract_clinical_trial_adverse_events` (precedent trial AE profiles), `FDA_get_warnings_and_cautions_by_drug_name` (label warnings, drug intervention), `OpenFDADevice_search_adverse_events` / `OpenFDADevice_search_recalls` (device intervention), `FAERS_search_reports_by_drug_and_reaction` (post-market signal context for a drug comparator or the intervention itself if previously marketed).

## 9. Ethical & Regulatory Considerations

- Regulatory pathway and submission plan (see `regulatory_pathway_notes.md`), informed consent considerations, IRB/ethics committee requirements.

Tools: drug — `OpenFDA_search_drug_approvals`, `OpenFDA_get_approval_history`, `FDA_OrangeBook_get_approval_history`; device — `OpenFDADevice_search_510k`, `OpenFDADevice_search_pma`, `OpenFDADevice_get_classification`.

---

**Evidence discipline**: every numeric or regulatory claim in the document should trace to one of the tool calls above. If a tool returns no precedent (novel endpoint, first-in-class mechanism, novel device category), say so explicitly in the section rather than filling the gap with an assumption.
