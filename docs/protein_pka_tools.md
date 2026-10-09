# Local protein pKa diagnostics

Install the optional dependency with `pip install 'tooluniverse[protein-pka]'`.
Neither the framework nor these tool modules import PROPKA at startup. Each
calculation runs in a temporary directory in a separate process with a bounded
timeout. It does not write `.pka` files beside the caller's input or change the
parent process's working directory or logging configuration.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(tool_type=["protein_pka"])
prediction = tu.tools.PROPKA_predict_pka(
    pdb_path="complex.pdb", ph_values=[6.5, 7.4]
)
comparison = tu.tools.PROPKA_compare_partner_pka(
    pdb_path="complex.pdb", partner_chain="B", ph_values=[6.5, 7.4]
)
```

Supply exactly one of `pdb_path`, `pdb_content`, or `pdb_id`. Files and inline
text remain local. Only `pdb_id` downloads a public structure from RCSB. Input
is limited to 2 MiB; explicitly select one model and remove alternate atom
locations before calculation. The calculation timeout defaults to 180 seconds
and can be set between 1 and 600 seconds.

Before prediction, observed standard-protein intraresidue N–CA, CA–C, C–O
and C–OXT distances must lie within conservative 1.0–2.2 Å sanity bounds.
Grossly broken bonds or duplicate backbone atoms return an input error before
the worker starts. Valid inputs report the checked bond count and missing
N/CA/C/O atom count in `input_backbone_geometry`. Missing atoms are not
reconstructed or presumed valid. This check does not cover peptide continuity,
sidechains, steric clashes, glycans, or stereochemistry; passing is not a
complete structure validation.

Results retain chain, PDB residue number, insertion code, group type, input
hash, PROPKA version and warnings. Comparison extracts the requested chain
from the same bound coordinates and matches these identifiers, including
termini as distinct group types. It reports missing groups instead of treating
them as zero shifts. There is no free-state relaxation. Path-based results are
not cached because the contents of the file may change.

`protonated_fractions` are independent-site Henderson-Hasselbalch estimates,
not coupled-site populations or net charges. Protein ionization groups are
reported; ligand pKa predictions are excluded. The tools perform no atom
reconstruction, complete geometric validation, glycan collision checking or physical
binding free-energy calculation. A pKa shift does not establish affinity or
pH selectivity; both validation flags remain false.

The offline test fixture contains protein atom records from public experimental
structure [1UBQ](https://www.rcsb.org/structure/1UBQ). The example compares the
single chain to itself as a zero-shift control.

API reference: [PROPKA `run.single`](https://propka.readthedocs.io/en/stable/api/propka.run.html).
