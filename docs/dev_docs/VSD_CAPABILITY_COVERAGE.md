# VSD capability coverage resolution

VSD must inspect ToolUniverse before discovering or generating another tool. The
coverage resolver reads built-in specifications and runtime registrations without
instantiating all tools, changing the active tool selection, writing a search log,
or sending the request anywhere.

## Classification contract

- `existing_exact`: a stable operation identifier or reviewed endpoint contract
  matches, or a provider-specific tool satisfies the requested semantics and fields.
- `existing_partial`: a provider, tool, or composed workflow plausibly overlaps but
  does not prove complete operation coverage.
- `missing`: no provider, tool, or workflow crosses the conservative match boundary.

Exact matches return `use_existing`. Partial matches return
`review_existing_or_extend_provider`, which prevents creation of a duplicate source
while allowing a new operation in an existing provider family. Only missing requests
return `discover_external_candidate`.

The result includes scoring components, exact tool and workflow counts, a normalized
capability digest, and a digest of the registry snapshot used for the decision.
These hashes make a decision reproducible; they do not identify a user or transmit
anything to the ToolUniverse maintainers.

## Case study

`examples/vsd/capability_coverage_case_study.py` evaluates four demands against the
real packaged registry. It demonstrates that rare-disease registry demand resolves
to Orphanet, FDA label demand resolves to the existing FDA family, a multi-stage
drug-discovery request identifies a composed workflow, and an intentionally alien
capability remains missing and may proceed to external discovery.

Checked evidence is available in both
`examples/vsd/artifacts/capability_coverage_snapshot.md` and the corresponding JSON
ledger.
