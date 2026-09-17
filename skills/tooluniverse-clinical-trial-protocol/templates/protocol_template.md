# Clinical Trial Protocol: [INTERVENTION NAME]

**Intervention type**: [Drug / Biologic / Device]
**Indication**: [INDICATION]
**Phase**: [PHASE]
**Protocol version / date**: [VERSION] — [DATE]
**Derived from feasibility assessment**: [link/reference to the `tooluniverse-clinical-trial-design` report used, or "run fresh" if none existed]

---

## 1. Background & Rationale

[Disease burden and unmet need, with citation. Mechanism-of-action rationale. Prior clinical experience with this intervention or its class, with precedent trial citations.]

## 2. Objectives & Endpoints

**Primary objective**: [ ]
**Primary endpoint**: [ ] — precedent: [trial/NCT ID or approval citation]

**Secondary objectives / endpoints**:
- [ ]
- [ ]

**Exploratory endpoints** (if any): [ ]

## 3. Study Design

- **Design**: [randomized / single-arm], [parallel / crossover], [open-label / blinded]
- **Arms and allocation ratio**: [ ]
- **Duration**: [screening] + [treatment] + [follow-up]
- **Precedent trials informing this design**: [NCT IDs]

## 4. Study Population & Eligibility Criteria

**Key inclusion criteria**:
- [ ]

**Key exclusion criteria**:
- [ ]

**Biomarker / companion diagnostic requirement** (if any): [ ]

## 5. Intervention Details

**Investigational arm**: [dose / route / schedule / duration, or device model / configuration / procedure]
**Comparator arm**: [placebo / active control / historical control — name, dose, sourcing]

## 6. Study Assessments & Schedule of Events

| Visit | Timepoint | Assessments |
|-------|-----------|-------------|
| Screening | [ ] | [ ] |
| Baseline | [ ] | [ ] |
| On-treatment | [ ] | [ ] |
| End of treatment | [ ] | [ ] |
| Follow-up | [ ] | [ ] |

## 7. Statistical Analysis Plan

**Primary analysis method**: [ ] (e.g. Cox proportional hazards, two-sample t-test, chi-square/logistic)

**Sample size justification** (from `scripts/sample_size_calculator.py`):

```
[paste the calculator's exact output here, including the formula line and
the effect-size assumptions — with a one-line citation of where those
assumptions came from, e.g. "effect size from NCT0XXXXXXX (Phase 2, n=XXX)"]
```

**Interim analysis / multiplicity plan** (if applicable): [ ]

## 8. Safety Monitoring & Adverse Event Reporting

**Expected adverse events** (mechanism/class-based, with precedent AE rates): [ ]
**Dose-limiting toxicity definition** (if applicable): [ ]
**Stopping rules**: [ ]
**Safety oversight**: [DSMB / medical monitor / other]

## 9. Ethical & Regulatory Considerations

**Regulatory pathway**: [IND->NDA(505(b)(1)/(2))/BLA, or 510(k)/De Novo/PMA] — rationale: [ ]
**Expedited program eligibility** (if identified in precedent search): [ ]
**IRB/ethics committee**: [ ]
**Informed consent considerations**: [ ]

---

*Generated with `tooluniverse-clinical-trial-protocol`. All precedent citations, regulatory statuses, and the sample-size calculation trace to specific tool calls listed in `references/protocol_sections_guide.md` — replace every remaining `[ ]` before this document is considered complete; do not submit with unresolved placeholders.*
