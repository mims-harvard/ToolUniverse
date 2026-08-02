# ALS Source-To-Reviewed-Runtime Cross-Format Total Proof

## Research question

Can a real ToolUniverse capability gap move from reviewed source discovery through bounded scanning, content-addressed inspection, exact contract binding, representative verification, approval, publication, fresh-runtime loading, and useful execution across every supported format without duplicating an existing source or widening authority?

## Result

Yes. The case kept the already-covered NIH RePORTER interface out of promotion, selected six DANDI gap contracts, bound each to its exact provider and operation, passed eighteen verification executions, rejected eight substitution attempts, loaded six published tools into a fresh ToolUniverse instance, and executed a final ALS evidence request through each format.

## Connected end-to-end path

1. Audit 2,744 configured tools, 259 configured hosts, and the review-only 51-source catalog.
2. Separate the existing NIH RePORTER host from the missing DANDI capability.
3. Crawl two explicit hosts under robots, host, page, depth, byte, and time bounds.
4. Snapshot and inspect OpenAPI, GraphQL, AsyncAPI, Postman, WSDL, protobuf, and MCP documents without execution.
5. Leave existing OpenAPI coverage alone; select six DANDI gap operations for review.
6. Bind provider, operation, method, parameters, and format-specific identity into each promotion digest.
7. Run three representative cases per operation, approve and publish, then load only into a fresh runtime.
8. Execute the six resulting tools and preserve the independent administrator-only Docker boundary.

## Six-format promotion and execution

| Format | Tool | Exact bound identity | Verification cases | Final result SHA-256 |
| --- | --- | --- | ---: | --- |
| graphql | `VSDDandiAlsGraphQL` | `searchAlsElectrophysiology` | 3 | `0bede811bbd337cec362867215b00bc59d3acad19eafa2f4b701ba1744c21169` |
| postman | `VSDDandiDandisetREST` | `Get dandiset` | 3 | `bbcda30660be54c8efcd11069cdc20552dc849661a7f01738e2a0725c4fa4a9e` |
| wsdl | `VSDDandiPreservationSOAP` | `GetPreservationRecord` | 3 | `50c785cedb17a54a55f93a56e98c563ef0eec3cfe1493d316f0d64f400ab54a5` |
| protobuf | `VSDDandiAlsGRPC` | `/dandi.v1.DandisetService/SearchAlsDandisets` | 3 | `f6e343a501a986742c3f49143db9325a524cadb01355bf0c1be9bcbe1398f208` |
| mcp | `VSDDandiMetadataMCP` | `search_dandisets` | 3 | `c10fd43209262d0af7c7fc694abc12128419915e519e4663408f57a9b67fdad5` |
| asyncapi | `VSDDandiChangeEvent` | `dandisets/{dandisetId}/changes` | 3 | `f52963356a5498c7c4e1f45dfc177230b874919b4acdce26d390135d0dbf52d3` |

## Fail-closed substitution cases

| Attempt | Format | Result | Boundary that rejected it |
| --- | --- | --- | --- |
| `graphql_cross_provider` | graphql | rejected | Reviewed runtime endpoint does not match the contract candidate |
| `postman_missing_parameter_map` | postman | rejected | Postman contract parameters must resolve every endpoint variable exactly |
| `soap_action_substitution` | wsdl | rejected | Reviewed SOAPAction does not match the WSDL operation |
| `soap_body_substitution` | wsdl | rejected | Reviewed SOAP body operation does not match the WSDL operation |
| `grpc_rpc_substitution` | protobuf | rejected | gRPC method must occur exactly once in the reviewed descriptor set |
| `mcp_undeclared_tool` | mcp | rejected | Reviewed MCP tool is not declared by the contract candidate |
| `asyncapi_channel_substitution` | asyncapi | rejected | Reviewed event channel or schema does not match the AsyncAPI candidate |
| `asyncapi_source_omission` | asyncapi | rejected | Reviewed runtime endpoint does not match the contract candidate |

## Sixteen professional case studies

| PR | Phase and question | Concrete result | Checks/assertions |
| --- | --- | --- | ---: |
| [#416](https://github.com/mims-harvard/ToolUniverse/pull/416) | **reviewed source foundation**: Which Autauga County tracts warrant CHD evidence review without ranking people or making clinical claims? | Six ToolUniverse calls combined reviewed CDC, WHO, FDA, PubMed, and trial evidence with explicit interpretation limits. | 6 |
| [#417](https://github.com/mims-harvard/ToolUniverse/pull/417) | **reviewed dynamic REST**: Can a bounded generated ClinicalTrials.gov tool find active US ALS studies and retrieve one exact follow-up record? | Two reviewed operations returned 20 search records and a consistent exact study detail. | 3 |
| [#418](https://github.com/mims-harvard/ToolUniverse/pull/418) | **catalog discovery**: Can demand for active cancer-trial fields identify one API-ready public dataset without executing it? | One official NY dataset matched all six demanded capabilities and remained inert review material. | 4 |
| [#419](https://github.com/mims-harvard/ToolUniverse/pull/419) | **verification and promotion**: Can one reviewed cancer dataset become two narrow tools only after representative verification? | Two tools passed three cases each, were approved, published, freshly loaded, and executed. | 6 |
| [#420](https://github.com/mims-harvard/ToolUniverse/pull/420) | **administrator-only Docker lifecycle**: Can a local inference service be provisioned without exposing Docker lifecycle control to an agent? | Independent Linux CI proved a non-root, loopback-only, read-only, resource-bounded container lifecycle and exact payload hash. | 30 |
| [#421](https://github.com/mims-harvard/ToolUniverse/pull/421) | **registry and workflow reuse**: Does ToolUniverse reuse an existing FDA tool or workflow before declaring a capability gap? | Exact tools and a workflow were reused; only the intentional calibration request remained a discovery gap. | 4 |
| [#423](https://github.com/mims-harvard/ToolUniverse/pull/423) | **OpenAPI inspection and promotion**: Can an ALS OpenAPI contract yield one selected read operation with exact provenance and fresh-runtime execution? | Inspection, three-case verification, approval, publication, execution, and hash-chain validation passed. | 12 |
| [#424](https://github.com/mims-harvard/ToolUniverse/pull/424) | **workflow-aware planning**: Can a multi-step ALS workflow distinguish reusable tools from the one missing step without executing during planning? | Planning reused exact capabilities, isolated the gap, and changed only after explicit loading. | 12 |
| [#425](https://github.com/mims-harvard/ToolUniverse/pull/425) | **private unmet-demand ledger**: Can repeated missing needs be ranked locally and exported only as reviewed, sanitized proposals? | Private observations were deduplicated, ranked, and explicitly exported without raw prompts. | 13 |
| [#426](https://github.com/mims-harvard/ToolUniverse/pull/426) | **environment-backed credentials**: Can credentials rotate without changing the reviewed tool identity or leaking into artifacts? | Initial and rotated credentials executed while configs, promotion records, results, and artifacts stayed secret-free. | 14 |
| [#427](https://github.com/mims-harvard/ToolUniverse/pull/427) | **suspension, drift, and recovery**: Can a published tool fail closed on contract drift and return only after reviewed recovery? | Drift suspended loading, changed-schema evidence was reviewed, and recovery restored the exact tool. | 19 |
| [#428](https://github.com/mims-harvard/ToolUniverse/pull/428) | **demand-to-runtime total system**: Can ALS demand move through discovery, review, promotion, use, resolution, suspension, and recovery as one system? | The full demand-to-reviewed-tool loop passed with Docker preserved as an independent administrator boundary. | 26 |
| [#429](https://github.com/mims-harvard/ToolUniverse/pull/429) | **heterogeneous contract inspection**: Can six incompatible contract formats become an inert, content-addressed operation inventory? | GraphQL, AsyncAPI, Postman, WSDL, protobuf, and MCP produced ten identified operations without execution. | 27 |
| [#430](https://github.com/mims-harvard/ToolUniverse/pull/430) | **multi-protocol execution**: Can one rare-disease study execute reviewed GraphQL, REST, SOAP, gRPC, MCP, event, pagination, and response formats? | Ten runtime cases and one full WSDL promotion case passed 33 assertions. | 33 |
| [#431](https://github.com/mims-harvard/ToolUniverse/pull/431) | **organic source discovery and handoff**: Can official-source scanning find ALS interface gaps without duplicates, installation, or silent telemetry? | Fifty sources, seven formats, two cron scans, seven snapshots, and one consent-bound local handoff passed 28 assertions. | 28 |
| This PR | **cross-format total proof**: Can every implemented phase operate as one source-to-runtime system? | Six promotions, eighteen verification runs, six final executions, and eight rejected substitutions. | 21 |

## End-to-end assertions

- `all_eight_substitution_attacks_were_rejected`: passed
- `all_prior_case_artifacts_or_ci_evidence_pass`: passed
- `all_six_publications_loaded_in_fresh_runtime`: passed
- `all_six_published_tools_executed`: passed
- `catalog_sources_remain_review_only`: passed
- `every_binding_names_its_contract_candidate`: passed
- `every_format_passed_three_verification_cases`: passed
- `every_promotion_has_exact_binding_hash`: passed
- `existing_reporter_source_was_not_promoted`: passed
- `grpc_binding_names_exact_descriptor_method`: passed
- `handoff_remained_local_and_unsubmitted`: passed
- `only_dandi_gap_candidates_were_promoted`: passed
- `portfolio_covers_every_prior_vsd_phase_pr`: passed
- `portfolio_includes_independent_docker_boundary`: passed
- `postman_template_has_explicit_parameter_map`: passed
- `seven_content_addressed_snapshots_exist`: passed
- `seven_formats_were_discovered`: passed
- `six_contract_formats_reached_promotion`: passed
- `source_intelligence_assertions_pass`: passed
- `two_tamper_detecting_cron_scans_exist`: passed
- `workflow_demand_credential_and_lifecycle_studies_are_present`: passed

## Interpretation boundary

This proves software behavior, provenance, review gates, bounded transport, and deterministic fixture execution. It does not certify a provider's scientific content, convert catalog membership into trust for execution, submit the local handoff, or expose Docker lifecycle operations to an agent.

Audit SHA-256: `b24ce5cfa14069f6545d05ddf13a810456b212476f01f578cbaf40fe82e8997b`
