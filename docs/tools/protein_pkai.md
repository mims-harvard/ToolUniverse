# Local pKAI side-chain diagnostics

`PKAI_predict_sidechain_pka` runs an installed pKAI model on the CPU. Supply exactly one of `pdb_path`, `pdb_content` or a public `pdb_id`. Paths and text remain on the execution host. Only the public-ID option downloads coordinates; the predictor does not upload structures or download weights.

Install the optional `pKAI` package in an isolated Python environment, following its [upstream instructions](https://github.com/bayer-science-for-a-better-life/pKAI). The tested PyPI release, 1.2.0, contains both TorchScript checkpoints and uses the lowercase `pkai` import namespace. It declares Torch 1.x dependencies; keep this installation separate from other model environments. `python_executable` can select a same-host interpreter with the dependencies and packaged weights already installed. The default uses the current interpreter. Missing dependencies or checkpoints return an error.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["protein_pkai"])
result = tu.tools.PKAI_predict_sidechain_pka(
    pdb_id="1UBQ", model_variant="pKAI+", threads=1
)
```

The upstream recommends pKAI+ for single-structure diagnostics and pKAI for explicitly sampled conformations. They are correlated variants of one model family, not independent experimental evidence. Both models predict ASP, GLU, HIS, LYS, CYS and TYR side chains. The supported backend does **not** implement ARG or actual N- and C-terminal predictions. Every successful response therefore has `complete_protein_ionization_inventory: false`; missing groups are never imputed or combined with another engine to claim a complete pH binding cycle.

Results include the installed package and Torch versions, checkpoint and input SHA256, exact supported-group coverage, and per-residue predictions. Upstream predictions are rounded to two decimals. Close SG pairs (at most 2.3 Å) are flagged as potentially disulfide-bonded. Explicit `SSBOND` annotations also mark CYS predictions ineligible for acid-base interpretation, regardless of coordinate distance; these declarations remain effective when a symmetry partner is absent from the supplied coordinates. Raw predictions are retained. A proximity flag alone does not establish a covalent bond, and these checks are not complete chemical validation.

Inputs require one PDB model, explicit standard residue names and complete observed backbone/ionizing atoms. Insertion codes, alternate locations, reused chain IDs across TER segments and duplicate atoms are rejected because the backend would otherwise skip or merge records. The tool performs only limited input checks, ignores HETATM features, and does not validate folding, stereochemistry, glycan compatibility, affinity or pH selectivity. Partial per-residue predictions and independent-site mathematics do not simulate coupled populations or conformational redistribution.
