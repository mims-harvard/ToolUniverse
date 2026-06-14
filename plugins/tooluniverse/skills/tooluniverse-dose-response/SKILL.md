---
name: tooluniverse-dose-response
description: Dose-response / concentration-response curve fitting — IC50, EC50, Hill slope, Emax/Emin efficacy, and relative potency from paired concentration vs response data (enzyme/cell assays, drug screening, agonist/antagonist pharmacology). Fits the 4-parameter logistic (Hill sigmoidal) model. Use when you have concentrations + responses and need a potency value, to compare two compounds' potency, or to judge curve quality. NOT for image-derived dose-response (use tooluniverse-image-analysis) and NOT for survival/regression (use tooluniverse-statistical-modeling).
disable-model-invocation: true
---

# Dose-Response / Concentration-Response Analysis

Turn paired **concentration vs response** measurements into a potency (IC50/EC50), a Hill slope, an efficacy (Emax), and a quality judgment — and compare potency between compounds.

## When to use this

- Enzyme inhibition / activation assays, cell viability, reporter assays, radioligand binding, agonist/antagonist pharmacology.
- You have a list of concentrations and the response at each, and want IC50/EC50 + Hill slope.
- You want to say "compound A is N-fold more potent than B."

The model is the 4-parameter logistic (4PL) / Hill sigmoidal:
`f(x) = Emin + (Emax − Emin) / (1 + (EC50/x)^n)` — where `n` is the Hill slope.

## Step 1 — Prepare the data (where results go wrong)

| Issue | What to do |
|---|---|
| **Concentration units** | Pick ONE unit (µM, nM, M) and use it for every point. The IC50 comes back in that unit. Don't mix. |
| **Log vs linear concentrations** | Pass concentrations on the **linear** scale (e.g. `0.01, 0.1, 1, 10`), not log10. The fitter logs internally. |
| **Zero/control concentration** | Drop a literal `0` concentration (log(0) is undefined). Keep it only as the Emin/Emax reference if normalizing. |
| **Direction** | Inhibition curves go high→low (IC50); activation curves go low→high (EC50). The tools handle both; just be consistent. |
| **Normalization** | Convert raw signal to % of control if you want Emax/Emin near 100/0: `% = 100 × (raw − blank)/(control − blank)`. Raw values also fit, but plateaus are then in raw units. |
| **Replicates** | Average technical replicates per concentration before fitting, or pass all points (the fit weights them equally). |

**Coverage requirement:** you need **≥4 points** (the tools require it) and ideally **6–8 spanning both plateaus** — points clearly above and clearly below the inflection. A curve that never plateaus gives an unreliable, extrapolated IC50 (see Step 4).

## Step 2 — Fit / get the potency

Single curve → IC50 or EC50 (same math; "IC50" for inhibition, "EC50" for activation):

```bash
tu run DoseResponse_calculate_ic50 '{"operation":"calculate_ic50",
  "concentrations":[0.001,0.01,0.1,1,10,100],
  "responses":[98,95,80,45,12,3]}'
```

Returns `ic50`, `ic50_95_confidence_interval`, `hill_slope`, `emax`, `emin`, `r_squared`, `log_ic50`.

Full 4PL parameters only → `DoseResponse_fit_curve` (same inputs). Two compounds → `DoseResponse_compare_potency` with `conc_a/resp_a/conc_b/resp_b` (returns each IC50 + `ic50_fold_shift_b_over_a` + `more_potent`).

For non-standard needs (constrained plateaus, weighting, plotting), `scripts/fit_dose_response.py` runs a scipy 4PL fit from a CSV and matches the tool.

## Step 3 — Interpret the four parameters

| Parameter | Meaning | Sanity check |
|---|---|---|
| **IC50 / EC50** | Concentration giving half-maximal effect — the potency. Lower = more potent. | Should fall *within* your tested range; if it's at/beyond an endpoint, the curve is incomplete (Step 4). |
| **Hill slope `n`** | Steepness / apparent cooperativity. ~1 = simple one-site. >1.5 = steep/positive cooperativity (or non-specific). <0.5 = shallow/multiple sites or heterogeneity. | A wildly large `|n|` (>4) usually means a bad fit or too few transition points, not real cooperativity. |
| **Emax** | Maximal response (top plateau) = efficacy. | For % data, full agonist ≈100; a **partial agonist** plateaus well below 100 even at saturating dose. |
| **Emin** | Bottom plateau (baseline/floor). | For % inhibition data, ≈0 for a complete inhibitor. |
| **r²** | Fit quality. | ≥0.95 good; <0.90 → inspect for outliers, wrong model, or incomplete curve before trusting the IC50. |

**Potency comparison:** report the **fold-shift** in IC50/EC50 (e.g. "A is 6.2× more potent than B"), and only call it meaningful if both fits are good (r²≥0.95) and the Hill slopes are comparable — a potency ratio between curves of very different slope is not a clean comparison.

## Step 4 — Quality gotchas (state these, don't hide them)

- **Incomplete curve / no plateau.** If responses don't flatten at both ends, Emax/Emin (and thus IC50) are extrapolated and unstable. Report the IC50 as "approximate / right-shifted of the tested range" and recommend wider concentrations.
- **<4–5 points or none near the inflection.** The fit can converge to a nonsense IC50 with a high r². Check that points actually bracket the IC50.
- **Biphasic / U-shaped data.** A single 4PL is wrong for hormesis or two-site behavior — the fit will look poor (low r²); flag it rather than forcing one IC50.
- **IC50 vs Ki.** IC50 depends on assay conditions (substrate/ligand concentration). Don't report IC50 as an affinity (Ki) without a Cheng-Prusoff correction.
- **Units.** The IC50 is only as correct as the concentration unit you fed in — always state the unit.

## Honest limitations

- 4PL assumes a monotonic sigmoid; it cannot describe biphasic, bell-shaped, or steep all-or-none responses.
- A confident IC50 from a poor or incomplete curve is the most common error — let r² and curve coverage gate how you report it.
- Potency (IC50/EC50) is not efficacy (Emax) — a more potent compound can be a weaker (partial) agonist; report both.

## Related skills
- `tooluniverse-image-analysis` — dose-response on image-derived measurements (.tif, colony, fluorescence).
- `tooluniverse-gpcr-structural-pharmacology` / `tooluniverse-network-pharmacology` — receptor pharmacology context.
- `tooluniverse-statistical-modeling` — general regression, EC50 via spline, power analysis.
