# Check protein C-alpha stereochemistry locally

`PDB_check_alpha_stereochemistry` checks the signed geometric orientation of
N/CA/C/CB in a selected legacy PDB model. Mirroring a center changes its
handedness while leaving its internal distances unchanged. Use this check after
coordinate generation or refinement, alongside atom inventories, covalent
geometry, disulfides and any appropriate physical diagnostics.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(include_tools=["PDB_check_alpha_stereochemistry"])
result = tu.tools.PDB_check_alpha_stereochemistry(pdb_path="structure.pdb")
data = result["data"]
print(data["opposite_or_degenerate_centers"], data["uncheckable_centers"])
```

Local paths and inline PDB content stay local. Only an explicitly supplied public
`pdb_id`, such as `1UBQ`, triggers a bounded download from RCSB. Supply exactly one
of `pdb_path`, `pdb_content`, or `pdb_id`; unused alternatives can be `None`.
The 4 MiB input limit and selected-model behavior match `PDB_inspect_structure`.
mmCIF input is not supported by this legacy PDB tool.

The determinant is `det(N-CA, C-CA, CB-CA)` in Å³. A positive sign corresponds to
the usual L-amino-acid geometry and a negative sign to D geometry. This fixed atom
ordering is **not** formal CIP R/S assignment: natural L-cysteine is still
reported as L. Glycine has no C-alpha handedness and is counted separately.
`expected_orientation="D"` supports an all-D coordinate hypothesis.

Near-planar geometry can make the sign misleading. The default
`minimum_normalized_volume=0.1` flags a small absolute determinant divided by the
product of the three vector lengths. Set it to zero for an orientation-only
diagnostic. `degenerate_tolerance_A3` independently handles numerical degeneracy.
These are geometry parameters, not affinity or energy thresholds.

Every alternate conformation is checked separately, using its own atoms and any
unambiguous shared backbone atoms. Missing or duplicated center atoms and
conflicting residue identities are uncheckable; they do not silently pass.
Caller-declared residue aliases, for example `{"HIE": "HIS"}`, can identify
force-field labels. TER-separated segments are kept separate, even when chain
and residue labels are reused.

Counts remain complete when detail lists are truncated. Check both
`all_checked_centers_match` and `complete_coordinate_center_coverage`, or their
combined `all_coordinate_centers_match_expected`. Zero checked centers cannot
produce a passing result. Coverage concerns coordinate residues only: missing
SEQRES residues require a separate inventory check.

This tool does not reconstruct coordinates or check Ile/Thr sidechain chirality,
the complete bond graph, energetics, binding, or pH selectivity. A successful tool
execution can report a failing geometry check. The response keeps
`structure_chemistry_verified`, `binding_verified`, and `pH_selectivity_verified`
false.

The tests use public 1UBQ and 1CRN coordinates, proper rotations, full and
single-center reflections, near-planar synthetic centers, missing atoms,
alternate locations and selected models. No unpublished design data are used.
