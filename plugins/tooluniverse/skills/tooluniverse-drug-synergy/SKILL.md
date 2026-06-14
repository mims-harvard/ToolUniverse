---
name: tooluniverse-drug-synergy
description: Drug-combination synergy analysis — quantify whether two drugs together are synergistic, additive, or antagonistic using the standard reference models (Bliss independence, HSA / highest single agent, Loewe additivity, ZIP, and the Chou-Talalay Combination Index). Use when you have measured single-drug and combination effects (inhibition/viability) and need a synergy score. Explains which model to use, what data each one needs, and how to read the score. NOT for looking up pre-computed synergy in a database (use the SYNERGxDB tool / cell-line-profiling skill).
disable-model-invocation: true
---

# Drug-Combination Synergy Analysis

Decide whether a two-drug combination does **more than expected** (synergy), exactly as expected (additivity), or **less** (antagonism) — and pick the right reference model for the data you have.

"Synergy" only means something relative to a **null model of additivity**, and the models define additivity differently — so the first decision is *which model*, driven by *what data you measured*.

## Step 0 — Pick the model by the data you have

| You measured… | Use model | Tool | Input |
|---|---|---|---|
| Single effects of A, B, and A+B at **one** dose pair | **Bliss** | `DrugSynergy_calculate_bliss` | `effect_a`, `effect_b`, `effect_combination` (each a fraction 0–1) |
| Effects of A, B, A+B across **several** dose points | **HSA** | `DrugSynergy_calculate_hsa` | `effects_a`, `effects_b`, `effects_combo` (arrays) |
| Single-agent **dose-response curves** + one combination point | **Loewe** | `DrugSynergy_calculate_loewe` | `doses_a_single`/`effects_a_single`, `doses_b_single`/`effects_b_single`, `dose_a_combo`, `dose_b_combo`, `effect_combo` |
| Single-agent dose-response + combo point, want Chou-Talalay CI | **Combination Index** | `DrugSynergy_calculate_ci` | same as Loewe + `assumption` |
| A full **dose × dose viability matrix** | **ZIP** | `DrugSynergy_calculate_zip` | `doses_a`, `doses_b`, `viability_matrix` (% , 0–100) |

> **Effects must be on a consistent inhibition scale.** Bliss/HSA/Loewe expect *fractional inhibition* `0–1` (0 = no effect, 1 = complete kill). If your data is % viability, convert: `inhibition = 1 − viability/100`. ZIP takes the viability matrix in % directly. Mixing scales is the most common error.

## Step 1 — What each model's "additivity" means

| Model | Null (additive) expectation | Best when |
|---|---|---|
| **Bliss independence** | drugs act independently: `E_exp = E_a + E_b − E_a·E_b` | different mechanisms; quick single-point screen |
| **HSA (highest single agent)** | combo should beat the *better* single agent: `E_exp = max(E_a, E_b)` | conservative "does it beat monotherapy?" question |
| **Loewe additivity** | a drug combined with itself = additive (dose equivalence) | same/similar mechanism; needs dose-response |
| **ZIP** | combines Bliss + Loewe; potency shift of one drug's curve by the other | dose-matrix screens (the SynergyFinder default) |
| **Chou-Talalay CI** | CI<1 synergy, =1 additive, >1 antagonism (median-effect) | classic isobologram-style analysis with dose-response |

There is no single "correct" model — **state which one you used.** Bliss and Loewe genuinely disagree for some combinations (that's expected, not an error); reporting two models (e.g. Bliss + HSA, or Loewe + ZIP) is good practice.

## Step 2 — Run it

```bash
# Bliss (single dose pair, fractional inhibition)
tu run DrugSynergy_calculate_bliss '{"operation":"calculate_bliss",
  "effect_a":0.4,"effect_b":0.3,"effect_combination":0.7}'
# -> expected 0.58, bliss_synergy_score 0.12, "Strong synergy"
```

`scripts/synergy_reference.py` computes the Bliss, HSA, and Loewe-style expected combination effects side-by-side from one dose pair, so you can see at a glance whether the models agree before running the full tools.

## Step 3 — Interpret the score

For Bliss/HSA/Loewe/ZIP, the synergy score is `(observed − expected)` (often ×100):

| Score (fractional, ×100 scale) | Call |
|---|---|
| > +10 | synergy |
| −10 to +10 | additive (no meaningful interaction) |
| < −10 | antagonism |

For **Combination Index (Chou-Talalay)**: **CI < 1 = synergy**, CI = 1 additive, CI > 1 antagonism (note the opposite direction — lower is more synergistic).

- A positive Bliss/HSA score means the combination exceeds the additive expectation at that point.
- Synergy is often **dose-dependent** — a combination can be synergistic at one ratio and antagonistic at another; for a matrix, report the synergistic *region*, not one number.

## Step 4 — Gotchas (state these)

- **Scale mismatch** (% viability vs fractional inhibition) — convert first (Step 0).
- **Effects near 0 or 1 (ceiling).** If both single agents already kill ~everything, the combo can't show synergy (no headroom) — Bliss/HSA saturate; interpret with care.
- **ZIP/Loewe/CI need real dose-response** with ≥3 non-zero, measurable-effect dose points per drug, or the Hill fit fails (the tools say so).
- **Model disagreement is normal** — don't shop for the model that gives "synergy"; pre-specify the model and report it.
- **A synergy score is not efficacy** — a strongly synergistic combination can still be weak overall; report the absolute combination effect too.

## Honest limitations

- These are *reference-model* synergy scores, not statistical tests — for confidence, replicate and report variability across the dose matrix.
- Synergy in vitro does not guarantee clinical benefit (PK/PD, toxicity, scheduling all matter).

## Related skills
- `tooluniverse-dose-response` — fit the single-agent IC50/EC50 curves that Loewe/CI/ZIP need.
- `tooluniverse-cell-line-profiling` — look up *pre-computed* combination synergy (SYNERGxDB).
- `tooluniverse-drug-repurposing` / `tooluniverse-network-pharmacology` — rationale for combinations.
