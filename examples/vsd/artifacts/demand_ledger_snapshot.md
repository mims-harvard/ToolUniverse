# Private ALS Capability-Demand Ledger Case Study

## Decision Question

Can repeated workflow gaps be counted and prioritized locally without silently reporting queries or exporting satisfied capabilities?

**Result:** Yes. Three hash-bound ALS plans and two retinal-calibration observations produced a deterministic unmet-demand ranking; one exact FDA capability was retained locally but excluded, and only two reviewed proposals were written to a non-transmitting export.

## Hash-Bound Workflow Input

Plan `f41c063db82dc5db` was verified against its complete SHA-256 before any observations were committed. Three distinct scheduled runs recorded five unmet tool steps each; replaying the last run recorded nothing because its event hashes were already present.

| Step | Fulfillment | Coverage |
| --- | --- | --- |
| `genes` | tool | existing_partial |
| `phenotypes` | tool | existing_partial |
| `literature` | tool | existing_partial |
| `trials` | tool | existing_partial |
| `drug_label` | tool | existing_exact |
| `microscopy_calibration` | tool | missing |
| `synthesis` | agent | agent_native |

## Local Priority Ranking

Missing observations receive five points and partial observations receive two. Exact coverage remains available in the private ledger but does not enter the unmet-demand ranking.

| Rank | Reviewed public summary | Exact | Partial | Missing | Score |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | Quantitative microscopy calibration for ALS research workflows | 0 | 0 | 3 | 15 |
| 2 | Traceable adaptive-optics retinal imaging calibration for research workflows | 0 | 0 | 2 | 10 |
| 3 | ALS biomedical literature retrieval for evidence workflows | 0 | 3 | 0 | 6 |
| 4 | ALS clinical-trial retrieval for evidence workflows | 0 | 3 | 0 | 6 |
| 5 | ALS rare-disease gene retrieval for evidence workflows | 0 | 3 | 0 | 6 |
| 6 | ALS rare-disease phenotype retrieval for evidence workflows | 0 | 3 | 0 | 6 |

## Explicit Proposal Export

Only the two highest reviewed demand IDs were selected. The export contains stable proposal IDs, safe structured capability fields, aggregate counts, and a review decision. It contains no local demand IDs, raw query descriptions, event IDs, or filesystem paths.

| Proposal | Public summary | Next step |
| --- | --- | --- |
| `332f9444843c672c` | Quantitative microscopy calibration for ALS research workflows | `review_external_api_candidates` |
| `2540259f913360b4` | Traceable adaptive-optics retinal imaging calibration for research workflows | `review_external_api_candidates` |

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `agent_synthesis_is_not_recorded` | PASS |
| `already_satisfied_demand_is_not_ranked` | PASS |
| `batch_plan_identity_is_verified` | PASS |
| `duplicate_run_is_deduplicated` | PASS |
| `event_ids_are_not_persisted` | PASS |
| `export_contains_only_selected_demands` | PASS |
| `export_is_hash_bound` | PASS |
| `export_is_local_only` | PASS |
| `ledger_has_expected_population` | PASS |
| `ledger_is_hash_bound` | PASS |
| `local_paths_are_not_exposed` | PASS |
| `raw_descriptions_are_not_persisted` | PASS |
| `repeated_missing_demand_ranks_first` | PASS |

## Privacy And Execution Boundary

The ledger is private and local; raw descriptions and event IDs are not stored. Export is an explicit reviewed file write and performs no network transmission, candidate creation, tool registration, or execution.

**Ledger SHA-256:** `240d1ceb612d5408b6a1ebb4c0232f5eaeadb6be4a88c2fd6a4797de266b33d6`

**Export SHA-256:** `fcec4c64b6522d01a6919133c98f8a347eb6b3eb23d4781ee1a3e593502aaec8`

**Case audit SHA-256:** `ca1cdf0f5ff2f6c1018f39251323edd8e6789bdf0bff066cafdea012aa5aa346`
