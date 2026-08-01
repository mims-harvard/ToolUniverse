# Registry-First ALS Workflow Planning Case Study

**Generated:** 2026-08-01T19:45:04.241132+00:00

## Decision Question

Can an agent preflight a complicated ALS research workflow, reuse existing tools and workflows, and isolate only the truly missing capability?

**Result:** Yes. The planner retained exact and partial registry coverage for review, sent only the microscopy-calibration gap to non-executable discovery, and recognized an existing drug-discovery workflow with all dependencies present.

## ALS Workflow Preflight

The planner scanned 2,744 registered specifications without loading those tools. It returned the following dependency-ordered plan:

| # | Step | Coverage | State | Best existing match | Next interface |
| ---: | --- | --- | --- | --- | --- |
| 1 | `genes` | existing_partial | needs_review | `Orphanet_get_genes` | `get_tool_info` |
| 2 | `phenotypes` | existing_partial | needs_review | `Orphanet_get_phenotypes` | `get_tool_info` |
| 3 | `literature` | existing_partial | needs_review | `PubTator3_GetEntityRelations` | `get_tool_info` |
| 4 | `trials` | existing_partial | needs_review | `ClinicalTrials_get_field_values` | `get_tool_info` |
| 5 | `drug_label` | existing_exact | ready_existing | `FDA_get_drug_name_by_set_id` | `get_tool_info` |
| 6 | `microscopy_calibration` | missing | missing | `None` | `VSDDiscoverAPICandidates` |
| 7 | `synthesis` | agent_native | blocked_by_dependencies | `None` | `None` |

The exact FDA-label capability is ready to reuse. Registry genes, phenotypes, literature, and trials have plausible existing coverage that must be inspected with `get_tool_info`. The agent-native synthesis waits for its dependencies and cannot enter API discovery. Only the intentionally absent microscopy-calibration step receives a `VSDDiscoverAPICandidates` handoff, and that handoff is still non-executable.

## Existing Workflow Shortcut

A separate whole-goal preflight selected `ComprehensiveDrugDiscoveryPipeline`. All 8 named dependencies are present in the registry, so the planner recommends loading that workflow rather than rebuilding it.

| Dependency | Registry state |
| --- | --- |
| `ADMETAI_predict_BBB_penetrance` | present |
| `ADMETAI_predict_bioavailability` | present |
| `ADMETAI_predict_toxicity` | present |
| `LiteratureSearchTool` | present |
| `OpenTargets_get_associated_drugs_by_disease_efoId` | present |
| `OpenTargets_get_associated_targets_by_disease_efoId` | present |
| `PubChem_get_CID_by_compound_name` | present |
| `PubChem_get_compound_properties_by_CID` | present |

## Tool Finder Integration

The existing keyword finder was called with capability coverage enabled. It returned 5 ranked tools and classified the FDA-label request as `existing_exact` with action `use_existing`. The Finder and workflow planner reported the same registry SHA-256, proving they evaluated the same local registry snapshot.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `dependency_order_is_valid` | PASS |
| `drug_label_reuses_exact_tools` | PASS |
| `finder_and_planner_share_registry_digest` | PASS |
| `finder_returns_coverage_with_ranked_tools` | PASS |
| `known_steps_never_route_to_discovery` | PASS |
| `missing_dependency_blocks_synthesis` | PASS |
| `only_real_gap_routes_to_discovery` | PASS |
| `planner_does_not_load_registry_tools` | PASS |
| `planner_is_deterministic` | PASS |
| `planner_is_local_non_executable` | PASS |
| `required_gap_controls_overall_action` | PASS |
| `whole_workflow_shortcut_has_complete_dependencies` | PASS |

## Boundary

This study plans and inspects only. It does not execute scientific tools, download data, persist demand, or create API candidates.

**Audit SHA-256:** `8f2863ca0fdfd5f5577f36a33f72fb0efe1043e6156b3743b7e7ab54b88e2d0a`
