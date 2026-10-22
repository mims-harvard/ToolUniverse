# Protein coordinate stereochemistry

Use both checks after coordinate generation, reconstruction, geometric initialization and physical preparation. A preprocessing stage can change a stereocenter even when later minimization preserves its input. Distance or force checks alone cannot detect mirrors.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(include_tools=[
    "PDB_check_alpha_stereochemistry",
    "PDB_check_beta_stereochemistry",
])
alpha = tu.tools.PDB_check_alpha_stereochemistry(pdb_path="model.pdb")
beta = tu.tools.PDB_check_beta_stereochemistry(pdb_path="model.pdb")
```

The inputs are legacy PDB coordinates: exactly one local `pdb_path`, inline `pdb_content`, or four-character public `pdb_id` such as `1UBQ`. Local coordinates stay local. Select one model by file order; models, TER segments and alternative locations are not pooled. Input size is limited to 4 MiB. Native mmCIF requires a separately recorded format conversion; this tool does not perform reconstruction.

The alpha check uses `det(N−CA, C−CA, CB−CA)`, positive for natural L geometry, including cysteine. The beta check uses `det(CA−CB, CG1−CB, CG2−CB)` for Ile and substitutes OG1 for CG1 for Thr. Positive beta orientation is labeled `natural`, negative `opposite`; these are independent of alpha L/D labels and are not formal CIP R/S assignments. An isolated beta mirror can pass the alpha check.

Check `complete_coordinate_center_coverage`, `uncheckable_centers`, and `all_coordinate_centers_match_expected` alongside the issue list. Beta results also report `eligible_beta_residues` and `beta_check_applicable`. Fully recognized input with no eligible Ile/Thr residues means inapplicable, zero checked centers, and no vacuous pass. Unrecognized backbone-like identities can make applicability unknown (`null`) rather than falsely inapplicable. Missing or ambiguous atoms, unrecognized backbone-like residues, unexpected elements, nonfinite coordinates and nearly planar centers are reported or rejected. Counts remain complete when detail lists are truncated.

The default minimum absolute normalized determinant is 0.1; setting it to zero requests orientation-only screening. This is a geometric diagnostic, not an experimentally calibrated energy cutoff. Caller-provided residue aliases declare canonical amino-acid identity; they do not prove the original modification's chemistry.

Neither check certifies complete stereochemistry, sidechain bond lengths, valence, disulfides, native glycan compatibility, equilibrium stability, affinity, or pH selectivity. They inspect only the specified coordinate centers; missing declared sequence regions remain outside their scope. Validate physical chemistry and declared/observed sequence coverage separately.
