# Complete VSD Oncology Source-Governance Case Study

## Decision Question

Can ToolUniverse start from an oncology evidence need, keep generic source administration outside the agent boundary, execute reviewed contracts, discover an unknown API without executing it, and promote only verified narrow tools with a complete audit chain?

## End-to-End Result

| Stage | Boundary exercised | Live proof |
| ---: | --- | --- |
| 1 | Administrator-only source catalog | Registered, probed, listed, queried, removed, and restored the temporary catalog |
| 2 | Packaged reviewed adapter | Discovered openFDA offline and retrieved the same tamoxifen label through a fixed typed tool |
| 3 | Reviewed dynamic REST | Searched active/upcoming New York breast-cancer studies and retrieved one deterministic NCT record |
| 4 | Demand-driven discovery | Searched the fixed Socrata catalog and kept the selected API non-executable pending review |
| 5 | Reviewed promotion | Ran six live verification cases, approved hash-bound drafts, and published two bounded tools |
| 6 | Explicit runtime loading | Loaded both publications into a fresh ToolUniverse instance and executed exact-filter queries |

## 1. Administrative Source Lifecycle

- Source: `openfda_tamoxifen_review` at `https://api.fda.gov/drug/label.json`
- Probe HTTP status: **200**
- Query records: **1** of **14** provider matches
- Selected label set ID: `1e6ff055-590c-41e6-9530-1fdf04cdbd02`
- Removed after inspection: **true**
- Catalog restored: **true**
- Boundary: Registration and generic querying occurred only through the administrator CLI. They did not publish an agent-facing tool.

## 2. Reviewed Source Adapter

- Offline source: **openFDA Drug Labels**
- Agent-facing tool: `VSDOpenFDALabelBySetId`
- Label: **SOLTAMOX** (`TAMOXIFEN CITRATE`)
- Effective time: `20211129`
- Route: `ORAL`
- Administrative operations present in the agent runtime: **0**
- Provider payload: `adfd73ae9a40c8fae86c31cc30bed62c88a7d232cae237f9c0aba2fa6541d6d9`

The generic administrative query established a record identifier only. The agent-facing call used the fixed openFDA endpoint, UUID input contract, source-specific response validation, and typed provenance.

## 3. Reviewed Dynamic REST

- National registry matches: **546**
- Bounded records returned: **20**
- Status counts: `{"ACTIVE_NOT_RECRUITING": 13, "RECRUITING": 7}`
- Phase counts: `{"NA": 2, "NOT_APPLICABLE": 1, "PHASE1": 2, "PHASE2": 11, "PHASE3": 5}`
- Deterministic detail record: `NCT01766297`
- Search/detail ID match: **true**

Both operations are reviewed HTTPS GET contracts with exact argument mappings, bounded schemas, no credentials, zero redirects, pinned public destinations, response limits, and operation/payload hashes.

## 4. Demand-Driven API Discovery

- Demand query: `active cancer clinical trials primary site phase protocol`
- Catalog matches: **13**
- Candidates reviewed: **10**
- Selected dataset: **Current Active Clinical Trials - Roswell Park Cancer Institute** (`2ig8-yxf8`)
- Proposed endpoint: `https://data.ny.gov/resource/2ig8-yxf8.json`
- Required fields present: **6/6**
- Execution allowed before review: **false**
- Selection rule: Require non-executable unreviewed state, an official government API-ready catalog record, and all six demanded fields; then choose the highest score with candidate ID as the stable tie-breaker.

## 5. Promotion And Fresh Runtime

| Tool | Required filter | Verification rows | Runtime query | Runtime rows |
| --- | --- | --- | --- | ---: |
| `VSDTotalCancerTrialsBySite` | `primary_site` | 19, 23, 20 | `primary_site=Breast` | 23 |
| `VSDTotalCancerTrialsByPhase` | `study_phase` | 25, 25, 25 | `study_phase=III` | 25 |

- Live verification cases: **6**
- Promoted tools present before explicit load: **0**
- Explicitly loaded publications: `VSDTotalCancerTrialsByPhase`, `VSDTotalCancerTrialsBySite`

Every draft, verification result, approval, and publication is bound to the preceding SHA-256 records. Loading is a separate explicit call; discovery alone never executes or publishes a candidate.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `administrative_catalog_restored` | PASS |
| `administrative_tools_not_agent_facing` | PASS |
| `discovery_candidate_has_required_fields` | PASS |
| `discovery_candidate_remained_non_executable` | PASS |
| `dynamic_search_detail_identifier_match` | PASS |
| `fixed_adapter_matches_admin_record` | PASS |
| `promoted_tools_absent_before_explicit_load` | PASS |
| `promotion_hash_chain_complete` | PASS |
| `published_runtime_filters_exact` | PASS |
| `published_tools_loaded_explicitly` | PASS |
| `reviewed_source_discovered_offline` | PASS |
| `six_live_promotion_cases_passed` | PASS |

## Reproducibility And Audit Chain

- End-to-end evidence-chain SHA-256: `0530702a8466da09286370a3303fbf68361074ea6543f8d86ef57d2aa7a6ebc6`
- Generated at: `2026-08-01T04:31:36.578274+00:00`
- The JSON artifact contains provider payload hashes, reviewed operation hashes, promotion hashes, exact arguments, bounded samples, and every assertion used to accept the run.

## Interpretation Boundary

This is a software-governance and public-record retrieval demonstration. It does not match patients to trials, establish eligibility, compare treatments, or provide medical advice. The state and national registries are independent and are not joined at record level.
