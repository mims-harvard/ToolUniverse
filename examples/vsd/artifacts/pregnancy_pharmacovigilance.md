# Pregnancy Pharmacovigilance Signal Governance Study

## Decision Question

Can a drug-safety workflow reuse FAERS and FDA label tools while adding one reviewed longitudinal pregnancy-exposure signal operation without claiming that spontaneous reports prove causality?

**Result:** Yes. ToolUniverse retained its FDA coverage, isolated the missing pregnancy-signal series, verified three exposure records, and governed the added operation through credentials, explicit loading, and drift.

## Why This Fits ToolUniverse

Safety researchers can add a narrow institutional or jurisdictional signal feed to an existing FAERS workflow while preserving provenance, denominator caveats, and a reviewable shutdown path.

The study follows ToolUniverse's documented pattern of composing existing scientific resources before extending the environment. It audited 2,744 configured tools and aligned the workflow with these documented skills: pharmacovigilance, adverse event detection, chemical safety.

## Existing Registry Reuse

| Workflow step | Baseline coverage | Top existing tools |
| --- | --- | --- |
| `faers_reports` | existing_exact | `FAERS_search_adverse_event_reports`, `FAERS_search_reports_by_drug_and_indication`, `FAERS_search_reports_by_drug_and_outcome`, `FAERS_search_reports_by_drug_and_reaction`, `FAERS_search_reports_by_drug_combination` |
| `label_warnings` | existing_exact | `FDA_get_adverse_reactions_by_drug_name`, `FDA_get_drug_label`, `FDA_get_drug_label_info_by_field_value`, `FDA_get_drug_name_by_environmental_warning`, `FDA_get_drug_name_by_pregnancy_or_breastfeeding_info` |
| `safety_literature` | existing_partial | `PubTator3_GetEntityRelations`, `BioGRID_get_ptms`, `MedicalLiteratureReviewer`, `EpiGraphDB_get_literature_evidence`, `FDA_get_drug_label_info_by_field_value` |

Those capabilities were not regenerated. The provider-specific step `pregnancy_signal_series` was missing and was the only step routed to inert external discovery.

## Organic Demand And Candidate Review

Three independent workflow preflights produced demand `26bd5f1bce9232c7` with priority score 15. A maintainer explicitly exported one sanitized proposal; its transmission state remained `none; this file was written locally for explicit human review`.

The catalog lead and OpenAPI operation remained non-executable. The local contract supplied one exact read operation and an environment-backed header credential requirement; no credential value entered the candidate, draft, evidence, approval, publication, runtime result, or artifact.

| Review identity | SHA-256 or ID |
| --- | --- |
| Demand proposal | `a2a4fc66b63bd7d6374f3fe99d5532cfe35fa544be435ac23bf0e62cf5661082` |
| OpenAPI candidate | `ef3bf8743b99121ee181c129dc4c6f41bf3610824e0e76ba760965b47a9ea7e6` |
| Source document | `de7770a00f7c9f697de7586b50f06931716338b56dd41a2233bae338bb8f742a` |
| Draft | `6031db7969587d875a0f999e5ddb6f96a2424de75a9ebf3f9fd061ae41370d8b` |
| Operation | `c095928f344e236f546d4fd462e776033a9b84e05b65ad457a5bb531ecfb06ad` |
| Verification | `370e5011ff85e0951673f92499e2e549b3eaf19e0a04a46922708eea2da48b96` |
| Approval | `0a7283f265add32be9d3e2aa039f9cb2f9ed22acf1b0a4e9140d9375d596a04a` |
| Publication | `23f087262595181336c827c6d93edf1609094502d30900bc092f944da048d21d` |

## Representative Verification And Fresh Runtime

The draft failed before transport when its credential was absent, then passed three representative records after the environment reference was configured. Publication was also refused after verification but before explicit approval. A new ToolUniverse instance could not see the tool until `load_published_tools` was called.

| Record | Key evidence retained |
| --- | --- |
| `EXP-ISOTRETINOIN` | comparator_cases, confidence_interval, evidence_limitations, exposed_cases, ingredient, reporting_odds_ratio, reporting_window, seriousness_categories, signal_status |
| `EXP-SEMAGLUTIDE` | comparator_cases, confidence_interval, evidence_limitations, exposed_cases, ingredient, reporting_odds_ratio, reporting_window, seriousness_categories, signal_status |
| `EXP-VALPROATE` | comparator_cases, confidence_interval, evidence_limitations, exposed_cases, ingredient, reporting_odds_ratio, reporting_window, seriousness_categories, signal_status |

The first and second records executed across credential rotation without changing operation identity. Capability resolution and workflow replanning then selected the published tool as exact coverage. The original local demand received one exact observation and was explicitly removed.

## Drift, Suspension, And Recovery

A contract endpoint move from `/v1` to `/v2` was classified as breaking. The assessment alone did not change runtime state: the tool still loaded until a maintainer explicitly suspended it. A fresh runtime then loaded nothing. A new unchanged assessment of the reviewed contract was required before explicit reactivation and the third execution.

| Lifecycle evidence | SHA-256 |
| --- | --- |
| Baseline assessment | `7bdb19c73a6e7a460464163e59aeb219002777ee11b1657b31926f0985d65dec` |
| Breaking assessment | `ccbb217123d8888e5fc4ed5de011a571928229847952841ded91d366452b2262` |
| Suspension event | `f13286f930812ea6fb21894cd913729214a5a74d2d772999d8f219c10191ceab` |
| Repaired assessment | `bf5f63e1fb5dde67bef8f316b5c4c549e72c5313b653d6dd21f568329b522f21` |
| Activation event | `4282318fded8c959baa314dcb1b6fbf28360017b2b47b4aa19f66fb48bf0cbcd` |

## Research Decisions Enabled

- which signals need formal epidemiologic follow-up
- which label sections should be compared
- which limitations prevent causal interpretation

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

Reporting odds ratios in these deterministic fixtures are not incidence rates, causal estimates, regulatory findings, or prescribing advice.

The provider and catalog are deterministic fixtures because the repository cannot bundle private credentials or controlled scientific data. Registry resolution, planning, demand, inspection, promotion, verification, publication, fresh loading, credential lookup, lifecycle, and audit logic all use production ToolUniverse paths.

**Audit SHA-256:** `3f64603603eff7024d6756e42cbfbd985a62951f956a8e56fdf2699492ce9cfe`
