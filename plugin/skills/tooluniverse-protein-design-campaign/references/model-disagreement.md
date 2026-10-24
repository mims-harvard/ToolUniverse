# Resolve pose disagreement and apparent sequence improvements

Read when complex predictors disagree or inverse-folding scores favor variants.

## Decompose disagreement before redesign

Retain all native samples and their model-family, checkpoint, seed and request identities. Deduplicate coordinate aliases within family using a documented canonical coordinate representation; raw file hashes change with headers and formatting. Keep the alias map and original artifacts.

Use the same residue correspondence, atom selection, fit convention and contact cutoff for parent and variant. First fit the ligand to itself to measure intrinsic fold deformation. Separately fit a declared receptor region, then measure ligand placement **without another ligand fit**. Report receptor-fit quality and coverage, ligand placement RMSD, centroid displacement, and ligand-surface, receptor-epitope and residue-pair contact overlaps. Similar ligand surfaces can still face different receptor residues or contact registers. Do not treat Jaccard overlap of empty contact sets as binding evidence.

For flexible multidomain or membrane receptors, compare relevant domain fits separately from the whole-chain fit. A poor whole-chain fit dominated by flexible tails can change apparent clashes. Keep all samples, including disagreeing ones; summarize poses within each source family and keep related checkpoints separate. A family with more samples must not gain more independent votes. These summaries are sensitivity analyses, not statistical probabilities of a pose being correct.

When screening an existing glycan context, transform the ligand hypothesis into the source receptor frame and leave the linked glycan coordinates attached to that receptor. Label this as alternate-context sensitivity, not glycans newly equilibrated on the predicted receptor. New variant poses require their own check.

## Control sequence priors on the same backbone

An improved conditional inverse-folding score in a complex may reflect a generic sequence or fold preference. Comparing against an independently predicted free fold also changes ligand geometry and cannot isolate receptor context.

For each bound pose, keep ligand coordinates, parent sequence, effective design mask, scoring mode, software and checkpoint fixed. Remove only the receptor for a ligand-only control; audit atom identity and exact retained ligand backbone before scoring. Preserve both raw requests and masks. Explicitly define any other retained component. Do not run a second full-complex call if a complete identical result already exists.

At a selected position, compute in natural-log probability units:

`delta_full = log p(mutant | full complex, other parent residues) - log p(parent | full complex, other parent residues)`

`delta_deleted = log p(mutant | same ligand backbone, receptor removed, other parent residues) - log p(parent | same ligand backbone, receptor removed, other parent residues)`

`context_effect = mean(delta_full) - mean(delta_deleted)`

Use normalized native probabilities over the entire alphabet, including X when present. Reject unselected zero placeholder rows, logits, incomplete alphabets and unconditional outputs. A native conditional table can supply many mutation comparisons without that many native model calls.

Decode samples separately in each system. The same numeric seed with different system lengths need not generate common random noise. Use the descriptive **unpaired sample range** `[min(full)-max(deleted), max(full)-min(deleted)]`, not an index-paired uncertainty estimate or confidence interval. Preserve each pose/checkpoint and its sample dispersion. Related soluble/vanilla weights remain one scoring family.

| Finding | Interpretation and next decision |
|---|---|
| Full and receptor-deleted gains are similar | Much of the gain is compatible with a sequence/backbone prior; do not promote it as an interface improvement. |
| Context effect changes sign across source poses or scoring checkpoints | Preserve the disagreement and test the opposing hypotheses with matched validation. |
| Effect survives deletion control only for one source pose family | A pose-discriminating sequence hypothesis; independent mutant complex prediction can test it. |
| Positive effect across declared contexts | Learned fixed-geometry receptor-context support; fold, chemistry, glycan checks and experimental validation still remain. |

None of these is binding free energy, KD, pose probability, pH selectivity or agonism. Receptor deletion omits relaxation, solvation, entropy and conformational populations.

## Use the registered local postprocessor

Discover `Protein_compare_receptor_context` and inspect its installed schema. Use `NvidiaNIM_proteinmpnn` for its documented sequence-generation capability; do not assume it exposes native conditional probability mode. Obtain conditional rows through a verified suitable local/remote provider. The postprocessor runs locally, makes no model or network calls, and does not extract native files or verify coordinates.

Supply the selected one-based ligand sequence position, parent/mutant residues, complete alphabet, scoring family, declared pose/checkpoint matrix and full/deleted score rows. Supply identical retained-ligand coordinate and sequence hashes, effective masks and common protocol digests for each pair. A protocol digest identifies common scoring settings, software and coordinate-hash convention; exclude pose, checkpoint, receptor-presence flag and decoding seed from that shared digest. Record those varying inputs separately in native manifests.

The tool checks declared identity equality, full-alphabet normalization and exact coverage of the declared pose × checkpoint matrix. It returns per-pose effects and equal-pose means within each source-family/checkpoint group. It cannot establish whether a caller omitted a native pose or supplied correct hashes, residue labels, masks or family assignments: audit native artifacts first. A partial matrix must remain incomplete; do not quietly redeclare it complete after a failed call.

Run this packaged **analytic** control after verifying the tool is installed. It uses categorical probability rows, not a biological candidate or an experimental calibration. The expected context effect is ln(2) nats.

```python
import json
import math
from importlib.resources import files
from tooluniverse import ToolUniverse

config_path = files("tooluniverse").joinpath("data", "protein_design_context_tools.json")
config = json.loads(config_path.read_text())[0]
args = config["test_examples"][0]
tu = ToolUniverse()
tu.load_tools(include_tools=["Protein_compare_receptor_context"])
result = tu.run_one_function(
    {"name": "Protein_compare_receptor_context", "arguments": args}, use_cache=False
)
assert result["status"] == "success"
effect = result["data"]["rows"][0]["receptor_context_effect_nats"]
assert math.isclose(effect, math.log(2), abs_tol=1e-12)
assert result["data"]["coordinate_identity_verified"] is False
assert result["data"]["binding_verified"] is False
```

## Freeze the next comparison prospectively

Protect core positions using the declared exposure/chemistry checks across the independent free folds; record thresholds as campaign policy, not universal defaults. Keep a pose-discriminating arm separate from broadly sequence-compatible proposals. Select the next bounded experiment to distinguish hypotheses, not merely maximize a score.

If a new control changes priority, retain the original ranking and frozen thresholds. Write a new policy version, evidence link and decision timestamp **before** seeing the relevant new validation results. Reuse unchanged request payloads; record adaptive prioritization separately. Validate promoted variants under parent-matched constructs, MSAs, templates, seeds and geometry procedures. A template-conditioned placement is not independent complex validation.
