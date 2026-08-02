# Rare-Disease Natural-History Cohort Growth Study

## Decision Question

Can a rare-disease workflow reuse HPO, Monarch, and trial tools while adding one reviewed longitudinal cohort trajectory needed for endpoint and feasibility research?

**Result:** Yes. Existing phenotype and trial resources were preserved, and the missing cohort trajectory became a narrow, verified, lifecycle-managed tool rather than a generic registry proxy.

## Why This Fits ToolUniverse

Researchers can compare harmonized cohort trajectories across ALS, DMD, and SMA while retaining cohort definitions, attrition, and readiness flags needed to judge whether downstream comparisons are defensible.

The study follows ToolUniverse's documented pattern of composing existing scientific resources before extending the environment. It audited 2,744 configured tools and aligned the workflow with these documented skills: rare disease diagnosis, clinical trial design, disease research.

## Existing Registry Reuse

| Workflow step | Baseline coverage | Top existing tools |
| --- | --- | --- |
| `disease_genes` | existing_partial | `Alliance_get_disease_genes`, `DisGeNET_get_disease_genes`, `DisGeNET_search_disease`, `ensembl_vep_region`, `EnsemblPheno_get_by_term` |
| `phenotype_annotations` | existing_partial | `HPO_get_disease_annotations`, `Mondo_get_disease_phenotypes`, `MyDisease_get_disease`, `Orphanet_get_phenotypes`, `Alliance_get_disease_genes` |
| `trial_landscape` | existing_partial | `ClinicalTrials_get_field_values`, `ClinicalTrials_search_by_intervention`, `ClinicalTrials_search_by_sponsor`, `ClinicalTrials_search_studies`, `ImmPort_search_studies` |

Those capabilities were not regenerated. The provider-specific step `longitudinal_trajectory` was missing and was the only step routed to inert external discovery.

## Organic Demand And Candidate Review

Three independent workflow preflights produced demand `312bd5b3dda526ca` with priority score 15. A maintainer explicitly exported one sanitized proposal; its transmission state remained `none; this file was written locally for explicit human review`.

The catalog lead and OpenAPI operation remained non-executable. The local contract supplied one exact read operation and an environment-backed header credential requirement; no credential value entered the candidate, draft, evidence, approval, publication, runtime result, or artifact.

| Review identity | SHA-256 or ID |
| --- | --- |
| Demand proposal | `fabad798410d0b63b80a99ea3bdeb712b1037723e101244cce3de530be7709fb` |
| OpenAPI candidate | `a3f86282c44cc8c947824118cd06e3ab4919ea9103d752ebd54176f36b093de4` |
| Source document | `761941cdeea7ab5ff87e12e48ecb8ca20d976ac2ed950cea1b154185f5af2311` |
| Draft | `e767cf4d1507675528404e5c2881e4a54556729f3bce503ed562566815570360` |
| Operation | `f29563af439b54bbe2998fb5a695cc932c8917104828e303bcbbaee8341ff5ca` |
| Verification | `9496581825e1d96b4f45be6423f7445def5d34682ee6292f471e3575760f5eb0` |
| Approval | `2c5b65a6b853e91995351adb9c6f6f29b2bd4c32180dc98a87357f8753f9ab8a` |
| Publication | `3a495b155f01a714145f684895c2e0b9d816b0bcb6bd856d802fae3689346849` |

## Representative Verification And Fresh Runtime

The draft failed before transport when its credential was absent, then passed three representative records after the environment reference was configured. Publication was also refused after verification but before explicit approval. A new ToolUniverse instance could not see the tool until `load_published_tools` was called.

| Record | Key evidence retained |
| --- | --- |
| `NH-ALS` | attrition_percent, disease, genotypes, motor_score_medians, phenotype_terms, timepoints_months, trial_readiness_flags |
| `NH-DMD` | attrition_percent, disease, genotypes, motor_score_medians, phenotype_terms, timepoints_months, trial_readiness_flags |
| `NH-SMA` | attrition_percent, disease, genotypes, motor_score_medians, phenotype_terms, timepoints_months, trial_readiness_flags |

The first and second records executed across credential rotation without changing operation identity. Capability resolution and workflow replanning then selected the published tool as exact coverage. The original local demand received one exact observation and was explicitly removed.

## Drift, Suspension, And Recovery

A contract endpoint move from `/v1` to `/v2` was classified as breaking. The assessment alone did not change runtime state: the tool still loaded until a maintainer explicitly suspended it. A fresh runtime then loaded nothing. A new unchanged assessment of the reviewed contract was required before explicit reactivation and the third execution.

| Lifecycle evidence | SHA-256 |
| --- | --- |
| Baseline assessment | `a823c6ba21c45eabf6935a8924da490f2325f002130c3958e46e19a24c18a783` |
| Breaking assessment | `9c13df5d4055660b8edec5ee3ea1951cab80445a6d387c14aebee70bb666b481` |
| Suspension event | `fb3e9f3ac32bb7fe4a76038d0e700fa256b7fdf81dc49845d00539f09fff7290` |
| Repaired assessment | `cdb46da487698fae2272cca22e0712a3d5958444052e74b6f980892dd97db025` |
| Activation event | `b89eea24f174b651557b3dd2fef94fea718a1abca2ba00abf14b94bd8b6e2d38` |

## Research Decisions Enabled

- whether timepoints and outcomes can be harmonized
- which genotype strata are underrepresented
- which attrition and treatment-era caveats affect feasibility

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

The fixture contains aggregate cohort summaries only. It cannot diagnose a person, estimate individual prognosis, or validate a clinical endpoint.

The provider and catalog are deterministic fixtures because the repository cannot bundle private credentials or controlled scientific data. Registry resolution, planning, demand, inspection, promotion, verification, publication, fresh loading, credential lookup, lifecycle, and audit logic all use production ToolUniverse paths.

**Audit SHA-256:** `56c48e3e12025bedae6c85a9345b5ee9bcc0bec5b44934aebf7cf6335bc340e0`
