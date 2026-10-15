---
name: tooluniverse-protein-design-campaign
description: "Run and review iterative protein binder design campaigns with multiple model families, structural and glycan checks, conditional pH hypotheses, resource-aware computation, and competition submission preparation. Use for ongoing candidate optimization or interpreting conflicting design evidence; not for simple structure retrieval or measured assay analysis."
---

# Protein Design Campaign

Turn an ongoing binder-design effort into reproducible candidate decisions and an honestly described experimental or competition submission. Preserve the user's chosen models, infrastructure and goals; this skill does not grant permission to upload unpublished designs, publish a repository or accept terms.

## Establish the current decision

For an existing campaign, read its latest status, manifests, executed results and failure records before launching jobs. Distinguish a completed process from an active one; an old PID or a queued browser file is not proof of ongoing computation or submission.

Record target isoform/species, assay construct and termini, intended epitope, glycosylation assumptions, molecule class, designable positions, and objective direction. Explicitly distinguish **stronger binding at acidic pH** from **binding at neutral pH with acidic release**. They are different objectives, not interchangeable consequences of adding histidine.

For competitions, verify the live challenge, account track, deadlines, novelty definition and molecule formats. Convert the deadline with an explicit UTC offset; AoE means UTC−12. Keep current competition limits in the campaign record, not as permanent defaults in this skill.

## Choose the next informative computation

1. Resolve execution or input defects before generating more designs. Missing atoms, misidentified glycans or incomplete pKa inventories invalidate downstream scores.
2. Test known positive controls through the **same preparation and scoring pipeline**. If a known binder fails, diagnose the pipeline before treating the cutoff as a candidate veto. Keep the original result and any revised criterion separate.
3. Spend compute on distinct uncertainty: foldability, complex pose, receptor/glycan compatibility, protonation mechanism, or cross-species compatibility. More seeds assess sampling but do not supply another model family.
4. When models disagree, compare constructs, component retention, protonation conventions and coordinate preparation. Do not average unrelated units into an apparent consensus.
5. Keep an experimental route visible: matched SPR/BLI or an equivalent binding assay at the specified pHs, with receptor species and construct controls. Computation cannot establish an assay detection threshold.

Use [structure-validation.md](references/structure-validation.md) for identity mapping, sidechains, glycans and controls. Read [ph-selectivity.md](references/ph-selectivity.md) for conditional binding. Read [compute-and-provenance.md](references/compute-and-provenance.md) before restarting failed jobs or scaling model coverage.

## Separate evidence dimensions

Do not call a design an experimentally supported binder based on pLDDT, pTM, low clash count, or a relaxed structure. Report these dimensions independently:

| Evidence | What it supports | What it does not establish |
|---|---|---|
| Independent monomer folds and core checks | Foldability and sampled agreement | A bound pose or affinity |
| Complex predictions with calibrated controls | A model-dependent pose hypothesis | Measured binding or success probability |
| Receptor/glycan geometry checks | Compatibility in explicitly sampled contexts | All native glycoforms or binding energy |
| Restrained physical preparation | Local geometry under specified force fields | Equilibrium stability or convergence without diagnostics |
| Complete bound/free pKa analysis | A protonation-linked hypothesis | Measured pH selectivity, KD, or no detectable binding |
| Partner-species analysis | Compatibility with the evaluated construct | Experimental cross-reactivity |
| Matched experimental assays | Binding within tested conditions | Generalization to untested constructs |

Report unique sequences, model families, seeds, conformers, prepared contexts and controls separately. State attempts planned, started, successful, failed and skipped. Near-identical variants and correlated structures are not independent replications.

## Maintain recoverable evidence

Use stable sequence identities and hashes, versioned parameters, input/output hashes, software/checkpoint versions, structure mappings, and explicit failure reasons. Keep original failed results and mark superseded analyses. A repaired aggregation bug requires recomputation of dependent rankings, not just edited narrative.

The campaign report should answer: what changed, which assumption was tested, what the result means, what remains unverified, and which next action reduces the largest uncertainty. Keep each statement traceable without putting operational logs in the user-facing report.

If a ToolUniverse defect is reproducible, reduce it to public or synthetic data before fixing it or proposing a PR. Keep unpublished candidate sequences, coordinates, backups, account details and credentials out of public patches.

## Prepare a reviewed submission

Read [submission.md](references/submission.md) for ranking, privacy, eligibility, browser state and receipt verification. Complete preparation and reversible checks before requesting still-required authorization. Preserve existing authorization; ask only for genuinely missing disclosure or action-time agreement confirmation.

The bundled local helper checks a CSV against configurable format limits, optional source identity, and common disclosure hazards. From this skill's directory, run:

```bash
python scripts/preflight_submission.py candidates.csv --methods methods.txt --source-csv source_candidates.csv --min-length 10 --max-length 250 --max-designs 20
```

Supply limits, class values and `--paired-classes` chain conventions from the actual portal. This helper uses no network, does not submit, and cannot certify official novelty, rights, scientific review or absence of all sensitive information. Inspect the exact files manually as well. Do not silently modify the package after the user reviews it.

## Completion criteria

- Promoted candidates have exact sequences and traceable rationale, with unsupported objectives labeled unverified.
- Controls, incomplete inventories, disagreement, failed jobs and superseded scores remain visible.
- Only intended data enter the reviewed package; required human review is actual, not inferred from AI work.
- Submission success has a portal receipt and verified candidate count; an upload, preview or click alone is insufficient.
