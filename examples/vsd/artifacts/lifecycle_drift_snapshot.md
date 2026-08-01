# Protected Rare-Disease Provider Drift And Lifecycle Case Study

## Decision Question

Can ToolUniverse distinguish harmless provider documentation changes from contract drift and keep unsafe publications out of fresh runtimes?

**Result:** Yes. Six inert assessments distinguished unchanged, metadata-only, review-required, and breaking contracts; explicit hash-bound state events controlled loading without modifying the approved publication.

## Provider Boundary

A deterministic protected rare-disease provider replaces network transport. Inspection, promotion, verification, credential handling, lifecycle validation, fresh loading, and execution use production paths.

## Reviewed Publication

The baseline protected operation passed three disease-specific cases before approval. The publication remains immutable throughout every lifecycle transition.

| Evidence | SHA-256 |
| --- | --- |
| Draft | `6eb25e7785b6638f7a3d87b895ac5154572c59f3a4bffbc0d54f3099b2c00949` |
| Verification | `5f8d0ee864d1c56ece5820f8bce8627734d1c5fc0b64a7562364f10ebe0ba715` |
| Approval | `0719320ddfe68e1a7a7bdaa964505ef4b01e5c662c7ca4ebdc3f11913abc529b` |
| Publication | `021c511b2b79bd5dca03cd5ecb28ef59e635472a1001ab99beac84350a2ddb30` |

## Drift Classification

| Contract | Classification | Changes or blockers | Suspend? |
| --- | --- | --- | --- |
| `unchanged` | `unchanged` | `none` | no |
| `metadata_only` | `metadata_only` | `none` | no |
| `review_required` | `review_required` | `response_validation` | yes |
| `breaking_endpoint` | `breaking` | `endpoint` | yes |
| `breaking_auth` | `breaking` | `operation_policy` | yes |
| `repaired` | `unchanged` | `none` | no |

Assessments are local, inert evidence. A recommendation never changes runtime state on its own.

## Explicit Lifecycle

The administrator explicitly suspended the publication using the breaking endpoint assessment. A fresh ToolUniverse instance loaded no tool. After the baseline contract was confirmed again, an explicit activation restored loading and two authenticated executions passed, including a credential rotation. Retirement then excluded the tool and could not be reversed for that publication.

Lifecycle sequence: `suspended -> active -> retired`.

A modified event failed validation before any registration. Each event links the previous event digest and the exact publication digest.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `active_publication_executes_after_repair` | PASS |
| `all_assessments_are_inert_and_hash_bound` | PASS |
| `breaking_auth_drift_is_blocked` | PASS |
| `breaking_endpoint_drift_recommends_suspension` | PASS |
| `credential_environment_is_restored` | PASS |
| `credential_rotation_preserves_operation_identity` | PASS |
| `exact_contract_is_unchanged` | PASS |
| `explicit_suspension_prevents_fresh_loading` | PASS |
| `lifecycle_events_form_a_hash_chain` | PASS |
| `metadata_drift_does_not_recommend_suspension` | PASS |
| `publication_anchor_matches_current_history` | PASS |
| `response_drift_requires_new_review` | PASS |
| `retired_publication_cannot_be_loaded` | PASS |
| `retirement_is_terminal` | PASS |
| `secret_values_are_absent_from_artifacts` | PASS |
| `state_does_not_change_during_assessment` | PASS |
| `tampered_lifecycle_fails_before_registration` | PASS |
| `three_protected_verification_cases_pass` | PASS |
| `unchanged_repair_supports_explicit_activation` | PASS |

## Operational Boundary

The lifecycle command reads a local OpenAPI file; it does not crawl, fetch, execute, suspend, activate, retire, or republish automatically. State is local to one VSD workspace and affects newly loaded ToolUniverse instances. Already-running instances must be restarted or otherwise unloaded by their host application.

**Case audit SHA-256:** `9d35320f91ed03ec6ae7423c3193a8dfcd8cfcc611bea1bfb0d7defd2de09420`
