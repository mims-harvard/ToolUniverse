# Conditional pH binding

Read when ranking designs for stronger acidic binding or acidic release.

## Specify direction and assay

Write the desired direction, pHs, receptor species, terminal construct, assay and detection threshold. Adding histidine can support either direction depending on bound/free environments and surrounding interactions; its free-amino-acid pKa is not a switch specification.

Read the actual experimental endpoint before using a public control. Retention after an acidic wash, dissociation kinetics, EC50 and equilibrium KD are different observables. Acid-wash retention does not supply paired equilibrium KD values; loading, avidity and molecular format can matter. Match species and format where possible. In TNF literature, verify whether “mTNF” means membrane-associated TNF rather than assuming it means murine TNF.

Crystal growth pH is not a binding assay. A published pH-dependent system can calibrate qualitative analysis, but another target or correlated copies of one crystal do not establish a target-specific detection threshold or success probability.

## Audit the complete bound/free system

Match chain, residue number, insertion code and canonical group type across calculations. Inventory expected groups from actual selected coordinates independently of worker output. A perfect match between two incomplete outputs does not establish coverage.

Include relevant acidic/basic sidechains and real N/C termini. PROPKA can internally label Asp/Glu and C-terminal carboxyl groups **COO**; filtering only `ASP`, `GLU`, or `C-` can silently omit them. Preserve upstream types and map biological identities using residue/terminal context. A terminal Asp can have both sidechain and terminal carboxyls. Hetero-ligand COO groups are not automatically protein Asp/Glu.

For same-coordinate partner analysis:

- Retain receptor glycans/cofactors or auxiliary subunits when required by the hypothesis; record what was removed.
- Restrict compared groups to the intended partner in **both** predictions. Auxiliary protein groups may remain in prediction output without becoming unmatched primary-partner groups.
- Compute both partners for aggregate linkage; the engineered histidine alone can omit opposing contributions.
- Mark missing, extra, unresolved or mismatched groups. Do not promote incomplete aggregates as full-system indices.

Use explicit free-component retention if the installed schema supports it. Otherwise prepare and audit the reference locally; do not pass unsupported parameters or silently change composition.

## Compare free references separately

Use independently predicted free components and components extracted from unchanged complex coordinates as separate, labeled hypotheses. Both can titrate; “same-coordinate” does not mean fixed protonation. Compare parent and mutant within the same reference convention, preparation and matched sample identities. A shared independent apo-receptor term can cancel in a paired difference; separately extracted receptors generally do not share that cancellation. A sign reversal across references is sensitivity, not a reason to select the favorable reference or average them.

For local integration, discover `Protein_calculate_pH_linkage` and inspect its installed schema. It postprocesses normalized pKa arrays; it does not predict pKas. Supply bound groups, the explicitly expanded union of all free molecular copies, an independently audited expected inventory with component labels, pH values/reference, reference kind and provenance. Map free chain/residue identities explicitly first. The tool rejects missing/extra/duplicate groups and reports component and terminal contributions. A match to the caller's expected inventory does not certify structural completeness; a partial declared inventory remains a partial-site diagnostic. Use the bundled [synthetic linkage example](linkage-example.md) after verifying that this interface is installed.

## Interpret scores at the computed level

State formula, sign convention, units, pH interval, matched-group count and assumptions. Show interface-site, other sidechain and terminal contributions. Independent-site linkage neglects coupling and conformational redistribution; it is not measured KD, a detection limit or an experimental pH population.

Keep same-mask comparisons when a predictor covers only a subset: disclose omissions such as disulfide cysteines and real termini. Two related weight sets remain one model family. Imposed-state learned energies without the complete proton chemical potential and relevant states are conditional diagnostics in their own units, not full pH linkage or kcal/mol affinity.

For coupled learned models, record imposed states, included components and cycle direction. Verify local updates against full rescoring before inverse searches. Individual-site behavior can disagree with the full cycle; report both. Opposing directions are unresolved evidence, not values to average across units.

## Calibrate gates without manufacturing hits

Use experimentally established public controls where available. State whether a control supports total cycle direction, individual edge behavior, or both. Expected aggregate direction can coexist with failure of a heuristic edge-fraction gate. Preserve the failed gate and identify which part is unvalidated; do not conflate it with total-direction failure.

Predeclare search constraints and thresholds. If nothing passes, report zero selected variants and limiting constraints. Check whether the model responds to mutations. Do not silently loosen a gate to force a hit.

## Treat termini as construct hypotheses

Terminal-excluded sensitivity is not chemical capping. An encoded extension is a new construct requiring hashes, coordinates, fold checks and official novelty review. Its apparent benefit may primarily reflect terminal contributions; assay tags, cleavage and processing can change it. Extensions of one core are not independent design families.

Do not inherit receptor/glycan, mouse or binding validation after a sequence change. Run a representative pilot and expand only when it reduces a specific uncertainty; preserve failures.

## Experimental claim boundary

Conditional binding requires matched assays at both pHs with controlled constructs, receptor preparation, buffers, concentration range and detection limits. Test cross-species binding separately. Report negative assays with their sensitivity. Computational improvements justify testing; they do not establish undetectable neutral-pH binding.
