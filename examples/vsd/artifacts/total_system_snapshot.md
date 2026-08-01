# ALS Demand-To-Reviewed-Tool Total VSD System Study

## Decision Question

Can repeated unmet ALS workflow demand safely become a reviewed, credentialed, lifecycle-managed ToolUniverse capability?

**Result:** Yes. One missing protected registry step was privately ranked and explicitly proposed, reviewed through source and OpenAPI boundaries, verified on three diseases, published, reused by planning and Finder, executed, explicitly closed in the demand ledger, suspended on drift, and safely reactivated after contract repair.

## Research Case

An ALS evidence workflow needed one protected registry operation that returns a consolidated record of genes, phenotypes, and clinical-trial identifiers. The initial registry had no operation at the reviewed provider endpoint, so planning isolated that step as the only tool gap while keeping the final synthesis agent-native.

The protected rare-disease provider and fixed catalog response are deterministic because the repository cannot bundle a live credential. All registry, planning, demand, admin, inspection, promotion, runtime, credential, lifecycle, and audit paths use production code.

## Organic Demand Loop

Three independent preflights produced demand `7fd44af18bd83619` with priority score 15. An administrator explicitly exported one sanitized proposal; no transmission occurred. After publication, the same demand received one exact observation, reducing its historical unmet rate to 0.75. The local reviewer then explicitly removed the resolved aggregate; the final demand count is zero.

| Demand boundary | SHA-256 |
| --- | --- |
| Sanitized proposal | `9fd9fc666c7e2745dcceecbbceeeb089418433521925237c751c864af0f22455` |
| Closed local ledger | `4536719c6cbeebfbabe82a9d3c8e83128470701aa10c0cb115f70ba6735738a0` |

## Review And Promotion

The administrator probed, listed, queried, and removed the provider through the mutable source CLI. A fixed public catalog search returned inert metadata candidates. The selected provider contract instead entered through local OpenAPI inspection, where its header API-key requirement was derived without a credential value.

| Boundary | SHA-256 |
| --- | --- |
| Draft | `090caaafe70bf10acd0c452b63039b1b14eb9e6dd390aa8b2cce07f879913e37` |
| Operation | `0f6c114c1d00fb3254f8934322cdb011e4c05d319ae1b89ebb8536ce1cd6c072` |
| Verification | `443a778d8fcaa14ce983f642409724318c4dc491b7417fa5074b01ece4c9bcfc` |
| Approval | `65049f384a082eb70c1315ba873a372ecee40c52cbe3e3a25356a864ff39621d` |
| Publication | `7c61b882193f8222ffe3602fb76de9f67ed3c952c1cc431e652c6e6f9fd35c0d` |

ALS, Duchenne muscular dystrophy, and spinal muscular atrophy records all passed required-field, nested-path, and exact-identifier checks before approval.

## Registry Growth And Use

The published tool was absent until explicit loading. The expanded registry classified the formerly missing capability as exact and selected `VSDProtectedRareDiseaseEvidenceById`. Workflow replanning removed the external-discovery handoff, and Tool Finder reported the same expanded registry digest.

The fresh runtime returned `RD-ALS` and `RD-DMD` across credential rotation without changing operation identity.

## Drift And Recovery

A declared provider move from `/v1` to `/v2` was classified as breaking and recommended suspension. The explicit suspension kept the publication out of a fresh runtime. A later unchanged assessment of the reviewed `/v1` contract permitted explicit activation, after which `RD-SMA` executed successfully.

| Lifecycle boundary | SHA-256 |
| --- | --- |
| Initial unchanged assessment | `dde26749f82cdb57f8fd4e33783345f8699f3d9bee1ea457cdd604be6d29b56c` |
| Breaking assessment | `46572bc6e59898a2a6d9bb30fdbe072d3ba4d658776e562413e251b5da7260a7` |
| Suspension event | `b4d7917c74ab9780121acc87f3a10be05306d91ea2454df06a4f5f45ed0ad817` |
| Repaired assessment | `7f67c0eccacd76517ab16e0a87898e24b2f0cf38248edd527312c0062f9c7371` |
| Activation event | `119a8be43a385e95501d02d630be9a5a3748d1d3af6acff0142a9fe3c4519f6a` |

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `admin_source_lifecycle_is_complete_and_restored` | PASS |
| `administrative_mutations_are_not_agent_facing` | PASS |
| `api_catalog_candidate_is_inert` | PASS |
| `breaking_drift_recommends_suspension` | PASS |
| `credential_reference_is_persisted_without_value` | PASS |
| `credential_rotation_preserves_operation_identity` | PASS |
| `demand_closure_is_explicit_and_hash_bound` | PASS |
| `demand_export_is_sanitized_local_and_hash_bound` | PASS |
| `exact_observation_updates_original_demand` | PASS |
| `final_reactivated_tool_executes` | PASS |
| `finder_and_replanner_share_expanded_registry` | PASS |
| `initial_capability_is_missing` | PASS |
| `initial_workflow_routes_only_real_gap` | PASS |
| `lifecycle_anchor_and_events_are_consistent` | PASS |
| `openapi_candidate_is_authenticated_inert_and_promotable` | PASS |
| `post_publication_capability_is_exact` | PASS |
| `provider_transport_uses_only_reviewed_header` | PASS |
| `repaired_contract_supports_safe_activation` | PASS |
| `repeated_private_demand_ranks_first` | PASS |
| `replanned_workflow_reuses_published_tool` | PASS |
| `secret_values_are_absent_from_artifacts_and_results` | PASS |
| `source_and_credential_environment_is_restored` | PASS |
| `suspension_prevents_fresh_loading` | PASS |
| `three_protected_verification_cases_pass` | PASS |
| `tool_is_absent_until_explicit_publication_load` | PASS |
| `workflow_and_demand_inputs_remain_private` | PASS |

## Boundaries

Raw workflow descriptions and event IDs remain absent from the private ledger and proposal. Credential values remain absent from persisted artifacts and results. Candidates remain inert, assessments never change state automatically, and source, demand, promotion, and lifecycle mutations remain administrator-controlled.

Docker provisioning remains the independent administrator-only phase in [#420](https://github.com/mims-harvard/ToolUniverse/pull/420), as required by the original security review. It is not part of the agent-callable VSD workflow tested here.

**Case audit SHA-256:** `6290c8a27385b1ea8834111e525f287805be6d2d6e2e704cfb8e75ea37e506cc`
