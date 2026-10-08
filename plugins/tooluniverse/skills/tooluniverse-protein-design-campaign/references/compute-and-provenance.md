# Resource-aware execution and recoverable evidence

Read before scaling or recovering from reset/OOM.

## Diversify relevant assumptions

Maintain a matrix of family, role, sequence/complex inputs, receptor construct, seed, samples, MSA source, templates, glycans and calibration. Generators, monomer folds, complex predictors, pKa tools and force fields answer different questions; they are not equivalent binding predictors.

Different weights or soluble/vanilla checkpoints of one architecture are not independent families. Shared MSAs/templates correlate outputs even across families. Keep private queries local; gap-padding public homologs for an insertion does not establish homolog support for that insertion or redesigned CDR.

For requests to run every relevant model, enumerate applicability and coverage, then run feasible models in stages. Mark unavailable, licensed, memory-limited or inapplicable models. Do not call a monomer model a complex validator to fill the matrix.

## Observe usable memory

Inspect current device allocatable/free memory, host available/free memory, other processes and disk space. Unified-memory systems may have high host available RAM while CUDA allocations fail. Hardware totals or `nvidia-smi` alone may not provide admission evidence.

Serialize large jobs with a campaign-owned lock, isolate incompatible runtimes, and set measured per-model thresholds with finite waiting. These reserves are environment-specific. Ensure child processes completed before analyzing or copying outputs.

After OOM/reboot, distinguish killed workers, startup failures, partial outputs and resumed controllers. Reconcile PID ownership, exit status, hashes and output counts before retrying. Retain failed and recovered calls separately.

Prefer smaller workloads, serialization or bounded retries of owned jobs. Do not restart a shared machine, kill unrelated processes or globally drop caches to rescue the campaign.

A per-file page-cache eviction hint can be considered for a **known, finished, read-only checkpoint** after confirming no active worker needs it. It is advisory and filesystem-dependent, not a universal recovery step. Measure device memory before/after and verify file identity/content; do not mutate checkpoints. Use only when safer recovery is insufficient and the action is authorized.

## Verify artifacts

Check nonempty output, format, sequence/chains, atoms and hashes. HTTP success may contain an error, encoded artifact, archive or relative reference. Decode documented formats, bound polling/retries, and do not respond to a public-control failure with an unauthorized private upload to another service.

Preserve inputs/outputs, versions, parameters, seeds, mappings and scoring-code revisions. Distinguish active snapshots from final snapshots. Use candidate/round-specific paths; copied generic summary names can overwrite other results.

Write corrections as versioned results with supersession links. Verify archive entry counts/hashes before deleting sources or claiming a backup is complete. Resume from verified completed stages after a reset.

## Convert defects to public fixes

Separate caller/environment mistakes, service failure, capacity limits and tool bugs. Check installed schemas, declared dependencies and a public/synthetic reproducer. Incompatible local dependencies are not automatically upstream defects.

For real bugs, test scientific invariants: group coverage, component retention, identity-resolved links, decoding or declared/observed sequence coverage. Keep private campaign data out of fixtures, docs and PRs. Validate on public data, then rerun affected private scores under a recorded revision.
