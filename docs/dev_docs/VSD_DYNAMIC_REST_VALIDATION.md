# VSD Reviewed Dynamic REST Runtime

## Scope

This phase restores the useful execution portion of PR #32 without restoring
arbitrary URL execution or automatic publication. An administrator-reviewed
operation can be attached to one `ToolUniverse` instance and invoked through
`run_one_function()`. Nothing is loaded by default and nothing is persisted by
this phase.

The runtime deliberately supports only public, read-only HTTPS JSON `GET`
operations. Authenticated or mutating APIs require a dedicated integration with
source-specific security review.

## Enforced Contract

- Exact-host allowlisting and public DNS resolution before every request.
- Connection to one pinned public IP while preserving TLS hostname validation.
- No redirects, proxy inheritance, credentials, nonstandard ports, or URL query
  strings in operation definitions.
- One shared wall-clock deadline and a one-megabyte undecoded response limit.
- Strict JSON media type, UTF-8 decoding, and finite JSON numbers.
- JSON Schema validation for tool arguments and provider responses.
- Exact argument-to-path/query mapping; every declared argument must be used.
- Percent encoding for path arguments and credential-name rejection for query
  parameters.
- Stable SHA-256 digests for both the reviewed operation and returned payload.

## End-to-End Proof

`examples/vsd/dynamic_rest_als_case_study.py` defines two independent reviewed
operations backed by ClinicalTrials.gov. It registers both into one real
`ToolUniverse` instance, searches active or upcoming US studies for amyotrophic
lateral sclerosis, chooses one returned identifier deterministically, and calls
the second operation to retrieve that record. The case fails if either provider
schema drifts or the detail identifier differs from the search result.

Artifacts are written to:

- `examples/vsd/artifacts/dynamic_rest_als_snapshot.json`
- `examples/vsd/artifacts/dynamic_rest_als_snapshot.md`

The result is an execution and record-consistency proof. It is not a patient
matching system, eligibility assessment, scientific endorsement, or treatment
recommendation.
