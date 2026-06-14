---

name: tooluniverse-enzyme-kinetics
description: "Enzyme kinetics — Michaelis-Menten Km, Vmax, kcat (turnover), and kcat/Km (catalytic efficiency / specificity constant) from substrate-velocity data, plus inhibition-mechanism analysis (competitive / uncompetitive / non-competitive, Ki). Fits the MM equation by nonlinear regression (and reports Lineweaver-Burk for reference). Use when you have substrate concentrations and initial reaction velocities and need kinetic parameters or to classify an inhibitor. NOT for BRENDA database lookups of published constants (use the BRENDA tools)."
---

# Enzyme Kinetics (Michaelis-Menten)

Turn **substrate concentration vs initial velocity** data into Km, Vmax, kcat, and catalytic efficiency — and classify an inhibitor's mechanism.

The Michaelis-Menten model: `v = Vmax·[S] / (Km + [S])`.

## When to use this

- You measured initial reaction rates at several substrate concentrations.
- You need Km (substrate affinity), Vmax, kcat (turnover number), or kcat/Km.
- You have ±inhibitor velocity data and want to classify the inhibition mode + Ki.

For *published* kinetic constants (someone else's Km/kcat), use the BRENDA tools instead — this skill is for analyzing **your own measured** data.

## Step 1 — Prepare the data

| Issue | What to do |
|---|---|
| **Initial velocities, not endpoints** | `v` must be the *initial* rate (linear phase, <10% substrate consumed). Endpoint or plateaued rates give a wrong Km/Vmax. |
| **Substrate range must span Km** | Include `[S]` both well below and well above Km (ideally ~0.2×Km to ~5×Km). Points only above Km can't define Km; only below can't define Vmax. |
| **Units — be consistent** | One `[S]` unit (mM, µM) → Km comes back in that unit. One velocity unit. Keep them fixed. |
| **For kcat you need [E]** | kcat = Vmax / [E]total. The tool's "catalytic_efficiency" is Vmax/Km on the velocity scale; to get true kcat (per-second turnover) and kcat/Km, divide Vmax by the molar enzyme concentration yourself. |
| **≥5–7 points** | Few points → unstable fit. Spread them across the range, not clustered. |

## Step 2 — Fit Michaelis-Menten

```bash
tu run EnzymeKinetics_calculate '{"operation":"michaelis_menten",
  "substrate_concs":[0.1,0.25,0.5,1,2,5,10],
  "velocities":[8.5,18,32,52,72,90,98]}'
```

Returns a `nonlinear_fit` block (`Vmax`, `Km`, `R2`, `SSE`) **— use these as the answer**, a `lineweaver_burk` block (for reference only), `catalytic_efficiency` (Vmax/Km), and `predicted_velocities` + `residuals`.

> **Prefer the nonlinear fit, not Lineweaver-Burk.** The double-reciprocal (Lineweaver-Burk) linearization distorts error (it over-weights low-`[S]` points) and is only for visualization/sanity — never report its Km/Vmax as the final values. The tool gives both; cite `nonlinear_fit`.

`scripts/fit_michaelis_menten.py` does the same nonlinear fit from a CSV and converts Vmax→kcat→kcat/Km when you supply the enzyme concentration.

## Step 3 — Interpret

| Parameter | Meaning | Notes |
|---|---|---|
| **Km** | Substrate concentration at ½Vmax — *apparent affinity* (lower Km = tighter binding / higher affinity). | In the same units as `[S]`. Must lie inside your tested range to be trustworthy. |
| **Vmax** | Maximum velocity at saturating substrate. | Depends on [E]; not an intrinsic enzyme property. |
| **kcat** | Turnover number = Vmax/[E] (per second). | Requires the molar enzyme concentration; intrinsic to the enzyme. |
| **kcat/Km** | Catalytic efficiency / specificity constant. | The best single metric to compare enzymes or substrates; near ~10⁸–10⁹ M⁻¹s⁻¹ is diffusion-limited ("catalytically perfect"). |
| **R² / SSE** | Fit quality. | R²≥0.98 good; check `residuals` for systematic curvature (a pattern, not random scatter, means MM is the wrong model). |

## Step 4 — Inhibition mechanism

Provide velocities ±inhibitor to classify the mode:

```bash
tu run EnzymeKinetics_calculate '{"operation":"inhibition",
  "substrate_concs":[...],
  "velocities_no_inhibitor":[...],
  "velocities_with_inhibitor":[...],
  "inhibitor_conc":5, "inhibition_type":"competitive"}'
```

| Mechanism | Effect on apparent Km | Effect on Vmax | Signature |
|---|---|---|---|
| **Competitive** | ↑ (increases) | unchanged | inhibitor competes at the active site; beatable by more substrate |
| **Uncompetitive** | ↓ (decreases) | ↓ | inhibitor binds only the ES complex |
| **Non-competitive (mixed)** | ~unchanged (pure) / changes (mixed) | ↓ | binds enzyme and ES; not relieved by substrate |

Ki is the inhibition constant (lower = more potent inhibitor). Decide the mechanism from how Km and Vmax shift, not from a single Lineweaver-Burk eyeball.

## Step 5 — Gotchas (state these)

- **Substrate inhibition** (velocity rises then *falls* at high `[S]`) breaks MM — the fit will show systematic residuals; flag it instead of forcing one Km.
- **Km outside the tested range** → unreliable; widen `[S]`.
- **kcat without [E]** is impossible — don't report a turnover number if you only fit velocities.
- **Lineweaver-Burk for final numbers** is the classic error — it's for a quick plot, not the reported Km/Vmax.

## Honest limitations

- MM assumes a single substrate, initial-rate, steady-state, one active site. Allosteric (sigmoidal) enzymes need the Hill equation; multi-substrate enzymes need their own formalism.
- Parameters are only as good as the substrate range and the initial-rate measurement.

## Related skills
- `tooluniverse-dose-response` — IC50/EC50 (the Hill/4PL sibling for concentration-response).
- `tooluniverse-statistical-modeling` — general nonlinear regression and model comparison.
- BRENDA tools — look up *published* enzyme kinetic constants.
