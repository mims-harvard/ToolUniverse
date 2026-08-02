# Precision Oncology Molecular Evidence Growth Study

## Decision Question

Can a molecular tumor-board workflow reuse ToolUniverse's variant and trial resources while safely adding one institution-reviewed evidence operation for therapy, resistance, and evidence-tier context?

**Result:** Yes. Existing variant and trial capabilities remained reusable, while one provider-specific evidence gap moved through private demand, inert discovery, authenticated OpenAPI review, three-case verification, publication, fresh-runtime use, credential rotation, and drift recovery.

## Why This Fits ToolUniverse

A research agent can assemble a reproducible tumor-board evidence packet without turning a hospital endpoint into an arbitrary proxy or treating fixture evidence as a treatment recommendation.

The study follows ToolUniverse's documented pattern of composing existing scientific resources before extending the environment. It audited 2,744 configured tools and aligned the workflow with these documented skills: precision oncology, cancer variant interpretation, clinical trial matching.

## Existing Registry Reuse

| Workflow step | Baseline coverage | Top existing tools |
| --- | --- | --- |
| `drug_label` | existing_exact | `OpenFDA_search_drug_labels`, `FDAGSRS_search_substances`, `OpenFDA_search_animalvet_adverse_events`, `OpenFDA_search_drug_enforcement`, `OpenFDA_search_drug_events` |
| `trial_search` | existing_partial | `ClinicalTrials_search_by_intervention`, `ClinicalTrials_search_by_sponsor`, `ClinicalTrials_search_studies`, `CTIS_search_trials_filtered`, `search_clinical_trials` |
| `variant_interpretation` | existing_partial | `civic_search_evidence_items`, `EBIProteins_get_variation`, `ClinVar_search_variants`, `civic_get_variant`, `ClinVar_get_clinical_significance` |

Those capabilities were not regenerated. The provider-specific step `reviewed_molecular_evidence` was missing and was the only step routed to inert external discovery.

## Organic Demand And Candidate Review

Three independent workflow preflights produced demand `4d73c37499d94921` with priority score 15. A maintainer explicitly exported one sanitized proposal; its transmission state remained `none; this file was written locally for explicit human review`.

The catalog lead and OpenAPI operation remained non-executable. The local contract supplied one exact read operation and an environment-backed header credential requirement; no credential value entered the candidate, draft, evidence, approval, publication, runtime result, or artifact.

| Review identity | SHA-256 or ID |
| --- | --- |
| Demand proposal | `1958f70cecb2262843c2e02c3818b199d6238734e7218f64473b994dee31a0a5` |
| OpenAPI candidate | `69ab594886c8c2080ec4270ae705a1ca912da21f962af08dd53ae2c1f9485260` |
| Source document | `c6e428911957aa56d65b9b9c145255646d86357896e5de91edfe68169e43db4b` |
| Draft | `0e14041ce102cb68eb6fb301a76b6b22f66172243ac6a0949b0effaaf9211f19` |
| Operation | `3693e681b78e3761ba8777ef2f0e07da3ea38c0430c2bed46f80e9bcc68c2642` |
| Verification | `86a17869fc8f893230f60fb07efd028c5d314655a0d4451064523e65acd8f536` |
| Approval | `d7484a31b1c177a6306382184db09612fb190e4f21edb7e4961031026196bd7a` |
| Publication | `09fd738eb14e79f0bcbfeca3ee73c2b2350c942baaa5969a035981b8542ee762` |

## Representative Verification And Fresh Runtime

The draft failed before transport when its credential was absent, then passed three representative records after the environment reference was configured. Publication was also refused after verification but before explicit approval. A new ToolUniverse instance could not see the tool until `load_published_tools` was called.

| Record | Key evidence retained |
| --- | --- |
| `ONC-CRC-KRAS` | approved_therapies, biomarkers, cancer_type, evidence_limitations, resistance_signals, trial_ids |
| `ONC-MEL-BRAF` | approved_therapies, biomarkers, cancer_type, evidence_limitations, resistance_signals, trial_ids |
| `ONC-NSCLC-EGFR` | approved_therapies, biomarkers, cancer_type, evidence_limitations, resistance_signals, trial_ids |

The first and second records executed across credential rotation without changing operation identity. Capability resolution and workflow replanning then selected the published tool as exact coverage. The original local demand received one exact observation and was explicitly removed.

## Drift, Suspension, And Recovery

A contract endpoint move from `/v1` to `/v2` was classified as breaking. The assessment alone did not change runtime state: the tool still loaded until a maintainer explicitly suspended it. A fresh runtime then loaded nothing. A new unchanged assessment of the reviewed contract was required before explicit reactivation and the third execution.

| Lifecycle evidence | SHA-256 |
| --- | --- |
| Baseline assessment | `6cfb622095e720d0aa4038e841e251ab49216ce2b54f92c99a4cbb4c216517ed` |
| Breaking assessment | `027b4c4c63c123b78454ca5352ec10c4ed29ae225303a7b248c3b3dae6ab93d2` |
| Suspension event | `9c54c5083c2a3445c3bbdd87bc86dbf62ea55c82d24be2cb179e2f597d488490` |
| Repaired assessment | `d7d03ec7f7dd5b3699cbe02749a14aef270940212e4f9f89ebc0de580f5bfdbb` |
| Activation event | `28eca6228e6c73edc477a4d1f7f715c8547be396182f4f5a6526e99d828132f6` |

## Research Decisions Enabled

- which evidence needs specialist confirmation
- which resistance mechanisms require literature review
- which trial identifiers warrant eligibility checking

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `assessment_does_not_auto_suspend` | PASS |
| `breaking_drift_is_detected` | PASS |
| `candidate_is_inert_and_authenticated` | PASS |
| `credential_reference_excludes_secret_value` | PASS |
| `credential_rotation_preserves_operation_identity` | PASS |
| `demand_closure_is_explicit` | PASS |
| `discovery_candidate_is_inert` | PASS |
| `existing_registry_capabilities_are_reused` | PASS |
| `fresh_runtime_executes_all_three_records` | PASS |
| `initial_provider_specific_capability_is_missing` | PASS |
| `missing_credential_fails_before_transport` | PASS |
| `only_gap_routes_to_external_discovery` | PASS |
| `private_demand_is_repeated_ranked_and_sanitized` | PASS |
| `provider_transport_is_exact_and_bounded` | PASS |
| `publication_is_absent_until_explicit_load` | PASS |
| `published_capability_resolves_exactly` | PASS |
| `repaired_contract_requires_explicit_reactivation` | PASS |
| `replanning_reuses_published_tool` | PASS |
| `secret_values_are_absent_from_artifacts` | PASS |
| `suspension_prevents_fresh_loading` | PASS |
| `three_representative_verification_cases_pass` | PASS |
| `unapproved_draft_cannot_publish` | PASS |

## Interpretation Boundary

The records demonstrate software governance only. They are not patient data, clinical recommendations, evidence grading, or proof of efficacy.

The provider and catalog are deterministic fixtures because the repository cannot bundle private credentials or controlled scientific data. Registry resolution, planning, demand, inspection, promotion, verification, publication, fresh loading, credential lookup, lifecycle, and audit logic all use production ToolUniverse paths.

**Audit SHA-256:** `670208057574c36024cede267121d830d1a6be68dc70e9082ad9eaeab7ab0551`
