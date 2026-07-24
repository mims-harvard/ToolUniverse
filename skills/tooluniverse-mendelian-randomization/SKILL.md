---
name: tooluniverse-mendelian-randomization
description: Mendelian randomization (MR) causal inference — does an exposure, risk factor, or biomarker CAUSALLY affect a disease/outcome, using genetic variants as instrumental variables (IEU OpenGWAS / EpiGraphDB MR-EvE). Use this whenever the user asks if X causes Y, whether an observational association is actually causal or just correlation, if a biomarker/trait is a causal risk factor, wants to triangulate epidemiology against genetic evidence, or mentions Mendelian randomization, instrumental-variable analysis, two-sample MR, or genetic causal evidence — even if they never say "MR" (e.g. "is LDL cholesterol actually causal for heart disease?", "does BMI cause type 2 diabetes or just correlate?", "is CRP a causal driver of stroke?"). Covers trait-label resolution, MR effect direction/magnitude, instrument quality (MOE score), method agreement (IVW vs MR-Egger vs weighted median), bidirectional MR for reverse causation, and distinguishing causation from genetic correlation. Not for plain GWAS association lookups (use the GWAS skills) or fitting your own instruments from raw summary statistics.
disable-model-invocation: true
---

# Mendelian Randomization (Causal Inference from Genetic Instruments)

**MR estimates the CAUSAL effect of an exposure on an outcome using genetic variants as instrumental variables.** Because alleles are randomized at conception, MR is largely robust to the confounding and reverse causation that bias observational associations. It is *not* a free lunch: the causal claim rests on three assumptions, and violating them (especially horizontal pleiotropy) silently biases the estimate.

**LOOK UP, DON'T GUESS:** never assert a causal MR estimate from memory. Genetic-instrument results are updated as new GWAS are published — always retrieve current evidence with `EpiGraphDB_get_mendelian_randomization`. Do not invent beta/p-values.

**Correlation ≠ causation, and genetic correlation ≠ causation.** A high genetic correlation (`rg`) means two traits share heritability — it does NOT establish a causal direction. Only MR (with valid instruments) speaks to causality. Report them as different kinds of evidence.

## The three instrumental-variable assumptions

| Assumption | Statement | How it fails | Check |
|---|---|---|---|
| **Relevance** | Instrument is robustly associated with the exposure | Weak instruments (low F-stat) → bias toward the confounded observational estimate | MOE score; instruments selected at GWAS significance |
| **Independence** | Instrument shares no common cause with the outcome | Population stratification, assortative mating | Ancestry-matched GWAS; report population |
| **Exclusion restriction** | Instrument affects the outcome ONLY through the exposure | **Horizontal pleiotropy** — the variant influences the outcome via another path | MR-Egger intercept ≈ 0; agreement across methods |

If you cannot speak to these, your causal claim is provisional. Say so.

## When to use

- "Does **[exposure]** causally affect **[outcome/disease]**?" — the core MR question.
- Triangulating an observational/epidemiological association ("BMI correlates with depression — is it causal?").
- Reverse-causation checks (bidirectional MR: does the outcome cause the exposure instead?).
- Prioritising drug targets / risk factors with genetic causal support.
- Distinguishing a causal driver from a shared-etiology bystander (MR vs genetic correlation).

This skill wraps the **IEU OpenGWAS / EpiGraphDB MR-EvE** ("MR Everything-vs-Everything") resource: a large matrix of pre-computed two-sample MR results between GWAS traits. It does **not** run a bespoke two-sample MR from raw summary statistics with your own instrument set — see *Limitations*.

## Anchor tools

| Tool | Purpose |
|---|---|
| `EpiGraphDB_search_opengwas` | Resolve a free-text trait to exact OpenGWAS study IDs + labels (DO THIS FIRST) |
| `EpiGraphDB_get_mendelian_randomization` | Pre-computed MR estimate(s) for an exposure→outcome trait pair (curated pairs; start here) |
| `OpenGWAS_get_mr_instruments` | Custom two-sample MR: fetch the exposure's clumped instruments + their harmonized outcome effects for *any* GWAS pair (needs a free `OPENGWAS_JWT`). Use when the pair isn't in MR-EvE |
| `EpiGraphDB_get_genetic_correlations` | `rg` between a trait and others (shared etiology, NOT causation). **Sparse** — see Step 4 caveat |
| `EpiGraphDB_get_drugs_for_trait` | Drugs targeting genes associated with a risk-factor trait (causal-target follow-up) |
| `gwas_search_associations` | GWAS Catalog associations, to inspect the instruments behind a trait |

## Workflow

### Step 1 — Resolve trait labels (avoid silent misses)
EpiGraphDB matches GWAS trait labels **exactly and case-sensitively**. Always resolve free text first:

```
EpiGraphDB_search_opengwas {"query": "coronary heart disease"}
# → returns ids like 'ieu-a-7' and the exact label 'Coronary heart disease'
```

Use the returned exact label (or a sentence-case form) in the MR call. The MR tool now retries sentence-case variants and returns a `metadata.note` when it falls back or finds nothing — **read that note**; an empty `mr_results` with a note means "labels didn't match", NOT "no causal effect".

### Step 2 — Run MR (exposure → outcome)
```
EpiGraphDB_get_mendelian_randomization {
  "exposure_trait": "LDL cholesterol",
  "outcome_trait":  "Coronary heart disease",
  "pval_threshold": 1e-5
}
```
Each row carries `beta` (causal effect estimate), `se`, `pval`, `method`, `moescore`, and the exposure/outcome IDs.

### Step 3 — Interpret (see tables below)
Direction, magnitude, instrument quality, and method agreement.

### Step 4 — Triangulate
1. **Bidirectional MR (primary triangulation)** — swap exposure and outcome to test reverse causation. A causal X→Y with no Y→X strengthens the claim; bidirectional signals suggest shared genetics or feedback. This is the reliable leg — lean on it.
2. **Multiple methods** — prefer pairs where IVW and a pleiotropy-robust method (MR-Egger, weighted median) agree in sign and significance.
3. **Genetic correlation (secondary, often empty)** — `EpiGraphDB_get_genetic_correlations` on the exposure. ⚠️ The `/genetic-cor` graph is **sparse**: it stores only strong edges (|rg| > 0.8), matches **exact, case-sensitive** labels distinct from OpenGWAS search labels, and **ignores** the `pval_threshold` argument. Common traits (e.g. 'Body mass index') return empty — that is a graph gap, **not** "no shared genetics." Read `metadata.note`; if empty, do NOT conclude absence — fall back to bidirectional MR. When it does return, high `rg` + significant MR = causal; high `rg` + null MR = shared etiology without a detectable causal path.

### Step 5 — Actionable follow-up (optional)
`EpiGraphDB_get_drugs_for_trait` surfaces drugs whose target genes drive a causal risk factor — a genetics-anchored repurposing hypothesis.

## Interpretation tables

### Causal effect (`beta`)
| Observation | Meaning |
|---|---|
| `beta > 0`, `pval` significant | Higher exposure causally **increases** the outcome (on the GWAS scale — often log-odds for a binary outcome) |
| `beta < 0`, `pval` significant | Higher exposure causally **decreases** the outcome |
| `pval` not significant | No detectable causal effect at the available instrument strength — **absence of evidence, not evidence of absence** |
| Effect on a binary outcome | `beta` is typically a log-odds-ratio; report `exp(beta)` as an odds ratio per SD/unit of exposure |

### Instrument quality (`moescore`, "Mixture of Experts")
| MOE | Confidence |
|---|---|
| > 0.9 | High-quality instrument selection — trust the estimate most |
| 0.6–0.9 | Moderate — corroborate with another exposure GWAS or method |
| < 0.6 | Weak — treat as hypothesis-generating only |

### Method (`method`)
| Method | Note |
|---|---|
| IVW (inverse-variance weighted) | Primary estimate; assumes no pleiotropy |
| MR-Egger | Allows directional pleiotropy; intercept ≠ 0 flags pleiotropy; lower power |
| Weighted median | Valid if ≥50% of instrument weight is from valid variants |
| Disagreement across methods | A red flag for pleiotropy — downgrade confidence |

## Limitations (state these honestly)

- **Two MR paths, different scopes.** `EpiGraphDB_get_mendelian_randomization` returns *pre-computed* MR-EvE estimates for curated trait pairs — fast, but limited to pairs IEU already ran. For a pair that isn't covered, or for custom instruments (your own p-value/clumping thresholds), use `OpenGWAS_get_mr_instruments` (needs a free `OPENGWAS_JWT`) to assemble harmonized exposure+outcome SNP data, then compute the IVW/MR-Egger estimate yourself (e.g. IVW = Σ(βx·βy/σy²)/Σ(βx²/σy²)) or hand the `mr_input` to the `TwoSampleMR` R package. Advanced sensitivity analyses (MR-PRESSO, Steiger, leave-one-out) still need `TwoSampleMR`.
- **Palindromic SNPs** (A/T, C/G) are not strand-resolved by `OpenGWAS_get_mr_instruments`; review or drop ambiguous ones before trusting the estimate.
- **Horizontal pleiotropy** is the dominant threat and cannot be fully excluded from a single estimate. Method agreement reduces but does not eliminate it.
- **Population.** Most OpenGWAS instruments are European-ancestry; effects and LD differ across ancestries. Report this.
- **Winner's curse / weak instruments** bias toward the confounded observational estimate; lean on MOE and instrument F-statistics.
- **Scale.** A statistically significant causal effect may be clinically small. Report magnitude, not just the p-value.
- **One GWAS ≠ truth.** Replication across independent exposure and outcome GWAS strengthens any MR claim.

## Reporting template

> **Causal question:** Does *[exposure]* affect *[outcome]*?
> **MR estimate:** beta = *X* (se *Y*, p = *Z*), method *IVW*, MOE *score* → *[direction + magnitude, OR if binary]*.
> **Triangulation:** bidirectional MR *[reverse effect?]*; genetic correlation rg = *[value]*; method agreement *[yes/no]*.
> **Assumptions/caveats:** instrument quality *[MOE]*, pleiotropy *[Egger intercept / method agreement]*, ancestry *[population]*.
> **Verdict:** *[supported / not supported / inconclusive]* causal effect, with the above caveats.
