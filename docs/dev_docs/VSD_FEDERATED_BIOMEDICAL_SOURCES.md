# Federated Biomedical Source Scanning

## Purpose

The federated scanner extends VSD discovery from two large API directories to a
reviewed set of official biomedical service contracts. Source metadata is a
sealed, declarative manifest; the scanner contains no provider-specific URLs,
operation names, or scientific cases. Adding a source therefore changes data,
not scanner control flow.

Source review grants permission only to retrieve and inspect one bounded
machine-readable contract. It does not approve any operation. Generated
configuration previews remain inert until the existing VSD verification,
approval, publication, and explicit local-loading stages succeed.

## Source Manifest

The packaged manifest is
`src/tooluniverse/data/vsd_federated_sources.json`. Its 20 entries cover official
services for protein models, bioinformatics software, cancer genomics, cell
lines, molecular QTLs, nucleotide archives, tissue expression, sequence
analysis, protein families, microbiomes, gene-disease knowledge, genome data,
ontologies, omics datasets, macromolecular structures, proteomics, structural
search, pathways, and research workflows.

Every source record declares:

- a stable source identifier and organization;
- official documentation and exact OpenAPI contract URLs;
- the reviewed HTTPS runtime base URL;
- access requirements and scientific topics;
- the basis for trusting the source owner;
- an inert execution state; and
- a content hash that seals the record.

The enclosing manifest is also hashed. Validation rejects undeclared fields,
duplicate or unsorted identities, unbounded lists, non-HTTPS URLs, IP literals,
credential-bearing URLs, unreviewed states, and digest mismatches. The generic
implementation supports up to 250 reviewed sources without adding adapter code.

## Operation Discovery

Run the complete packaged manifest:

```console
tooluniverse-vsd-scan \
  --state-directory ~/.tooluniverse/vsd/federated-biomedical \
  run-federated
```

Run a separately reviewed manifest:

```console
tooluniverse-vsd-scan \
  --state-directory ~/.tooluniverse/vsd/federated-custom \
  run-federated --manifest ./reviewed-sources.json
```

Read the latest sealed summary without contacting any source:

```console
tooluniverse-vsd-scan \
  --state-directory ~/.tooluniverse/vsd/federated-biomedical \
  status --kind federated
```

Each cycle retrieves every declared contract without redirects, limits each
response to 1 MB, canonicalizes parsed OpenAPI content, and records both raw and
semantic hashes. Semantic hashing prevents harmless key-order or whitespace
changes from creating new candidate identities while preserving evidence of raw
representation changes.

The scanner then uses the common OpenAPI inspector and configuration generator
to classify every operation. It checks exact operation and host coverage against
the loaded ToolUniverse registry, deduplicates identities across sources,
records all blockers, and retains only a hash and name for each draftable
preview. It never calls an operation, writes the built-in registry, publishes a
tool, or loads a generated configuration.

State is written atomically with a cross-process lock. Immutable cycle history,
the latest report, content-addressed contract snapshots, semantic source deltas,
and fully recomputed validation make the command suitable for cron or another
administrator-owned scheduler.

## Measured Evaluation

The live evaluation completed two full source cycles and a separate cancer
qualification study against the actual ToolUniverse registry:

| Measure | Result |
| --- | ---: |
| Reviewed service sources | 20 |
| Contracts inspected successfully | 20 |
| Distinct operations inspected | 1,142 |
| Structurally draftable, inert previews | 533 |
| Preview identities overlapping the earlier catalog portfolio | 15 |
| Incremental identities beyond the earlier portfolio | 518 |
| Combined unique candidate identities | 3,559 |
| Selected tools passing three live verification cases | 7 |
| Accepted live calls, including post-publication runtime calls | 42 |
| Drifted candidates rejected before approval | 3 |

The 533 previews are candidates, not approved tools. The first 3,097 catalog
rows also contain duplicate operation identities; the cross-portfolio comparison
uses 3,041 unique baseline identities and reports the exact 518-operation
increment after deduplication.

The qualification asks whether one locally loaded evidence panel can connect
three cancer contexts to seven independent evidence layers without editing the
built-in registry. It verifies TP53 in cervical cancer, BRCA1 in breast cancer,
and EGFR in lung cancer across protein models, normalized genes, pathways,
reference coordinates, experimental cell lines, regulatory associations, and
sequencing panels. Every selected tool is generated from its current contract,
passes all three cases before approval, is explicitly published and loaded into
a fresh runtime, and then succeeds for all three cases again. Three other
contract-derived candidates fail current response-schema validation and remain
unapproved and unpublished.

Review the human-readable report at
`examples/vsd/artifacts/federated_biomedical_expansion_study.md`. The synchronized
machine-readable evidence is
`examples/vsd/artifacts/federated_biomedical_expansion_study.json`, and the full
inert scan ledger is
`examples/vsd/artifacts/federated_biomedical_source_scan.json`.

Reproduce the live qualification with:

```console
PYTHONPATH=src uv run python \
  examples/vsd/federated_biomedical_expansion_study.py \
  --workspace ./.vsd-federated-biomedical-study
```

## Scaling Boundary

This work does not claim 20,000 tools. Reaching that scale responsibly requires
hundreds of additional official contracts or high-quality registries, plus
deduplication, representative inputs, live response verification, ownership,
and maintenance. Counting endpoints or datasets without those stages would
overstate usable ToolUniverse capability.

The manifest and generic scan path remove the need for a new code adapter per
official service, so reviewed sources can be added incrementally. A practical
expansion process should admit sources only when the official owner exposes a
stable contract, documentation, HTTPS runtime identity, access policy, and a
maintainer who can own verification failures and contract drift. Demand and
workflow gaps should prioritize which inert candidates receive the more
expensive promotion work.
