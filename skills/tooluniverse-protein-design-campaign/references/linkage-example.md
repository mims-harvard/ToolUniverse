# Local linkage analytic control

Use only after discovering `Protein_calculate_pH_linkage` in the installed
ToolUniverse revision. This tool integrates supplied pKas; it is not a
predictor. A one-site toy system tests sign and units without a GPU or network.
It is deliberately partial and cannot represent a complete protein reaction.

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(include_tools=["Protein_calculate_pH_linkage"])
site = {"chain": "A", "residue_number": 1, "group_type": "HIS"}
result = tu.run_one_function({
    "name": "Protein_calculate_pH_linkage",
    "arguments": {
        "bound_groups": [{**site, "pka": 7.0}],
        "free_groups": [{**site, "pka": 6.0}],
        "expected_groups": [{**site, "component": "binder"}],
        "reference_kind": "independent_coordinates",
        "reference_ph": 6.0,
        "ph_values": [6.0, 7.0],
        "provenance": {
            "pka_method": "synthetic analytic control",
            "inventory_source": "declared one-site toy system",
            "reference_description": "independently specified one-site free reference",
        },
    },
}, use_cache=False)
```

Expected pH 7 values: `relative_log10_association` ≈ −0.480725379 and
`relative_linkage_energy_kcal_mol` ≈ +0.655828162 at the default 298.15 K.
Positive energy is relative to pH 6 here, not a claim of acidic release.
The sign for a campaign depends on its actual requested and reference pHs.
Adding an expected C- group absent from both prediction arrays must fail.

For real systems, independently inventory the selected coordinates, normalize
free chain/residue/insertion identities, expand every molecular copy and include
all relevant partners and real termini. Generic COO types require coordinate
context. Supply matching component/construct chemistry on both sides and retain
predictor failures outside the finite arrays. Matching supplied inventories does
not certify structural completeness or valid pKa predictions.

Report total, component and terminal contributions separately for each predictor
and reference convention. Same-coordinate components still titrate. Terminal
exclusion is a diagnostic, not chemical capping. Do not feed learned energies
into pKa fields or treat the conditional curve as measured affinity.
