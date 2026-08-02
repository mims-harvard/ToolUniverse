# OpenAPI-to-Tool ALS Registry Case Study

**Generated:** 2026-08-01T18:52:50.208765+00:00

## Decision Question

Can an administrator turn the provider's current OpenAPI operation into a narrow ToolUniverse tool that retrieves exact ALS trial records without granting an agent arbitrary API access?

**Result:** Yes. The local specification produced an inert candidate; the selected GET operation passed three exact record checks, was hash-approved, then loaded explicitly into a fresh ToolUniverse instance.

## Official Contract Inspection

- Provider documentation: https://clinicaltrials.gov/data-api/api
- Current specification: https://clinicaltrials.gov/api/oas/v2
- Contract: ClinicalTrials.gov REST API 2.0.5 (OpenAPI 3.0.3)
- Source SHA-256: `ba31adaea67e6bb09ff77af5c0c11daf36d5aff7f5d6cbed89f0aab04b297aea`
- Operations inspected: 9 (9 promotable, 0 blocked)

The inspector read a local, bounded copy of the provider contract. It did not fetch, register, or execute any operation. Every candidate began with `execution_allowed: false`.

## Selected Operation

| Property | Reviewed value |
| --- | --- |
| Operation | `fetchStudy` |
| Request | `GET https://clinicaltrials.gov/api/v2/studies/{nctId}` |
| Response | `application/json` validated against the provider schema |
| Candidate | `47a4c7402dfb7b86` |
| Blockers | `[]` |

Only the required `nctId` path argument was exposed. The response format was fixed to JSON; CSV, ZIP, RIS, and FHIR choices in the broader provider operation were not exposed by this generated tool.

## Verification And Approval

The draft `vsdclinicaltrialsstudybynct_27f9c4e92c3f` ran 3 distinct ALS record cases. Each case required the nested title, status, condition, and NCT identifier paths and asserted that the returned identifier exactly matched the requested one.

| NCT ID | Status | Phase | Brief title | Response bytes |
| --- | --- | --- | --- | ---: |
| `NCT03019419` | COMPLETED | PHASE2 | Perampanel for Sporadic Amyotrophic Lateral Sclerosis (ALS) | 7724 |
| `NCT04428775` | TERMINATED | PHASE2 | A Safety and Biomarker Study of ALZT-OP1a in Subjects With Mild-Moderate ALS Disease | 14170 |
| `NCT04745299` | COMPLETED | PHASE3 | Evaluation the Efficacy and Safety of Mutiple Lenzumestrocel (Neuronata-R® Inj.) Treatment in Patients With ALS | 17119 |

Approval bound the exact source, candidate, operation, draft, verification, and publication hashes. A fresh ToolUniverse instance did not contain the tool until the approved publication was loaded explicitly.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `candidate_inert_before_review` | PASS |
| `candidate_integrity_hash_propagated` | PASS |
| `exact_nested_identifiers_verified` | PASS |
| `fresh_runtime_loaded_explicitly` | PASS |
| `generated_contract_is_read_only` | PASS |
| `hash_chain_complete` | PASS |
| `invalid_identifier_rejected_before_transport` | PASS |
| `official_contract_parsed` | PASS |
| `provider_responses_schema_validated` | PASS |
| `published_tool_absent_before_load` | PASS |
| `three_distinct_cases_verified` | PASS |
| `zero_redirect_https_provenance` | PASS |

## Interpretation

The practical value is contract conversion with evidence: an administrator can review one operation in a provider's official specification, narrow its inputs, prove it against real records, and distribute a hash-bound tool. The agent receives only that approved operation, not a generic HTTP client or the ability to promote other operations.

**Boundary:** This case demonstrates software-governance and public-registry retrieval. It does not assess eligibility, efficacy, safety, or treatment suitability.

**Audit SHA-256:** `cec78d5359fdf83a262576323925d7ed1b750bafbfd2490dbb18d677fab18170`
