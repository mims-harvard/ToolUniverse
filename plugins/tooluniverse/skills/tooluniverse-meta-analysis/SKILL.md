---
name: tooluniverse-meta-analysis
description: Meta-analysis / evidence synthesis — pool effect sizes across studies (odds ratios, risk ratios, hazard ratios, mean differences, correlations, GWAS betas) with fixed- or random-effects models, quantify heterogeneity (Q, I², τ²), and build a forest plot. Use when you have results from MULTIPLE studies and need a single pooled estimate, or to synthesize evidence from a systematic review / multiple GWAS / replicated experiments. Handles the error-prone effect-size + standard-error preparation (converting OR/HR/CI, two-group means±SD, proportions, and correlations into the (effect, SE) the pooling step needs).
disable-model-invocation: true
---

# Meta-Analysis & Evidence Synthesis

Pool quantitative results from **multiple studies** into one estimate, and judge how consistent the studies are. This is the statistical half of a systematic review (the literature-collection half is `tooluniverse-literature-deep-research`).

## When to use this

- You have effect sizes from ≥2 studies/cohorts and want a single pooled estimate + CI.
- Synthesizing a systematic review, replicated experiments, multi-cohort GWAS, or multi-dataset associations.
- Deciding whether studies agree (low heterogeneity) or conflict (high heterogeneity).

Do NOT use it to *find* the studies — use `tooluniverse-literature-deep-research` / the literature tools for that, then bring the extracted numbers here. Before trusting any input study, consider checking it with `Crossref_check_retraction`.

## The workflow

```
1. Extract (effect, SE) per study  ← THE ERROR-PRONE STEP
2. Pick fixed vs random effects
3. Pool: MetaAnalysis_run
4. Read heterogeneity (I², Q, τ²)
5. Forest plot + interpret
```

## Step 1 — Convert each study to (effect_size, se)  ← do this carefully

The pooling step needs an **effect size on an additive scale** and its **standard error**. Ratio measures (OR/RR/HR) must be **log-transformed** first. Most reported numbers give you a CI, not an SE — derive the SE from the CI.

| What the paper reports | effect_size | se |
|---|---|---|
| OR / RR / HR with 95% CI `[L, U]` | `ln(point)` | `(ln(U) − ln(L)) / (2 × 1.96)` |
| OR / RR / HR with a p-value (no CI) | `ln(point)` | `|ln(point)| / z_from_p` (two-sided `z`) |
| GWAS / regression `β` with SE | `β` (as reported) | the reported SE |
| Two groups, means + SDs + n₁,n₂ | Hedges' g (see script) | SE of g (see script) |
| Single proportion `p`, n | `logit(p)=ln(p/(1−p))` | `sqrt(1/(np) + 1/(n(1−p)))` |
| Pearson correlation `r`, n | Fisher `z = atanh(r)` | `1 / sqrt(n − 3)` |

**Critical rules**
- **Log-transform ratio measures.** Pooling raw ORs is wrong; pool `ln(OR)` and exponentiate the pooled result back. The script does this for you.
- **One direction.** Make sure every study's effect points the same way (e.g. "exposure increases risk"); flip sign / invert the ratio for studies coded the opposite way.
- **Same effect measure.** Don't mix OR with HR with mean-difference in one pool.
- `2 × 1.96` assumes a 95% CI; use `2 × 1.645` for 90%, `2 × 2.576` for 99%.

The helper script does these conversions — prefer it over hand math:

```bash
python skills/tooluniverse-meta-analysis/scripts/meta_analysis.py --input studies.csv
# studies.csv columns (use the set that matches your data):
#   name, or, ci_low, ci_high            (ratio + CI)
#   name, beta, se                       (already on log/linear scale)
#   name, mean1, sd1, n1, mean2, sd2, n2 (two-group means -> Hedges' g)
#   name, r, n                           (correlation -> Fisher z)
```

## Step 2 — Fixed vs random effects

| Use **fixed-effects** when | Use **random-effects** when |
|---|---|
| Studies estimate the *same* true effect (e.g. exact replications, one trial split by site) | Studies differ in population/design/dose (the usual real-world case) |
| I² is low (<25%) | I² is moderate–high, or studies are clinically heterogeneous |

When unsure, **report random-effects** (DerSimonian–Laird) as primary — it is the conservative default and widens the CI to reflect between-study variance.

## Step 3 — Pool with MetaAnalysis_run

```bash
tu run MetaAnalysis_run '{"method":"random","studies":[
  {"name":"Smith 2019","effect_size":0.41,"se":0.12},
  {"name":"Lee 2021","effect_size":0.67,"se":0.18},
  {"name":"Garcia 2023","effect_size":0.33,"se":0.10}]}'
```

Returns `pooled_effect`, `pooled_se`, `pooled_ci_lower/upper`, `pooled_z`, `pooled_p_value`, a `heterogeneity` block (`Q`, `Q_df`, `Q_p_value`, `I_squared`, `tau_squared`), and `per_study` weights + CIs.

> **Scale foot-gun — read this.** `MetaAnalysis_run` pools *whatever scale you hand it* and has no idea your inputs were ratios. For an OR/RR/HR you MUST pass the **log-transformed** `effect_size` + `se` from Step 1 (e.g. `ln(1.42)=0.351`, not `1.42`) — feeding raw ratios silently produces a wrong pooled value with no error. And the values it returns — including its prose `interpretation` string — are on that **same log scale**. So: **ignore the tool's `interpretation` field for ratios, and `exp()` the `pooled_effect` and CI bounds back to the OR/RR/HR scale yourself before reporting.** The helper script avoids all of this — it takes raw ORs, tracks the scale, and prints results already back-transformed.

## Step 4 — Interpret heterogeneity (decides the story)

| I² | Heterogeneity | What it means |
|---|---|---|
| 0–25% | Low | Studies largely agree; fixed-effects is defensible |
| 25–50% | Moderate | Prefer random-effects; note the variability |
| 50–75% | Substantial | Random-effects; investigate sources (subgroup / meta-regression) |
| >75% | Considerable | Pooling may be inappropriate — explain *why* studies differ instead |

- `Q_p_value < 0.10` → statistically significant heterogeneity (Q is low-powered, so 0.10 not 0.05).
- `tau_squared` is the between-study variance on the effect scale; `> 0` is what random-effects adds over fixed.
- **Borderline I² (≈25–50%) with a non-significant Q (`Q_p_value ≫ 0.10`), especially with few studies:** fixed and random-effects converge — report **random-effects as primary** and note that fixed-effects agrees. Don't agonize over the model choice when both give essentially the same pooled estimate.

## Step 5 — Forest plot + report

The script prints a text forest plot (per-study effect, CI, weight%, and the pooled diamond). Report, in order:
1. Pooled estimate + 95% CI + p (on the **interpretable** scale — exponentiate ratios back).
2. Number of studies and total N.
3. Heterogeneity: I² + Q p-value + the model you chose and why.
4. Direction/consistency: do all studies point the same way?

> Example: "Across 3 cohorts (N=4,210), the pooled OR was 1.51 (95% CI 1.33–1.72, p=3.4×10⁻⁶), random-effects. Heterogeneity was substantial (I²=55%, Q p=0.11), so the random-effects model is reported; all three studies showed the same direction of effect."

## Honest limitations

- **Garbage in, garbage out.** Meta-analysis cannot fix biased primary studies; check input study quality (and retraction status via `Crossref_check_retraction`) first.
- **Publication bias.** A pooled estimate from only published studies is likely inflated. With ≥10 studies, inspect a funnel plot / Egger's test (the script notes this); with <10, state that small-study bias cannot be assessed.
- **Ecological / aggregation issues.** Pooling study-level summaries is not the same as pooling individual patient data.
- **Don't over-pool.** With I²>75% and clinically different studies, a single number can mislead — describe the variation instead.

## Related skills
- `tooluniverse-literature-deep-research` — find and grade the studies to feed in.
- `tooluniverse-statistical-modeling` — single-study regression, Cox, ORs (see `references/cox_regression.md` for HR extraction).
- `tooluniverse-gwas-study-explorer` / `tooluniverse-gwas-finemapping` — GWAS-specific multi-cohort analysis.
