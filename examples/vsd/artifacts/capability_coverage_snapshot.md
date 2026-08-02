# VSD registry-first coverage study

## Question

Can VSD prevent duplicate API/tool generation by checking the real ToolUniverse
registry and its composed workflows before external discovery?

## Method

The offline study read 2,743 packaged and runtime-visible tool specifications. It
did not instantiate those tools, write a demand log, contact an API, or send the
capability descriptions anywhere. Four materially different demands exercised the
exact, partial, workflow, and missing branches.

## Results

| Demand | Classification | Decisive evidence | Action |
| --- | --- | --- | --- |
| Rare-disease genes and phenotypes | Existing partial | Existing Orphanet gene/phenotype tools and other disease resources | Review and reuse or extend existing providers |
| FDA label by set identifier | Existing exact | `FDA_get_drug_name_by_set_id` and the generic FDA label-field tool | Use existing tools |
| Disease-to-target-to-compound-to-ADMET literature workflow | Existing exact | `ComprehensiveDrugDiscoveryPipeline` | Use existing workflow |
| Quantum microscope waveform optimizer | Missing | No tool or workflow crossed the conservative match threshold | Continue to external discovery |

All four assertions passed. The complete normalized requests, bounded match
evidence, scoring components, registry digest, and capability digests are in
`capability_coverage_snapshot.json`.

## Interpretation

Provider overlap alone does not prove an exact operation. The resolver therefore
distinguishes a reusable exact operation from partial provider coverage, allowing
ToolUniverse to add a genuinely new operation without registering the same source
again. A missing result is only permission to begin candidate discovery; it is not
approval to execute or publish anything.
