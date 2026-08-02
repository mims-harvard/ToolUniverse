# Multi-Omics Drug-Repurposing Evidence Growth Study

## Decision Question

Can a systems-biology workflow reuse target, pathway, and compound tools while adding one reviewed cross-study response signature and keeping local model provisioning outside the agent control plane?

**Result:** Yes. Existing target and pathway resources remained available, the cross-study signature followed the full demand-to-lifecycle path, and the independent Docker evidence remained administrator-only.

## Why This Fits ToolUniverse

A repurposing workflow can add a harmonized institutional signature to ToolUniverse without hiding cohort count, replication status, or modality coverage, then pass a bounded evidence packet to separately provisioned local inference infrastructure.

The study follows ToolUniverse's documented pattern of composing existing scientific resources before extending the environment. It audited 2,744 configured tools and aligned the workflow with these documented skills: multi-omics integration, drug repurposing, drug target validation.

## Existing Registry Reuse

| Workflow step | Baseline coverage | Top existing tools |
| --- | --- | --- |
| `compound_search` | existing_partial | `AntibodyRegistry_search`, `ChEMBL_get_assay_activities`, `ChEMBL_get_target`, `ChEMBL_get_target_activities`, `ChEMBL_search_protein_classification` |
| `pathway_network` | existing_partial | `STRING_get_network`, `humanbase_ppi_analysis`, `NDEx_search_networks`, `OmniPath_get_signaling_interactions`, `STRING_ppi_enrichment` |
| `target_association` | existing_partial | `europepmc_disease_target_score`, `genomics_england_disease_target_score`, `OpenTargets_target_disease_evidence`, `reactome_disease_target_score`, `cancer_biomarkers_disease_target_score` |

Those capabilities were not regenerated. The provider-specific step `cross_study_signature` was missing and was the only step routed to inert external discovery.

## Organic Demand And Candidate Review

Three independent workflow preflights produced demand `3228432d8b1fdbf6` with priority score 15. A maintainer explicitly exported one sanitized proposal; its transmission state remained `none; this file was written locally for explicit human review`.

The catalog lead and OpenAPI operation remained non-executable. The local contract supplied one exact read operation and an environment-backed header credential requirement; no credential value entered the candidate, draft, evidence, approval, publication, runtime result, or artifact.

| Review identity | SHA-256 or ID |
| --- | --- |
| Demand proposal | `528a209eab5d553445c3e432dfcfea3f4f4da3c6e74bdc35ba5660718a1ceb51` |
| OpenAPI candidate | `5b344a675b12666d801a14a16537ba3e26e2f04b81bd09113fe7197b96693c06` |
| Source document | `866bcc021b32dca301143bd3331378112a4ec788ac7b1f496b9b8bb3d0ceef97` |
| Draft | `1896c7b0ff64718c7f578ffd0c2f54257c10fbbc48b709c08c528d23c69becec` |
| Operation | `317e0375110cc9c99840de79826a5b66580abecfd3166771f00b677e8c11295a` |
| Verification | `a1293373d1ecc0d9024a2e851668928e3a9a99f69ae5da09458fd57b28223e98` |
| Approval | `e0436b97823a45b4ded86351d45c65dd81a2b0683b219ef3be2b0a768da42641` |
| Publication | `2c962b7494009a1d426b69c30c8a6d3acc1ff2d93dfebdd34e2e83f8b4a538ff` |

## Representative Verification And Fresh Runtime

The draft failed before transport when its credential was absent, then passed three representative records after the environment reference was configured. Publication was also refused after verification but before explicit approval. A new ToolUniverse instance could not see the tool until `load_published_tools` was called.

| Record | Key evidence retained |
| --- | --- |
| `MO-AD-TREM2` | candidate_compounds, cell_types, cohort_count, disease, effect_directions, genes, metabolites, pathways, perturbation, proteins, replication_status |
| `MO-CRC-KRAS` | candidate_compounds, cell_types, cohort_count, disease, effect_directions, genes, metabolites, pathways, perturbation, proteins, replication_status |
| `MO-RA-TNFA` | candidate_compounds, cell_types, cohort_count, disease, effect_directions, genes, metabolites, pathways, perturbation, proteins, replication_status |

The first and second records executed across credential rotation without changing operation identity. Capability resolution and workflow replanning then selected the published tool as exact coverage. The original local demand received one exact observation and was explicitly removed.

## Drift, Suspension, And Recovery

A contract endpoint move from `/v1` to `/v2` was classified as breaking. The assessment alone did not change runtime state: the tool still loaded until a maintainer explicitly suspended it. A fresh runtime then loaded nothing. A new unchanged assessment of the reviewed contract was required before explicit reactivation and the third execution.

| Lifecycle evidence | SHA-256 |
| --- | --- |
| Baseline assessment | `834fb52d819a9e284fa46a3484073ae21c7143052c77bf7755ad82ac65dff54b` |
| Breaking assessment | `f385ea2cf6e91b05263f318b929a04f386e351368ca796e3fa9a5ce7a5e83711` |
| Suspension event | `e6efe4877d9872a134b5915c0efa14352c85cac0844140231362183002c7df7d` |
| Repaired assessment | `2f8fa60081e70d3abc5587a2c2f0b3645aecaddc5134398dec2a01a01c13ee7a` |
| Activation event | `3f2b18236b1cb17129bae82c48ad40ec9ec53d1fef44452eece86a09b3b184d3` |

## Research Decisions Enabled

- which response directions replicate across cohorts
- which modalities or cell types remain missing
- which compound classes warrant independent target and safety review

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

The fixture does not validate differential-expression statistics, causal targets, compound efficacy, or local-model scientific reasoning.

The provider and catalog are deterministic fixtures because the repository cannot bundle private credentials or controlled scientific data. Registry resolution, planning, demand, inspection, promotion, verification, publication, fresh loading, credential lookup, lifecycle, and audit logic all use production ToolUniverse paths.

**Audit SHA-256:** `484f1ff21282f983e4a55731f5cc909b3a08e2bc6ec727d3516049ddb0810b64`
