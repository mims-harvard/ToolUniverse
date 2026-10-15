# Study-Design Review Guides

Use this reference after identifying the study design. Apply only relevant modules. Reporting guidelines improve completeness but do not prove validity or compliance. Verify the current guideline version before making a formal compliance claim.

## Contents

- Randomized trials
- Observational and causal-inference studies
- Diagnostic-accuracy studies
- Prediction models and machine learning
- Systematic reviews and meta-analyses
- Qualitative research
- Animal studies
- Laboratory, organoid, omics, and imaging studies
- Economic evaluations
- Mixed or unclear designs

## Randomized Trials

Use CONSORT-style checks for completed trials and SPIRIT-style checks for protocols.

Check:

- allocation sequence, concealment, stratification, clustering, and who was masked;
- prespecified estimand, primary outcome, analysis population, and intercurrent-event handling;
- sample-size assumptions, attrition allowance, stopping rules, and interim analyses;
- participant flow, deviations, missing outcomes, harms, effect sizes, and uncertainty;
- consistency among registration, protocol, statistical analysis plan, and report.

Do not assume an intention-to-treat label guarantees correct handling of missing outcomes or intercurrent events.

## Observational and Causal-Inference Studies

Use STROBE-style reporting checks; use RECORD-style additions for routinely collected data when relevant.

Check:

- source population, sampling, eligibility, exposure, comparator, outcome, and time zero;
- confounding control, positivity, measurement error, selection, immortal-time, and reverse-causation risks;
- clustering, repeated observations, matching or weighting diagnostics, and missing data;
- target estimand, temporal ordering, sensitivity analyses, and limits on causal language;
- absolute as well as relative effects and applicability to the target population.

Cross-sectional associations generally cannot establish temporal direction or prevention.

## Diagnostic-Accuracy Studies

Use STARD-style reporting and QUADAS-2 concepts.

Check:

- intended use, target condition, setting, participant spectrum, and prespecified thresholds;
- reference-standard validity, blinding, timing, verification, and uninterpretable results;
- whether all participants received the same reference standard;
- sensitivity, specificity, predictive values, likelihood ratios, and confidence intervals;
- spectrum effects, prevalence dependence, calibration when risk is predicted, and external validation.

Flag incorporation bias, partial verification, differential verification, and data-derived thresholds.

## Prediction Models and Machine Learning

Use TRIPOD-style reporting and PROBAST concepts; apply AI-specific extensions when relevant and verified.

Check:

- intended use, target population, outcome horizon, predictors available at prediction time, and comparator model;
- patient-level splitting, temporal order, site separation, and independence of validation data;
- whether imputation, normalization, feature selection, augmentation, and tuning occur only within training data;
- events or effective sample size relative to model complexity and overfitting controls;
- discrimination with uncertainty, calibration, overall accuracy, threshold performance, and decision-curve or net-benefit analysis;
- locked-model external validation, subgroup performance, fairness, transportability, and deployment monitoring;
- executable pipeline, feature definitions, coefficients or model artifact, versions, and seeds.

Treat preprocessing before splitting and tuning on the test set as leakage. Discrimination alone does not establish clinical utility.

## Systematic Reviews and Meta-Analyses

Use PRISMA-style reporting. Select risk-of-bias instruments appropriate to included designs, such as RoB 2 for randomized trials or ROBINS-I for nonrandomized intervention studies.

Check:

- protocol registration, eligibility criteria, complete search strategy, databases, registries, grey literature, and search dates;
- independent screening, extraction, conflict resolution, and excluded-study accounting;
- effect-measure compatibility, unit-of-analysis issues, model choice, and dependence among estimates;
- heterogeneity using clinical and methodological assessment plus tau-squared and prediction intervals where useful;
- sensitivity, influence, subgroup, and meta-regression analyses without data dredging;
- small-study effects, selective reporting, risk of bias, and certainty of evidence such as GRADE when appropriate.

A random-effects model does not explain heterogeneity. Avoid interpreting I-squared in isolation.

## Qualitative Research

Use COREQ- or SRQR-style reporting according to the method.

Check:

- sampling strategy, participant context, recruitment, adequacy, and the operational basis for saturation or information power;
- interviewer identity, training, relationship to participants, positionality, and reflexivity;
- interview guide, recording, transcription, field notes, and data management;
- named analytic framework, coder roles, iterative analysis, disagreements, audit trail, and use of software;
- negative cases, triangulation, member reflection or checking when methodologically appropriate;
- grounding of themes in quotations and limits on transferability.

Do not require every trustworthiness technique mechanically; judge whether the chosen approach fits the epistemology and research question.

## Animal Studies

Use ARRIVE-style reporting and the 3Rs as relevant.

Check:

- experimental unit, litter and cage effects, sex, age, strain, genotype, housing, and husbandry;
- allocation, concealment, blinding, exclusions, humane endpoints, welfare monitoring, and adverse events;
- sample-size rationale and whether technical observations are mistaken for biological replicates;
- intervention timing, dose, route, outcome timing, and measurement reliability;
- ethics approval and replacement, reduction, and refinement considerations.

## Laboratory, Organoid, Omics, and Imaging Studies

Check:

- biological versus technical replication and the true experimental unit;
- donor, plate, batch, run, cage, field, image, and repeated-measure dependence;
- randomization across batches, blinded acquisition or analysis, and prespecified exclusion rules;
- authentication, contamination checks, reagent identifiers, calibration, detection limits, and QC thresholds;
- preprocessing, normalization, batch correction, multiplicity, pipeline versions, and leakage;
- whether claims generalize beyond the number of independent donors, specimens, or experiments.

Never inflate sample size by counting fields, cells, images, wells, or organoids as independent when treatment was assigned at a higher level.

## Economic Evaluations

Use CHEERS-style reporting.

Check perspective, time horizon, comparators, costing year, discounting, outcome valuation, model structure, parameter sources, uncertainty analysis, heterogeneity, and conflicts. Distinguish cost effectiveness from affordability and budget impact.

## Mixed or Unclear Designs

Ask for the research question, design, unit of assignment, unit of observation, outcome type, time structure, and intended inference. Until clarified, provide conditional concerns instead of prescribing a single model or checklist.
