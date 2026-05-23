---
name: tooluniverse-variant-predictor-dms-benchmarking
description: "Validate a variant-effect predictor (AlphaMissense, ESM-C SAE, ESM logits, EVE, conservation scores, or any per-variant numeric score) against experimental deep mutational scanning (DMS) data. Computes per-variant predictor scores, splits variants into neutral vs disruptive groups by DMS effect, runs a Mann-Whitney U test on the predictor scores, and sweeps the stratification thresholds for robustness. Use when you need to know whether a predictor's scores track real functional disruption on a specific protein."
disable-model-invocation: true
---

# Variant-effect predictor benchmarking against DMS

The core user question: **"I have a variant-effect predictor — does it actually
correlate with experimental DMS measurements on this protein?"**

The predictor can be anything that assigns a numeric score to single missense
variants:
- ESM-C 6B Sparse Autoencoder (SAE) feature drops at the mutation site
- AlphaMissense pathogenicity scores
- ESM logits-based variant scoring (`ESM_score_sequence`)
- EVE / EVE++ scores
- Conservation scores (ConSurf, Rate4Site)
- DynaMut2 ΔΔG predictions
- A custom in-house model

This skill validates ALL of these against a DMS dataset with the same statistical
framework. SAE is shown as the worked example because the surrounding skills in
this collection are SAE-themed, but the procedure is predictor-agnostic.

**Provenance**: Statistical methodology adapted from
`dms_analysis/skills/sae_global_drop_vs_dms.md` in
[ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka Zitnik lab).
Reference: `05_validation1_global.py`, `06_validation1_aggregations.py`,
`07_validation1_sweep.py`.

---

## When to use this skill

- You picked a variant-effect predictor and want to know if it's worth trusting
  on your protein of interest
- You're comparing two predictors on the same DMS dataset (run this skill twice,
  compare the resulting per-K Mann-Whitney U p-values + effect sizes)
- Reviewers want robustness evidence — the parameter sweep (K, neutral band,
  disruptive quantile) is exactly that
- You're publishing a new variant-effect method and need a benchmark figure

**Not for**:
- Per-position / per-feature interpretation — use
  `tooluniverse-dms-hotspot-mechanism-interpretation`
- Single-variant interpretation (you have one variant, no DMS) — use
  `tooluniverse-protein-sae-variant-interpretation` or
  `tooluniverse-protein-lof-mechanism`
- Building a predictor from scratch — out of scope

---

## Required inputs

| Input | Format | Example |
|---|---|---|
| DMS effect matrix | (20 amino acids × n_positions) `np.array`, NaN for unmeasured | from `tooluniverse-mavedb-dms-retrieval` |
| Disruptive tail convention | `"top"` (ΔΔG positive = destabilizing) or `"bottom"` (fitness low = LoF) | metadata from DMS retrieval step |
| Per-variant predictor scores | (20 × n_positions) `np.array` matching DMS layout | computed from your chosen predictor — see Step 2 |
| Aggregation K | `int`, mean of top-K when the predictor outputs many sub-scores per variant | only relevant for multi-feature predictors like SAE; ignore otherwise |

---

## Workflow

### Step 1: Retrieve DMS

```python
# Pulls all variants in one call after the MaveDB-pagination fix
MaveDB_get_variant_scores(urn="urn:mavedb:00000115-a-7")
```

Then parse + reshape into the (20 × n_positions) matrix as documented in
`tooluniverse-mavedb-dms-retrieval`.

### Step 2: Compute per-variant predictor scores

Pick **one** of these predictor sources. The choice changes Step 2 only; Steps
3–5 are identical.

#### Predictor option A — ESM-C 6B SAE (the worked example)

For every variant, call `ESM_get_sae_features` with WT and mutant sequences,
sum activations across the residue window, compute drop = max(0, WT − mut),
and aggregate to one score per variant via the top-K mean of drops:

```python
import numpy as np

def sae_drop_per_variant(wt_pooled, variant_pooled, K=3):
    """SAE drop for one variant = mean of the K largest feature drops."""
    drops = np.maximum(0.0, wt_pooled - variant_pooled)  # (n_features,)
    sorted_desc = -np.sort(-drops)
    return float(sorted_desc[:K].mean())
```

Build the (20, n_positions) predictor matrix by looping mutants. The expensive
step is the `ESM_get_sae_features` calls — cache by `(sequence, position)`
to make reruns free. The full library scale is well-tested:
`tests/integration/test_dms_pipeline_e2e_kras.py` runs ~300 mutants for KRAS
positions 10–25.

#### Predictor option B — AlphaMissense

```python
# AlphaMissense gives 0-1 pathogenicity score per missense variant
AlphaMissense_get_variant_score(
    uniprot_accession="P01116",
    position=12,
    reference_amino_acid="G",
    alternate_amino_acid="V",
)
```

Looped over the DMS variant list to populate the (20, n_positions) matrix.
Free, no API key required.

#### Predictor option C — ESM logits-based score

```python
ESM_score_sequence(
    sequence=mutant_sequence,
    model="esmc-600m-2024-12",
)
# returns per-residue logits; compute mutant-vs-WT log-odds at the mutation site
```

#### Predictor option D — any external score

Bring your own. Just produce a `(20, n_positions)` `np.ndarray` aligned to the
DMS matrix.

### Step 3: Stratify DMS into neutral vs disruptive

```python
def categorize(dms_matrix, disruptive_tail, neutral_abs=0.1, disruptive_quantile=0.05):
    """Split variants into neutral and disruptive masks.

    disruptive_tail: 'top' (positive = destabilizing, e.g. folding ΔΔG)
                     'bottom' (low = LoF, e.g. fitness)
    """
    flat = dms_matrix[~np.isnan(dms_matrix)]
    if disruptive_tail == "top":
        cut = np.quantile(flat, 1 - disruptive_quantile)
        disruptive = dms_matrix >= cut
    elif disruptive_tail == "bottom":
        cut = np.quantile(flat, disruptive_quantile)
        disruptive = dms_matrix <= cut
    else:
        raise ValueError("disruptive_tail must be 'top' or 'bottom'")
    neutral = np.abs(dms_matrix) <= neutral_abs
    disruptive = disruptive & ~np.isnan(dms_matrix)
    neutral = neutral & ~np.isnan(dms_matrix) & ~disruptive
    return neutral, disruptive
```

**Keep the neutral band tight** (`|effect| ≤ 0.1`). A loose neutral band leaks
weakly-disruptive variants into the "neutral" group and erodes the contrast.
**Sign matters** — get `disruptive_tail` from the DMS-retrieval skill's metadata;
a flipped sign silently inverts every conclusion.

### Step 4: One-sided Mann-Whitney U test

```python
from scipy.stats import mannwhitneyu

neutral, disruptive = categorize(dms_matrix, disruptive_tail)
s_neutral = predictor_scores[neutral][~np.isnan(predictor_scores[neutral])]
s_disruptive = predictor_scores[disruptive][~np.isnan(predictor_scores[disruptive])]

u, p = mannwhitneyu(s_disruptive, s_neutral, alternative="greater")
print(f"disruptive median = {np.median(s_disruptive):.4f}, "
      f"neutral median = {np.median(s_neutral):.4f}, p = {p:.3g}")
```

For SAE-style multi-feature predictors with a top-K parameter, run this for
K ∈ {1, 3, 10} and report all three — the best K is usually different across
predictors and you want the comparison transparent, not tuned.

### Step 5: Robustness sweep

```python
sweep = []
for neutral_abs in (0.05, 0.1, 0.2):
    for q in (0.05, 0.1):
        neut, disr = categorize(dms_matrix, disruptive_tail,
                                neutral_abs=neutral_abs,
                                disruptive_quantile=q)
        s_n = predictor_scores[neut][~np.isnan(predictor_scores[neut])]
        s_d = predictor_scores[disr][~np.isnan(predictor_scores[disr])]
        if len(s_n) < 5 or len(s_d) < 5:
            continue
        _u, p = mannwhitneyu(s_d, s_n, alternative="greater")
        sweep.append({"neutral_abs": neutral_abs, "disruptive_q": q, "p": p,
                      "n_n": len(s_n), "n_d": len(s_d)})
```

A predictor that passes only at one (neutral_abs, q) point is suspect. A
predictor that passes across the grid is robust.

### Step 6: Visualize + interpret

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(4, 4))
ax.boxplot(
    [s_neutral, s_disruptive],
    labels=[f"neutral (n={len(s_neutral)})", f"disruptive (n={len(s_disruptive)})"]
)
ax.set_ylabel("Predictor score")
ax.set_title(f"p = {p:.3g}")
plt.tight_layout()
plt.savefig("predictor_vs_dms.png", dpi=150)
```

---

## Interpretation

| Result | What it means |
|---|---|
| **p < 0.01 AND robust across sweep** | Predictor reliably distinguishes disruptive from neutral on this protein. Safe to use for prioritization (not classification — see limits) |
| **p < 0.05 but flips signs in sweep** | Borderline. Effect exists but is sensitive to stratification — needs more data or tighter neutral band |
| **p > 0.05** | Predictor is not informative on this DMS assay. Possible causes: wrong `disruptive_tail`, predictor mis-calibrated for this protein family, DMS measures something the predictor wasn't trained for |
| Significant **at K=1 but not K=10** (multi-feature predictors only) | Disruption is concentrated in a few features (K=1 best) vs distributed across many (K=10) |

---

## Comparing two predictors

Run this skill twice on the same DMS dataset (e.g. SAE drops AND AlphaMissense),
keep the same stratification (`disruptive_tail`, `neutral_abs`, `disruptive_quantile`),
and compare:

| Metric | Better predictor has |
|---|---|
| Lower p-value | More confidence of discrimination |
| Larger median gap (disruptive − neutral) | Larger effect size |
| Fewer NaNs in coverage | Predicts more variants |
| Robust across sweep | More reliable in different conditions |

---

## Honest limitations

1. **Per-protein test only**. Generalizing "predictor X is good" requires running
   this on multiple proteins from different families.
2. **Per-assay only**. A predictor calibrated for stability might fail on
   binding-fitness assays — same protein, different DMS, different result.
3. **Coarse signal**. This says "predictor responds to mutational disruptiveness."
   It does NOT say "predictor identifies the *right* residues" — for that, run
   `tooluniverse-dms-hotspot-mechanism-interpretation`.
4. **MWU assumes independence**. DMS variants at the same position are mildly
   correlated (shared structural context); the p-values are slightly optimistic.
5. **Tail definitions are arbitrary**. 5% disruptive cutoff and 0.1 neutral band
   are reasonable defaults; the right thresholds depend on the assay's
   signal-to-noise. The sweep is what gives you robustness, not any single choice.

---

## Cross-references

| Step | Tool / Skill |
|---|---|
| DMS retrieval | `tooluniverse-mavedb-dms-retrieval` |
| Per-variant SAE scoring | `ESM_get_sae_features`, `ESM_score_variant_sae_disruption` |
| Per-variant AlphaMissense | `AlphaMissense_get_variant_score` |
| Per-variant ESM logits | `ESM_score_sequence` |
| Structural prior (for predictor analysis) | `Structure_annotate_per_residue` |
| Next step: per-hotspot mechanism | `tooluniverse-dms-hotspot-mechanism-interpretation` |
| Final visualization | `tooluniverse-annotated-dms-heatmap` |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/sae_global_drop_vs_dms.md`
Reference scripts: `dms_analysis/scripts/05_validation1_global.py`, `06_validation1_aggregations.py`, `07_validation1_sweep.py`
