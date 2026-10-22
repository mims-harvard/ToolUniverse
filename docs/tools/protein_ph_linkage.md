---
orphan: true
---

# Protein pH linkage from matched pKa inventories

`Protein_calculate_pH_linkage` is a local, standard-library postprocessor. Use
`PROPKA_predict_pka` or another suitable predictor to obtain pKas first. Unlike
`PROPKA_compare_partner_pka`, which predicts a same-coordinate primary partner,
this tool integrates a caller-supplied bound inventory against the explicitly
expanded union of **all** free components. It makes no remote requests.

The inventory must be independently audited from the selected construct and
coordinates. Supply each molecular copy explicitly, with free groups mapped to
bound chain/residue/insertion/type identities. For example, a three-chain
receptor plus one binder requires all four chains on both sides. Predict free
receptor subunits in their relevant associated state; do not turn an intact
trimer into three isolated monomers unless that is the intended reference.
The tool does not infer stoichiometry or molecular correspondence.

## Model and sign

For independent monoprotic sites, the proton binding polynomial is
`Q(pH) = product(1 + 10**(pKa - pH))`. With association defined as bound minus
all free components, the returned logarithmic trend is

```text
L(pH) = [ln Q_bound(pH) - ln Q_free(pH)]
      - [ln Q_bound(reference_pH) - ln Q_free(reference_pH)]
relative_log10_association = L / ln(10)
relative_linkage_energy_kcal_mol = -R * temperature_kelvin * L
R = 0.00198720425864083 kcal mol^-1 K^-1
```

Positive energy at an acidic requested pH relative to a neutral reference is a
release-direction **linkage contribution**. It is not a predicted absolute
binding free energy, experimental KD or a calibrated success probability.
`d(log10 K_assoc)/d(pH) = -delta_proton_count_bound_minus_free`.

`reference_kind` is either `independent_coordinates` or
`same_coordinate_components`. Both inputs contain titrating pKas: the latter
means unchanged component coordinates extracted from the complex, **not** a
fixed protonation state. Compare parent and mutant within each convention;
retain reference-dependent sign reversals.

## Tested synthetic one-site example

This toy HIS inventory is deliberately partial; it is an analytic control,
not a protein or a complete binding reaction.

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

At pH 7, the relative log10 association term is approximately **−0.480725**;
the conditional energy is approximately **+0.6558 kcal/mol** at 298.15 K.
At the reference pH, both relative quantities are zero. The inventory result
says `matches_supplied_expected_inventory: true` and
`structural_completeness_verified: false`.

The return includes total, per-component, terminal and nonterminal same-mask
curves, provenance and a normalized calculation hash. PROPKA-style group
arrays are accepted; extra predictor metadata is ignored. Supported normalized
types are ASP, GLU, HIS, LYS, ARG, CYS, TYR, N+ and C-. Resolve generic COO using
coordinate context before calling. An Asp C terminus can contain both ASP and
C- groups at the same residue.

## Failure and interpretation boundaries

Missing, extra, duplicate, unresolved or nonfinite groups cause an error rather
than silent intersection. A group missing from both predictions is caught only
if the independently supplied expected inventory includes it. Two equally
incomplete lists cannot establish structural completeness. Disulfide/capping
state, missing atoms, ligand groups and omitted molecular components require
external audit. Correct composition also does not prove valid pKa predictions.

The numerical model omits coupled microstates, conformational redistribution,
ligand ionization and ionic-strength effects. Terminal-excluded curves are
sensitivity diagnostics; they do not simulate a capped molecule. Do not supply
learned Hamiltonian scores as pKas or pool their units with kcal/mol. Each
predictor/reference/preparation should be calculated and reported separately.

Inputs are bounded to 2,000 groups per inventory, 20 requested pHs in [0, 14],
finite pKas in [−1,000, 1,000] and temperatures in [200, 400] K. These wide pKa
bounds permit stable analytic controls; they are not a claim of physical
plausibility. The tool returns `status: error` with a reason on invalid inputs.
`binding_verified` and `pH_selectivity_verified` are always false.
