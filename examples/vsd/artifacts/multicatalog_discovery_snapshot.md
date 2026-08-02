# Multi-Catalog Rare-Disease Capability Growth Study

## Decision Question

Can repeated demand for genotype-stratified rare-disease progression and specialist-access evidence become a narrow, proven ToolUniverse tool?

**Result:** Yes. Five verified catalogs yielded five relevant inert candidates; duplicate US listings converged on one endpoint, an administrator reviewed its contract, three disease cohorts passed verification, and the published tool closed the workflow gap.

## Why This Case Matters

A comparative ALS, Duchenne muscular dystrophy, and spinal muscular atrophy workflow needed longitudinal progression, genotype, clinical-outcome, and specialist-access measures from one machine-readable cohort operation. The existing registry could not satisfy that operation, so planning produced a specific discovery handoff instead of pretending a related tool was enough.

Deterministic catalog and cohort responses replace network transport. Agent invocation, provider dispatch, normalization, ranking, deduplication, registry comparison, demand, planning, OpenAPI inspection, promotion, verification, publication, loading, execution, and provenance use production code.

## Repeated Demand

Three independent preflights recorded the same missing capability as `f8b08737f5a438f5`. The reviewed local proposal is bound by `49785a274d6bc170f6317b8160fb975f39503b0abc76f30295ea639658868e40`; exporting it did not submit or approve a tool.

## Five-Catalog Search

The agent-facing discovery tool searched all five providers and inspected 10 catalog records. Format, URL, and relevance filters retained 5 inert candidates. Two duplicate records were collapsed by exact endpoint/specification identity.

| Provider | Catalog records | Candidates | Status |
| --- | ---: | ---: | --- |
| `socrata` | 2 | 1 | success |
| `datagov` | 2 | 3 | success |
| `data_europa` | 2 | 1 | success |
| `ckan_data_gov_uk` | 2 | 1 | success |
| `apis_guru` | 2 | 1 | success |

| Candidate | Catalog evidence | Format | Matched terms | Score |
| --- | --- | --- | ---: | ---: |
| Rare Disease Registry API | apis_guru | `openapi/json` | 5 | 0.7125 |
| Rare Disease Longitudinal Cohort | datagov, datagov, socrata | `soda/json` | 6 | 0.7017 |
| County care access CSV | datagov | `rest/csv` | 3 | 0.5142 |
| Specialist services JSON | ckan_data_gov_uk | `rest/json` | 2 | 0.4750 |
| Outcome definitions XML | data_europa | `rest/xml` | 2 | 0.4250 |

The APIs.guru result is an OpenAPI lead; the government-catalog results are endpoint leads. Neither form becomes executable. Catalog provenance is evidence for review, not approval or scientific endorsement.

## Reviewed Handoff

Data.gov and Socrata independently pointed to `https://data.example.gov/resource/abcd-1234.json`. An administrator obtained and inspected the provider contract, selected `getLongitudinalCohort`, and confirmed that the contract endpoint matched the discovered identity. Publication was rejected before verification and approval.

| Promotion boundary | SHA-256 |
| --- | --- |
| Catalog candidate | `b732a65feecf080e` |
| OpenAPI candidate | `6760cbb7c25b2945720e28b3fd402c25485f83297b096ac41408c3a8495f12e0` |
| Draft | `eef3cf4ab55cc529429d98002e1d92dd73d89062245f55ce641a85384ac52447` |
| Verification | `40c8be2cd848a3be5cbef977d9301668cf52bdc2f4bdbc869b432315c70cf4a5` |
| Approval | `5d5be8acdb8baa96f0df4dc38a6e059f1970366e3346f7f8e6557d8f44a78591` |
| Publication | `9f2ddc82d87491ef5cafca59b7fbad86dcdfaad934dc453f8cf1f8b1a4eb181c` |

## End-to-End Execution

Three records passed the reviewed response schema, required nested-value checks, and exact cohort-identifier checks. After explicit loading into a fresh ToolUniverse instance, the same three cohort calls executed:

| Cohort | Disease | Participants | Follow-up | Progression change | Access wait |
| --- | --- | ---: | ---: | ---: | ---: |
| `ALS-NEURO-001` | Amyotrophic lateral sclerosis | 428 | 36 months | -13.4 | 47 days |
| `DMD-PED-014` | Duchenne muscular dystrophy | 312 | 48 months | -8.1 | 62 days |
| `SMA-NAT-022` | Spinal muscular atrophy | 196 | 30 months | -5.7 | 35 days |

## Closed Growth Loop

Replanning classified the original gap as `existing_exact` and selected `VSDRareDiseaseLongitudinalCohort`. Repeating the same catalog search then removed the already-registered endpoint and returned an auditable duplicate reason, preventing the growth loop from proposing it again.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `all_five_catalog_providers_succeeded` | PASS |
| `catalog_credentials_are_not_persisted` | PASS |
| `catalog_metadata_remained_inert` | PASS |
| `cross_catalog_duplicates_were_merged` | PASS |
| `demand_was_observed_three_times` | PASS |
| `discovered_endpoint_matches_reviewed_contract` | PASS |
| `five_distinct_candidates_survived_format_and_relevance_filters` | PASS |
| `initial_workflow_identified_the_real_gap` | PASS |
| `irrelevant_and_unusable_records_were_filtered` | PASS |
| `post_publication_discovery_suppressed_registered_endpoint` | PASS |
| `published_tool_closed_the_workflow_gap` | PASS |
| `published_tool_was_absent_until_explicit_load` | PASS |
| `review_gate_blocked_early_publication` | PASS |
| `three_complex_cohort_records_executed` | PASS |
| `three_verification_cases_passed` | PASS |
| `verification_approval_publication_hash_chain_is_complete` | PASS |

## Boundary

This proves discovery and software-governance behavior against deterministic provider fixtures. It does not certify the scientific quality of a catalog record, approve a provider automatically, or let an agent bypass contract review and human approval.

**Case audit SHA-256:** `9228fde0fa09fd290c1dba149b6c06675f16e75cfc21db9405882a2fd7b87f3f`
