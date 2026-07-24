---

name: tooluniverse-pharmacokinetics
description: "Pharmacokinetic (PK) analysis of concentration-time data — non-compartmental analysis (NCA) for Cmax, Tmax, AUC (0-t and 0-∞), terminal half-life, clearance (CL), volume of distribution (Vd), MRT, and absolute bioavailability (F). Also one-compartment fitting. Use when you have plasma/serum drug concentrations over time after a dose and need PK parameters, or to compute bioavailability from IV + oral AUCs. NOT for ADMET property prediction from structure (use tooluniverse-admet-prediction)."
---

# Pharmacokinetic (PK) Analysis — Non-Compartmental Analysis

Turn a **concentration-vs-time** profile after a dose into the standard PK parameters, and compute **bioavailability** from IV + oral data. Non-compartmental analysis (NCA) is the model-independent workhorse used for most PK reporting.

## When to use this

- You have measured plasma/serum (or other matrix) drug concentrations at known times after a dose.
- You need Cmax/Tmax/AUC/half-life/clearance/Vd, or absolute bioavailability F.
- Comparing exposure (AUC, Cmax) between formulations, doses, or routes.

This is **measured-data** PK. For predicting ADMET properties from a chemical structure, use `tooluniverse-admet-prediction`.

## Step 1 — Prepare the concentration-time data

| Issue | What to do |
|---|---|
| **Units — be consistent** | One time unit (h), one concentration unit (mg/L or ng/mL), one dose unit (mg). Pass them as `time_unit`/`conc_unit`/`dose_unit`. CL and Vd come back in derived units (e.g. L/h, L). |
| **Route matters** | Set `route` to `iv` or `po`/oral. CL and Vd are only directly interpretable for **IV** data; from oral data they are **apparent** (CL/F, Vd/F) because absorption is incomplete. |
| **Include t=0** | For IV bolus include the t=0 (back-extrapolated) point; for oral the pre-dose value is usually 0. |
| **BLQ (below limit of quantification)** | Leading BLQs before the first measurable → treat as 0; BLQs in the terminal tail → drop them (don't set to 0, it corrupts the terminal slope). |
| **Sampling design** | You need enough late points to define the terminal phase (≥3 points clearly in the log-linear decline) or the half-life and AUC0-∞ are unreliable. |
| **Single vs multiple dose** | NCA here assumes a single dose. For steady-state, analyze one dosing interval (AUC0-τ) and say so. |

## Step 2 — Run NCA

```bash
tu run NCA_compute_parameters '{
  "times":[0,0.5,1,2,4,8,12,24],
  "concentrations":[0,2.5,4.8,6.1,4.2,2.1,1.0,0.2],
  "dose":100, "route":"iv",
  "dose_unit":"mg", "conc_unit":"mg/L", "time_unit":"h"}'
```

Returns `Cmax`, `Tmax`, `Clast`, `Tlast`, `AUC0_last`, `AUC0-inf`, `AUC_extrapolation_pct`, `lambda_z`, `t_half`, `r_squared_terminal_fit`, `clearance_CL`, `volume_distribution_Vd`, `MRT_iv`, with a `units` block. AUC uses the FDA/EMA **linear-up / log-down trapezoidal** method.

For a CSV profile (with BLQ handling), `scripts/nca_from_csv.py` computes the same parameters locally.

Other tools:
- `NCA_fit_one_compartment` — fit a 1-compartment model (k, V, CL) when you want a parametric model instead of NCA.
- `NCA_calculate_bioavailability` — absolute F from `auc_po`, `dose_po`, `auc_iv`, `dose_iv` (see Step 4).

## Step 3 — Interpret the parameters

| Parameter | Meaning | Notes / sanity |
|---|---|---|
| **Cmax / Tmax** | Peak concentration & time to peak — absorption rate/extent. | For IV bolus Cmax is at t=0; a later Tmax means absorption (oral) or distribution. |
| **AUC0-t / AUC0-∞** | Total exposure (area under the curve). The key exposure metric. | AUC0-∞ extrapolates the tail using `Clast/lambda_z`. |
| **AUC_extrapolation_pct** | % of AUC0-∞ that was extrapolated beyond the last point. | **>20% → AUC0-∞ (and anything derived from it) is unreliable**; report AUC0-last instead and note insufficient sampling. |
| **lambda_z / t_half** | Terminal elimination rate constant and half-life. | Trust only if `r_squared_terminal_fit` ≥ ~0.95 and ≥3 terminal points were used. |
| **CL** (clearance) | Volume cleared per time = `Dose/AUC0-∞` (IV). | From oral data this is **CL/F** (apparent). |
| **Vd** | Volume of distribution = `CL/lambda_z` (IV). | From oral data this is **Vd/F** (apparent). |
| **MRT** | Mean residence time. | Longer MRT = slower overall elimination. |

## Step 4 — Absolute bioavailability (F)

F needs the **same drug given both IV and orally** (ideally same subjects, dose-normalized):

```bash
tu run NCA_calculate_bioavailability '{"auc_po":35.0,"dose_po":200,"auc_iv":43.4,"dose_iv":100}'
```

`F = (AUC_po / Dose_po) / (AUC_iv / Dose_iv)`. Report as a fraction or %. F near 1 = well absorbed; low F = poor absorption or high first-pass metabolism. F > 1 signals a data/dosing error (recheck units and doses).

## Step 5 — Quality gotchas (state these)

- **Extrapolation >20%** → don't report AUC0-∞/CL/Vd as reliable; the profile wasn't followed long enough.
- **Bad terminal fit** (`r_squared_terminal_fit` < 0.9, or <3 tail points) → half-life is unreliable.
- **CL/Vd from oral data are apparent** (CL/F, Vd/F) — never present them as true clearance/volume without IV data.
- **Units** drive CL/Vd — a wrong conc unit silently scales them. Always check the returned `units` block.
- **Flip-flop kinetics** (absorption slower than elimination) makes the "terminal" slope reflect absorption, not elimination — suspect it when oral t½ ≫ IV t½.

## Honest limitations

- NCA is model-independent and robust but gives no mechanistic structure (no separate absorption/distribution rate constants) — use `NCA_fit_one_compartment` or population PK for that.
- AUC accuracy depends entirely on sampling density around Cmax and in the terminal phase.
- Single-dose assumptions; for steady state analyze one interval (AUC0-τ) and accumulation separately.

## Related skills
- `tooluniverse-admet-prediction` — predict ADME properties from structure (no measured data).
- `tooluniverse-dose-response` — IC50/EC50 potency from concentration-response (not time-course).
- `tooluniverse-statistical-modeling` — compare PK parameters across groups.
