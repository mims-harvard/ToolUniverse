# Infectious-Disease Genomic Surveillance Growth Study

## Decision Question

Can an outbreak research workflow reuse sequence and taxonomy tools while adding one reviewed jurisdictional cluster summary without exposing individual records or accepting an unreviewed live event stream?

**Result:** Yes. Sequence and taxonomy capabilities stayed in place; one bounded aggregate cluster operation passed the full review and lifecycle path, with provider drift disabling fresh loading until explicit recovery.

## Why This Fits ToolUniverse

An incident-analysis workflow can connect public sequence resources to a narrow reviewed cluster feed while retaining sample windows, coverage, quality flags, and action provenance needed for cautious interpretation.

The study follows ToolUniverse's documented pattern of composing existing scientific resources before extending the environment. It audited 2,744 configured tools and aligned the workflow with these documented skills: infectious disease, sequence retrieval, phylogenetics.

## Existing Registry Reuse

| Workflow step | Baseline coverage | Top existing tools |
| --- | --- | --- |
| `outbreak_literature` | existing_partial | `BGPT_search_paper_evidence`, `BioGRID_get_ptms`, `BioGRID_search_by_pubmed`, `DisProt_search`, `EuropePMC_Guidelines_Search` |
| `sequences` | existing_partial | `NCBIDatasets_get_sequence_reports`, `AMPSphere_get_family`, `NCBI_get_sequence`, `NCBI_SRA_search_runs`, `proteins_api_get_epitopes` |
| `taxonomy` | existing_partial | `RCSBGraphQL_get_polymer_entity`, `ENCORI_get_RNA_RNA_interactions`, `euhealthinfo_search_diabetes_epidemiology_registry`, `NCBI_SRA_search_runs`, `VEuPathDB_search_genes_by_organism` |

Those capabilities were not regenerated. The provider-specific step `jurisdictional_cluster` was missing and was the only step routed to inert external discovery.

## Organic Demand And Candidate Review

Three independent workflow preflights produced demand `2f2b085f253e8ac9` with priority score 15. A maintainer explicitly exported one sanitized proposal; its transmission state remained `none; this file was written locally for explicit human review`.

The catalog lead and OpenAPI operation remained non-executable. The local contract supplied one exact read operation and an environment-backed header credential requirement; no credential value entered the candidate, draft, evidence, approval, publication, runtime result, or artifact.

| Review identity | SHA-256 or ID |
| --- | --- |
| Demand proposal | `d29703f28dc56c666bb7a893999dd923827bd168da5b03e099001b88a1e144c6` |
| OpenAPI candidate | `58ddddd93b798469d65aa62b64d1aea638e398f1f6c3f9900c1563e84f8fcf65` |
| Source document | `c11c1cfb2a8c0387e7df0a4842cb8cee49be4452c9b7db779c14c532484d1768` |
| Draft | `321befbd570d0390b14ca97a31c2997abafac2cf427a3237b4697e4bcddfd3d6` |
| Operation | `626c2549f38f42eeb16eadbe8af09aae2e05e99c2ec6cbbb605700989820f75d` |
| Verification | `528c9df77dba6b47dded8748c2bd5a9c893eb16857b0875ad753f35900a51a1c` |
| Approval | `4420acbbded6d96368e99539befdad43b27d4f9df2a9308b053f34b5f84b7e68` |
| Publication | `4ab48a1e4d1c9b48115d04110f6ce42c176830f56024fe7093ab5e4457879161` |

## Representative Verification And Fresh Runtime

The draft failed before transport when its credential was absent, then passed three representative records after the environment reference was configured. Publication was also refused after verification but before explicit approval. A new ToolUniverse instance could not see the tool until `load_published_tools` was called.

| Record | Key evidence retained |
| --- | --- |
| `OUT-H5N1-01` | case_count, lineages, mutation_markers, pathogen, public_health_actions, quality_flags, region, sample_window, sequence_count |
| `OUT-MPXV-01` | case_count, lineages, mutation_markers, pathogen, public_health_actions, quality_flags, region, sample_window, sequence_count |
| `OUT-NIPAH-01` | case_count, lineages, mutation_markers, pathogen, public_health_actions, quality_flags, region, sample_window, sequence_count |

The first and second records executed across credential rotation without changing operation identity. Capability resolution and workflow replanning then selected the published tool as exact coverage. The original local demand received one exact observation and was explicitly removed.

## Drift, Suspension, And Recovery

A contract endpoint move from `/v1` to `/v2` was classified as breaking. The assessment alone did not change runtime state: the tool still loaded until a maintainer explicitly suspended it. A fresh runtime then loaded nothing. A new unchanged assessment of the reviewed contract was required before explicit reactivation and the third execution.

| Lifecycle evidence | SHA-256 |
| --- | --- |
| Baseline assessment | `f9a97ff2e1c097a808f37c24eb374447d310227ff032907061ddb2d28b8fdecd` |
| Breaking assessment | `5fd74dbcf5f72d7acedadf69ad4919b991e146888c65def360ae8e50b5b41ec1` |
| Suspension event | `397eab7013fa8c8bb267b061c9267afb520996443d346271f8ff5b48210fd263` |
| Repaired assessment | `ec402e0b6484cfec7731a43b0817e38da5c64f6be0e83b68fcf02e7249f5d58c` |
| Activation event | `83e0af6eeeece1b95bf27c2de51e98f00583529af1e6e1c744138b6bac45d57f` |

## Research Decisions Enabled

- which sequence gaps require follow-up
- which lineage statements are supported only at aggregate level
- which quality flags must accompany any incident brief

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

The deterministic records contain no individual data and do not establish transmission direction, outbreak magnitude, or public-health guidance.

The provider and catalog are deterministic fixtures because the repository cannot bundle private credentials or controlled scientific data. Registry resolution, planning, demand, inspection, promotion, verification, publication, fresh loading, credential lookup, lifecycle, and audit logic all use production ToolUniverse paths.

**Audit SHA-256:** `409cf2f88a547e2573f0cc1a3ed87f724edaef12272b7d9a613004c31fb11a3c`
