# Multi-Catalog Cancer Source Evaluation

## Evaluation Objective

Can ToolUniverse expand its registry for a multi-source cancer program while applying consistent qualification and publication controls to catalog candidates?

## Evidence Basis

- Study mode: `network_backed`
- Live catalog searches: **4**
- Replayed catalog searches: `["datagov"]`
- Candidate resource and contract qualification: `live`

`network_backed` means only the Data.gov catalog response is replayed from a previously captured live response because its shared `DEMO_KEY` quota returned HTTP 429. The other four catalogs and all five selected resources/contracts are live.

## Evaluation Scope

The program needs molecular, trial, mortality, access, and outcome evidence. Those leads live in five catalogs with different APIs and metadata shapes, and a relevant catalog title does not prove that the underlying resource is current, safely executable, correctly typed, or contract-compatible.

## Baseline Capability Assessment

- Initial action: `discover_missing_capabilities`
- Initial capability states: `{"mortality_context": "missing", "program_review": "agent_native", "trial_inventory": "missing"}`
- Demand records: **2**, each observed **3** times

## Catalog Search Results

| Catalog | Evidence | Research role | Query | Catalog matches | Candidates | Selected lead |
| --- | --- | --- | --- | ---: | ---: | --- |
| `socrata` | `live` | local trial inventory | `active breast cancer clinical trials phase` | 39 | 1 | Current Active Clinical Trials - Roswell Park Cancer Institute |
| `datagov` | `replay` | outcome benchmark | `cancer` | 1 | 1 | (C) - Cancer Deaths - Column Chart |
| `data_europa` | `live` | current age-stratified cancer mortality | `cause of death cancer Ireland csv` | 1129091 | 5 | Principal Cause of Death |
| `ckan_data_gov_uk` | `live` | treatment-access delay | `cancer waiting times` | 163 | 5 | 62 Day Cancer Waiting Times by Tumour Site |
| `apis_guru` | `live` | genomics workflow contract | `genomics` | 2529 | 1 | Genomics API |

Every selected lead was still `unreviewed_candidate` with `execution_allowed=false` and a content digest. Catalog ranking was used for triage, never as approval.

## Source Qualification Decisions

| Catalog | Decision | Concrete reason |
| --- | --- | --- |
| Socrata | Published | Three distinct exact-site calls passed verification. |
| Data.gov | Not published | The catalog URL redirects to a signed object-store URL; the reviewed runtime rejected the redirect and query-bearing target before reading data. |
| Data Europa | Published | The bounded resource supplied a current, parseable JSON-stat mortality cube through 2024. |
| Data.gov.uk CKAN | Blocked | Provider returned `application/octet-stream` for catalog-declared CSV; the reviewed runtime refused the mismatch. |
| APIs.guru | Blocked | All 5 Google Genomics operations had authentication, write-method, request-body, or unsupported-parameter blockers. |

## Accepted Runtime Evidence

- **Trials:** `VSDCancerTrialsByPrimarySite` returned **23** exact `Breast` rows in the checked execution. The dataset is a registry snapshot; a populated `date_closed` must not be presented as currently recruiting.
- **Mortality context:** `VSDIrishCancerMortalityContext` returned malignant-neoplasm counts through **2024**: **2266** deaths at age 65 or under and **8041** over age 65, or **10307** combined.
- **Outcome candidate rejected:** the live endpoint failed bounded verification before its contents could be accepted for quality review.

These are source observations, not clinical conclusions and not cross-population comparisons.

## Promotion and Registry Validation

| Tool | Verification cases | Draft | Verification | Approval | Publication |
| --- | ---: | --- | --- | --- | --- |
| `VSDCancerTrialsByPrimarySite` | 3 | `f355f33186ed` | `e764c2b08600` | `fea453e8ffd3` | `79fa7b176d30` |
| `VSDIrishCancerMortalityContext` | 3 | `b24787d59717` | `01b74b661904` | `c8a7d5427b1a` | `a07e75fbc3c7` |

The two tools were absent before explicit loading. Replanning classified both operations as exact existing capabilities, and repeat Socrata/Data Europa discovery suppressed one registered endpoint each.

## Measured Outcomes

The initial registry had no exact tool for either executable gap. The completed workflow added two reviewed tools, closed both gaps, and excluded three leads that did not meet publication requirements.

| Metric | Result |
| --- | ---: |
| Catalogs searched | 5 |
| Selected leads qualified | 5 |
| Tools published | 2 |
| Leads not published | 3 |
| Verification executions for published tools | 6 |
| Post-publication executions | 2 |
| Exact capability gaps closed | 2 |
| Exact registered candidates suppressed | 2 |

## Observed VSD Contribution

VSD converted two unmet capabilities into reusable ToolUniverse tools through one governed process spanning five catalogs. A direct integration could retrieve the same raw provider records, but it would need to recreate the catalog adapters, qualification controls, approval evidence, registry loading, and duplicate checks represented below.

| Activity | Direct-integration baseline | Observed VSD contribution |
| --- | --- | --- |
| Catalog search | Implement and maintain five provider-specific search clients and normalize their different response schemas. | One discovery interface returned ranked, inert candidates with a common schema and source provenance. |
| Source qualification | Implement equivalent transport, schema, media-type, contract, and freshness checks separately for each source. | Uniform checks identified the Data.gov redirect, CKAN media-type mismatch, and five unsupported genomics operations before approval. |
| Reusable integration | A direct script can retrieve the same provider values but needs a separate review, provenance, publication, and loading convention. | Two resources became content-addressed ToolUniverse tools after six verification executions and explicit approval. |
| Registry maintenance | Compare each proposed operation with the existing registry and distinguish exact identity from semantic similarity. | Replanning resolved both published operations and repeat discovery suppressed only their exact method, host, and path identities. |

## Validation Results

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

## Interpretation Limits

This evaluation covers software governance and public aggregate-data retrieval. It does not establish trial eligibility, compare treatments, infer patient risk, certify the scientific quality of a catalog listing, or compare the accuracy of VSD with a manually engineered integration.

**Case audit SHA-256:** `1ff0dc3fecde1eaef4067900dd915a5503b530344c8e3b77f9f46b81b4055fa1`
