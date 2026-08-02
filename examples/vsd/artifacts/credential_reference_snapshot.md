# Environment-Backed Rare-Disease Credential Case Study

## Decision Question

Can a reviewed ToolUniverse operation use a protected API without persisting, returning, or fixing the credential into its contract?

**Result:** Yes. The protected header was derived from a reviewed OpenAPI scheme, read only at execution, rotated without changing the operation digest, and rejected when missing, malformed, or reflected by the provider.

## Provider Boundary

A deterministic protected rare-disease API fixture is used because no real credential is bundled with the repository. The full ToolUniverse promotion and runtime paths are real; only network transport is replaced.

The OpenAPI inspector recognized one required `apiKey` header named `X-Rare-Disease-Key`. The inert candidate contains the header contract but no value. Promotion binds that contract to the environment reference `TOOLUNIVERSE_VSD_RARE_DISEASE_KEY`.

## Promotion Evidence

| Boundary | SHA-256 |
| --- | --- |
| Draft | `98cb65b06de746ef4bb13229701b62a89d1c9988e3ee37c9b6d8dd2499352939` |
| Operation | `d9f22e4ffdaead4202c5f2416509c73a472f57ff5ef018fc23e018709a371595` |
| Verification | `af0f010bc059a009edc44275596bd8982e93d9e7bab04b98b2ae53ef6b9ed4de` |
| Approval | `627048f102a22863fccc5dfe568fd1b0fd9ae1695bbf74199cd7d3fd9f89333b` |
| Publication | `6e46c2dda4472b19a7010ec395dbd60cba9bfdb738a72ec44dfc1c70b2cdd2f4` |

Three authenticated verification cases retrieved ALS, Duchenne muscular dystrophy, and spinal muscular atrophy records with genes, phenotypes, and trial identifiers before approval and publication.

## Runtime And Rotation

A fresh ToolUniverse instance loaded `VSDProtectedRareDiseaseEvidence`, returned `RD-ALS`, then returned `RD-SMA` after credential rotation. The operation SHA-256 was unchanged because the reviewed contract stores only the environment reference.

Missing and malformed values failed before transport. A provider response that reflected the exact runtime credential was rejected before schema validation or result construction.

## End-to-End Assertions

| Assertion | Result |
| --- | --- |
| `approved_publication_is_hash_bound` | PASS |
| `candidate_remains_inert_before_promotion` | PASS |
| `credential_environment_is_restored` | PASS |
| `credential_reference_is_the_only_persisted_auth_material` | PASS |
| `fresh_tooluniverse_executes_published_tool` | PASS |
| `header_is_not_exposed_in_result_or_provenance` | PASS |
| `invalid_credential_fails_before_transport` | PASS |
| `missing_credential_fails_before_transport` | PASS |
| `openapi_header_auth_is_recognized` | PASS |
| `provider_reflection_is_rejected` | PASS |
| `secret_rotation_preserves_operation_identity` | PASS |
| `secret_values_are_absent_from_artifacts` | PASS |
| `three_authenticated_verification_cases_pass` | PASS |
| `transport_receives_only_reviewed_header` | PASS |

## Secret Boundary

No credential value appears in the draft, verification evidence, approval, publication, ToolUniverse result, provenance, or checked case artifact. The environment variable name is not a secret and remains in the reviewed contract so operators know what to configure.

**Case audit SHA-256:** `0fd635055d4f7c06cf8568d9d83d09c5697b98021d7fe3ae8b6c5f535fc066d5`
