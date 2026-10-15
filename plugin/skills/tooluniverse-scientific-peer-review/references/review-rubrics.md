# Scientific Review Rubrics

Use the shared calibration first, then select only the rubric modules relevant to the request.

## Contents

- Shared rating calibration
- Rubric selection and legacy mapping
- Novelty and significance
- Literature context
- Methodological rigor
- Data-analysis validity
- Results interpretation
- Writing and presentation
- Reproducibility
- Ethical compliance
- Experimental design
- Protocol optimization

## Shared Rating Calibration

| Rating | Meaning |
|---|---|
| 5 | Strong, transparent, and fit for purpose; only minor refinements needed |
| 4 | Sound overall, with limited issues unlikely to change the main conclusion |
| 3 | Usable but materially incomplete; revisions could affect interpretation |
| 2 | Major weaknesses substantially reduce confidence or reproducibility |
| 1 | Fundamentally inadequate for the stated claim or purpose |
| Not assessable | The supplied material does not contain the evidence needed to judge |

Use ratings only when requested. Do not average `Not assessable` entries. If an overall score is requested, report the included criteria, calculation, weighting, and number assessed; prefer whole or half points over spurious decimals.

## Rubric Selection and Legacy Mapping

| Review need | Apply this module | Legacy AgenticTool replaced in host mode |
|---|---|---|
| Originality and contribution | Novelty and significance | `NoveltySignificanceReviewer` |
| Prior work and research gap | Literature context | `LiteratureContextReviewer` |
| Study methods | Methodological rigor | `MethodologyRigorReviewer` |
| Statistics and analysis | Data-analysis validity | `DataAnalysisValidityReviewer` |
| Results and discussion | Results interpretation | `ResultsInterpretationReviewer` |
| Language and presentation | Writing and presentation | `WritingPresentationReviewer` |
| Data, code, and materials | Reproducibility | `ReproducibilityTransparencyReviewer` |
| Human/animal ethics and disclosures | Ethical compliance | `EthicalComplianceReviewer` |
| Proposed experiment | Experimental design | `ExperimentalDesignScorer` |
| Proposed protocol | Protocol optimization | `ProtocolOptimizer` |

## Novelty and Significance

Assess:

- originality of the research question relative to the literature actually supplied or retrieved;
- contribution beyond established knowledge;
- whether the work is incremental, enabling, or potentially field-changing;
- whether significance claims are supported by the demonstrated effect and scope.

Never claim that work is globally novel without an external literature search. When no search was performed, label the result “novelty within the supplied context.”

## Literature Context

Assess:

- coverage of directly relevant and competing work;
- accuracy of summaries and attribution;
- critical synthesis rather than a paper-by-paper list;
- clarity of the unresolved gap and how the study addresses it;
- balance across supporting, conflicting, and null evidence.

Suggest specific missing topics or search concepts. Suggest exact citations only after verifying them.

## Methodological Rigor

Assess:

- alignment between research question, design, population, intervention/exposure, comparator, and outcomes;
- operational definitions and measurement validity;
- sampling, inclusion/exclusion criteria, allocation, randomization, blinding, and controls;
- procedural detail sufficient for replication;
- confounding, selection bias, information bias, batch effects, and leakage;
- sample-size or precision justification;
- deviations from protocol and handling of missing data.

Prioritize threats to identification and causal interpretation over cosmetic reporting issues.

## Data-Analysis Validity

Assess:

- whether tests or models match the outcome, design, dependence structure, and estimand;
- assumption checks and remedies;
- effect sizes, uncertainty intervals, exact p-values, and multiplicity control;
- missing-data handling, sensitivity analyses, and robustness checks;
- separation of confirmatory and exploratory analyses;
- availability of analysis code, software versions, seeds, and preprocessing decisions.

Do not recommend a statistical test without explaining why it matches the design. Do not infer that assumptions passed merely because a test was named.

## Results Interpretation

Assess:

- whether every major conclusion is supported by a reported result;
- distinction among association, prediction, mechanism, and causation;
- clinical or practical importance versus statistical significance;
- alternative explanations, negative findings, and contradictory evidence;
- generalizability and limitations;
- whether future-work claims follow from the actual uncertainty.

Flag causal verbs when the design supports only association.

## Writing and Presentation

Assess:

- clarity, concision, terminology consistency, and definition of abbreviations;
- grammar, scientific style, sentence-level ambiguity, and unsupported promotional language;
- logical order between question, method, result, and conclusion;
- whether figures and tables can be interpreted independently from their captions;
- consistency among text, tables, figures, supplements, and reported sample sizes;
- whether uncertainty and limitations remain visible after editing.

Quote only short excerpts needed to locate a problem, then propose a concrete rewrite pattern.

For writing-only requests, correct grammar and style without performing an unsolicited methods review, but also neutralize unsupported epistemic force. Do not merely polish claims such as “clearly proves,” “very unique,” “extremely safe,” or “patients benefited.” When quantitative support is absent, use an evidence-bounded pattern such as “The observed results were consistent with [specific outcome]” or retain a placeholder rather than asserting benefit, novelty, safety, or causality.

## Reproducibility

Assess:

- data accessibility, identifiers, formats, documentation, and access restrictions;
- code and environment availability, licensing, version pinning, and executable instructions;
- protocol, materials, model, and instrument detail;
- provenance of derived data and transformation steps;
- justified embargoes and a concrete access path.

Distinguish “available on request” from openly reproducible. Treat broken or unverified links as verification gaps.

## Ethical Compliance

Assess what is reported about:

- ethics-board or animal-care approval and approval identifiers;
- informed consent, assent, waiver, and vulnerable populations;
- participant or animal welfare and adverse-event monitoring;
- privacy, de-identification, retention, access control, and secondary use;
- conflicts of interest, funding, and sponsor role;
- dual-use, community, or environmental risks where applicable.

Flag missing statements without asserting noncompliance. Recommend specialist review for jurisdiction-specific requirements.

## Experimental Design

Assess:

- hypothesis clarity and falsifiability;
- independent, dependent, control, and nuisance variables;
- controls, randomization, allocation concealment, and blinding;
- sample-size rationale, expected effect, variance, and attrition;
- measurement reliability, validity, timing, and data-quality checks;
- prespecified statistical analysis and decision criteria;
- bias mitigation, ethics, resources, timeline, and contingency plans.

Finish with the two or three design changes most likely to increase inferential value.

## Protocol Optimization

Assess:

- clarity of objectives, inputs, steps, roles, and decision points;
- feasibility, dependencies, resources, and schedule;
- safety risks, failure modes, stopping rules, and contingencies;
- measurement, acceptance criteria, quality control, and audit trail;
- reproducibility and change control.

Provide a prioritized action checklist. Preserve correct protocol content rather than rewriting it wholesale unless requested.
