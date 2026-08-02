# Multi-Catalog Breast-Cancer Program Study

## Decision Question

Can ToolUniverse turn a complex breast-cancer program need into a reviewed source portfolio while rejecting attractive but unsafe or unfit catalog results?

## Evidence Mode

- Study mode: `network_backed`
- Live catalog searches: **4**
- Replayed catalog searches: `["datagov"]`
- Candidate resource and contract qualification: `live`

`network_backed` means only the Data.gov catalog response is a captured real replay because its shared `DEMO_KEY` quota returned HTTP 429. The other four catalogs and all five selected resources/contracts are live.

## Why This Is Hard

The program needs molecular, trial, mortality, access, and outcome evidence. Those leads live in five catalogs with different APIs and metadata shapes, and a relevant catalog title does not prove that the underlying resource is current, safely executable, correctly typed, or contract-compatible.

## Initial Gap And Repeated Demand

- Initial action: `discover_missing_capabilities`
- Initial capability states: `{"mortality_context": "missing", "program_review": "agent_native", "trial_inventory": "missing"}`
- Demand records: **2**, each observed **3** times

## Five Real Catalog Searches

| Catalog | Evidence | Research role | Query | Catalog matches | Candidates | Selected lead |
| --- | --- | --- | --- | ---: | ---: | --- |
| `socrata` | `live` | local trial inventory | `active breast cancer clinical trials phase` | 39 | 1 | Current Active Clinical Trials - Roswell Park Cancer Institute |
| `datagov` | `replay` | outcome benchmark | `cancer` | 1 | 1 | (C) - Cancer Deaths - Column Chart |
| `data_europa` | `live` | current age-stratified cancer mortality | `cause of death cancer Ireland csv` | 1128799 | 5 | Principal Cause of Death |
| `ckan_data_gov_uk` | `live` | treatment-access delay | `cancer waiting times` | 163 | 5 | 62 Day Cancer Waiting Times by Tumour Site |
| `apis_guru` | `live` | genomics workflow contract | `genomics` | 2529 | 1 | Genomics API |

Every selected lead was still `unreviewed_candidate` with `execution_allowed=false` and a content digest. Catalog ranking was used for triage, never as approval.

## Qualification Decisions

| Catalog | Decision | Concrete reason |
| --- | --- | --- |
| Socrata | Published | Three distinct exact-site calls passed verification. |
| Data.gov | Not published | The catalog URL redirects to a signed object-store URL; the reviewed runtime rejected the redirect and query-bearing target before reading data. |
| Data Europa | Published | The bounded resource supplied a current, parseable JSON-stat mortality cube through 2024. |
| Data.gov.uk CKAN | Blocked | Provider returned `application/octet-stream` for catalog-declared CSV; the reviewed runtime refused the mismatch. |
| APIs.guru | Blocked | All 5 Google Genomics operations had authentication, write-method, request-body, or unsupported-parameter blockers. |

## Evidence Actually Retrieved

- **Trials:** `VSDCancerTrialsByPrimarySite` returned **23** exact `Breast` rows in the checked execution. The dataset is a registry snapshot; a populated `date_closed` must not be presented as currently recruiting.
- **Mortality context:** `VSDIrishCancerMortalityContext` returned malignant-neoplasm counts through **2024**: **2266** deaths at age 65 or under and **8041** over age 65, or **10307** combined.
- **Outcome candidate rejected:** the live endpoint failed bounded verification before its contents could be accepted for quality review.

These are source observations, not clinical conclusions and not cross-population comparisons.

## Promotion And Closed Loop

| Tool | Verification cases | Draft | Verification | Approval | Publication |
| --- | ---: | --- | --- | --- | --- |
| `VSDCancerTrialsByPrimarySite` | 3 | `750d2b50ada9` | `4288f40d992b` | `8e3da3508517` | `f3ceee3cb26a` |
| `VSDIrishCancerMortalityContext` | 3 | `216282468230` | `2f1c8d204a9d` | `14c816780cb5` | `f6eb42f295e8` |

The two tools were absent before explicit loading. Replanning classified both operations as exact existing capabilities, and repeat Socrata/Data Europa discovery suppressed one registered endpoint each.

## Exact VSD Advantage

| Task | Without VSD | With VSD |
| --- | --- | --- |
| Search five incompatible catalogs | Write five provider-specific clients and compare raw schemas manually. | Invoke one agent-facing tool and receive one inert candidate contract. |
| Decide whether a result is usable | A relevant title can be mistaken for a safe, current API. | Bounded verification exposed a redirect boundary, a MIME mismatch, blocked genomics operations, and stale replayed values. |
| Create reusable tools | Wire endpoints directly with no common review or evidence chain. | Publish only two exact hash-bound tools after verification and approval. |
| Avoid duplicate growth | Repeat searches can recreate an endpoint already in the registry. | Replanning finds exact coverage and rediscovery suppresses both endpoints. |

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `all_five_catalogs_returned_live_or_replayed_results` | PASS |
| `all_selected_candidates_are_hash_bound_and_inert` | PASS |
| `catalog_credentials_were_not_persisted` | PASS |
| `ckan_mime_mismatch_blocked_verification` | PASS |
| `datagov_unfit_resource_was_not_approved` | PASS |
| `demand_was_observed_three_times_before_growth` | PASS |
| `early_publication_was_rejected` | PASS |
| `genomics_contract_operations_were_blocked_before_drafting` | PASS |
| `initial_plan_identified_both_exact_capability_gaps` | PASS |
| `mortality_resource_completed_three_verification_cases` | PASS |
| `mortality_runtime_returned_current_age_stratified_data` | PASS |
| `mortality_totals_were_computed_from_provider_values` | PASS |
| `post_publication_discovery_suppressed_both_resources` | PASS |
| `post_publication_plan_resolved_both_exact_capabilities` | PASS |
| `published_tools_were_absent_until_explicit_load` | PASS |
| `trial_registry_completed_three_distinct_verification_cases` | PASS |
| `trial_runtime_returned_exact_site_rows` | PASS |
| `two_hash_chains_reached_publication` | PASS |

## Boundary

This is a software-governance and public aggregate-data retrieval proof. It does not establish trial eligibility, compare treatments, infer patient risk, or certify the scientific quality of a catalog listing.

**Case audit SHA-256:** `61fab0c67c77aacd3a6996fa1f7004bf6d13361359f77449bb6b9b41f07fe345`
