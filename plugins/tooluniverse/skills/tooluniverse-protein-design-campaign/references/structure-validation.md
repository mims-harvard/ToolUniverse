# Structure identity, physical preparation and controls

Read when a score depends on a bound pose, missing atoms, receptor context or glycans.

## Map identities before distances

Map canonical sequence, declared polymer sequence, observed residues and model residue numbers. Include chain, insertion code, residue name, alternate location and model identity. Observed coordinates can conceal missing loops or termini; amino-acid identity alone does not resolve repeated segments.

Obtain framework/CDR annotation for each antibody candidate, then map numbering labels back to actual sequence indices. Do not apply IMGT labels as literal array offsets. Prefixes change sequence indexing without changing domain numbering. Record public framework provenance and redesigned regions; an internal mutation criterion is not an official novelty score.

For glycans, map identities from the source connection graph (`struct_conn` in mmCIF or explicit PDB LINK), root attachment, component identity and bond atom names. Do not equate hetero-chain appearance order with identity. Renumbering can create huge apparent LINK distances when correspondence is wrong; check identity before declaring a broken bond. A missing LINK record is a metadata gap, not evidence of absent chemistry.

Separate missing declared links, resolvable links failing a distance check, unresolved/ambiguous atoms, and externally inferred bonds. Do not collapse them into one collision count.

## Validate coordinates before physics

Design outputs can have valid backbones but absent, zero-filled or coincident sidechains. Audit expected atoms, duplicate identities, peptide C–N continuity, missing stretches, disulfide geometry and residue identities before interpreting energy or interface distances.

Rebuild missing atoms with a documented method, retaining original files and execution failures. Mark modeled loops and termini as modeled. Recover a lost atom from a verified prior output when appropriate, with provenance; do not invent a terminal group to improve a score.

Hydrogen-bond claims need donor/acceptor identities, the actual hydrogen if present, relevant distances and directional geometry. A nearby histidine nitrogen is not automatically a directional hydrogen bond. Verify HID/HIE/HIP atom identities after preparation; these are imposed states, not equilibrium pH populations.

## Place and refine without overstating the result

A monomer fitted by framework Cα alignment is a **template-conditioned placement**, not independent docking. Clashes may reflect loop conformation or rigid placement; a fold metric cannot repair this interpretation gap.

Benchmark against the experimentally bound native control and selected free-model controls with the same alignment, partner selection, atom filters, cutoffs and preparation. A short antigen fragment is not full-receptor/glycan calibration; record that difference.

If a known binder fails, retain the failure and mark the criterion unvalidated as an absolute binding veto. If restrained refinement resolves the control, apply the same declared procedure to candidates. Neither outcome proves a candidate binds. A cutoff retuned on one control has not been independently validated by that same control.

Record force field, solvent, restraints, movable components, steps/time, termination reason and force/displacement diagnostics. Completion is not force convergence. Strong restraints can preserve an imposed pose. Use per-residue displacement as well as chain-average RMSD when movement matters.

## Name glycan coverage

Distinguish observed roots, modeled sugars, conformers, site occupancy, complete glycoforms and receptor conformations. Many configurations from a few poses remain correlated conditional contexts.

If glycans are static obstacles outside the force field, say so; do not describe protein-only minimization as joint glycoprotein refinement. Account for glycans on the free receptor in bound/free comparisons; deleting them changes the reference system.

## ToolUniverse capability checks

Inspect installed schemas and execute a public/local smoke check before documenting exact calls. Availability depends on the installed revision; a PR is not proof a capability exists locally.

- `PDB_inspect_structure`: inspect metadata coverage; an inventory is not a force-field topology validator.
- `PROPKA_predict_pka` and `PROPKA_compare_partner_pka`: local hypotheses, not binding validation; see the pH reference.
- If `PDB_compare_declared_links`, declared/observed sequence auditing, or MSA inspection are available, use explicit identity/coverage outputs. Otherwise audit source records locally and do not claim these tools ran.

After adopting a repaired worker, record its version/hash and rerun affected analyses. Public bug reproductions should use public structures or synthetic fixtures.
