---
name: tooluniverse-sae-dms-global-validation
description: "Test the foundational question of any DMS × SAE study: do DMS-disruptive substitutions perturb the SAE feature representation more than DMS-neutral ones? Computes per-substitution top-K SAE drop, splits variants into neutral vs disruptive groups by DMS effect, runs a Mann-Whitney U test per assay, sweeps the K and the neutral-band choice for robustness. A positive result is the prerequisite for per-position SAE interpretation."
disable-model-invocation: true
---

# Global SAE drop vs DMS effect

The foundational test for any deep-mutational-scanning × SAE analysis:
do DMS-disruptive substitutions perturb the SAE feature representation more
than DMS-neutral ones? A positive result establishes that the SAE-drop axis
carries DMS signal — the prerequisite for any per-position / per-feature
interpretation downstream.

**Provenance**: Workflow adapted from `dms_analysis/skills/sae_global_drop_vs_dms.md`
and reference scripts `05_validation1_global.py`, `06_validation1_aggregations.py`,
`07_validation1_sweep.py` in [ada-f/esmc_sae](https://github.com/ada-f/esmc_sae)
(Ada Fang, Marinka Zitnik lab).

---

## When to use this skill

- You've built a per-mutant SAE tensor (via `tooluniverse-sae-mutant-tensor-build`)
- You have a DMS effect matrix (via `tooluniverse-mavedb-dms-retrieval`) for
  the same protein
- You want to validate, before any biological interpretation, that the SAE
  is responding to mutational disruptiveness at all

**Not for**:
- Identifying *which* features matter — use `tooluniverse-sae-dms-hotspot-features`
- Single-variant interpretation — use `tooluniverse-protein-sae-variant-interpretation`

---

## Required inputs

| Input | Source | Notes |
|---|---|---|
| `sae_tensor` shape `(20, n_positions, 16384)` | `tooluniverse-sae-mutant-tensor-build` | WT-diagonal NaN |
| `wt_sae_vector` shape `(16384,)` | same skill | WT pooled features |
| `dms_matrix` shape `(20, n_positions)` | `tooluniverse-mavedb-dms-retrieval` | NaN for unmeasured |
| `disruptive_tail` | metadata from DMS retrieval | `"top"` or `"bottom"` |
| `K` | parameter | mean of top-K drops; sweep K ∈ {1, 3, 10} |

---

## Workflow

### Step 1: Compute per-substitution SAE drop

```python
import numpy as np

# Drop = max(0, WT − mutant); only the LOST activation
# Shape: (20, n_positions, 16384)
drops = np.maximum(0.0, wt_sae_vector[None, None, :] - sae_tensor)
```

### Step 2: Top-K aggregation

SAE activations are sparse (k≈64 features active per residue out of 16,384),
so a small top-K (1, 3, 10) is the right summary, not a mean over all
features. Sweep several K and report each — the best K varies by assay and
the choice should be transparent, not tuned.

```python
def topk_drop(drops, K):
    """For each (a, p), take the mean of the K largest feature drops."""
    sorted_desc = -np.sort(-drops, axis=-1)  # shape (20, n_positions, 16384)
    return sorted_desc[:, :, :K].mean(axis=-1)  # shape (20, n_positions)

scores = {K: topk_drop(drops, K) for K in (1, 3, 10)}
```

### Step 3: Define neutral and disruptive categories per assay

```python
def categorize(dms_matrix, disruptive_tail, neutral_abs=0.1, disruptive_quantile=0.05):
    """Returns boolean masks (neutral, disruptive) shape (20, n_positions)."""
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
    # disruptive and neutral must not overlap
    disruptive = disruptive & ~np.isnan(dms_matrix)
    neutral = neutral & ~np.isnan(dms_matrix) & ~disruptive
    return neutral, disruptive
```

**Keep the neutral band tight** (`|effect| ≤ 0.1` or similar). A loose
neutral band leaks weakly-disruptive variants into the "neutral" group and
erodes the contrast.

**Sign matters**. For folding/binding ΔΔG, positive = destabilizing →
disruptive is the **top** tail. For fitness/growth, low = LoF → disruptive
is the **bottom** tail. Get this from the DMS-retrieval skill's metadata; a
flipped sign silently inverts every result.

### Step 4: One-sided Mann-Whitney U test per K

```python
from scipy.stats import mannwhitneyu

neutral_mask, disruptive_mask = categorize(dms_matrix, disruptive_tail)

results = {}
for K, score_matrix in scores.items():
    s_neutral = score_matrix[neutral_mask]
    s_disrupt = score_matrix[disruptive_mask]
    s_neutral = s_neutral[~np.isnan(s_neutral)]
    s_disrupt = s_disrupt[~np.isnan(s_disrupt)]
    u, p = mannwhitneyu(s_disrupt, s_neutral, alternative="greater")
    results[K] = {
        "n_neutral": len(s_neutral),
        "n_disruptive": len(s_disrupt),
        "median_neutral": float(np.median(s_neutral)),
        "median_disruptive": float(np.median(s_disrupt)),
        "u_statistic": float(u),
        "p_value": float(p),
    }
```

### Step 5: Robustness sweep

A single (K, neutral-band, disruptive-quantile) call can pass by chance.
Sweep the grid:

```python
sweep = []
for K in (1, 3, 10):
    for neutral_abs in (0.05, 0.1, 0.2):
        for q in (0.05, 0.1):
            neut, disr = categorize(dms_matrix, disruptive_tail,
                                    neutral_abs=neutral_abs,
                                    disruptive_quantile=q)
            score = topk_drop(drops, K)
            s_n = score[neut][~np.isnan(score[neut])]
            s_d = score[disr][~np.isnan(score[disr])]
            if len(s_n) < 5 or len(s_d) < 5:
                continue
            _, p = mannwhitneyu(s_d, s_n, alternative="greater")
            sweep.append({"K": K, "neutral_abs": neutral_abs,
                          "disruptive_q": q, "p_value": p,
                          "n_n": len(s_n), "n_d": len(s_d)})
```

A result that holds across the grid is robust; one that only passes at a
specific (K, neutral_abs, q) is suspect.

### Step 6: Plot per-K box/strip panels

```python
# matplotlib (optional dep, available via the [visualization] extra)
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
for ax, K in zip(axes, (1, 3, 10)):
    s_n = scores[K][neutral_mask].ravel()
    s_d = scores[K][disruptive_mask].ravel()
    ax.boxplot([s_n[~np.isnan(s_n)], s_d[~np.isnan(s_d)]],
               labels=["neutral", "disruptive"])
    ax.set_title(f"K={K}, p={results[K]['p_value']:.2g}")
axes[0].set_ylabel("SAE feature drop")
plt.tight_layout()
plt.savefig("sae_drop_vs_dms.png", dpi=150)
```

---

## Output

```python
{
    "per_K": {1: {...}, 3: {...}, 10: {...}},  # see Step 4
    "sweep": [...],                              # see Step 5
    "figure": "sae_drop_vs_dms.png",
    "disruptive_tail_used": "bottom",
    "neutral_band": 0.1,
    "disruptive_quantile": 0.05,
}
```

---

## Interpretation

- **Significant result** (p < 0.01 across multiple K): the SAE responds to
  mutational disruptiveness. Necessary foundation for per-position
  interpretation, but **coarse** — any larger functional perturbation moves
  the embedding more, so this alone doesn't show the SAE has captured
  protein-specific biology.
- **Non-significant result**: stop. The downstream per-hotspot enrichment
  will not have a load-bearing signal. Possible causes: DMS sign was
  flipped, neutral band too loose, library is too small / too uniform, or
  the SAE genuinely doesn't track this assay.
- **Significant at K=1 but not K=10 (or vice versa)**: the perturbation is
  concentrated in a few features (K=1 best) or distributed across many
  (K=10 best). Report both; don't tune.

---

## Honest limitations

1. **Foundational, not interpretive**. A pass here means "SAE is sensitive
   to mutation," not "SAE is biologically meaningful for this protein." The
   payload is in `tooluniverse-sae-dms-hotspot-features`.
2. **Pair-wise comparison only**. The neutral-vs-disruptive contrast cannot
   support claims about *how broad* the perturbation is across different
   assays of the same protein; that needs a separate analysis comparing
   disruptive sets directly.
3. **Tail definitions are arbitrary**. The 5% disruptive cutoff and 0.1
   neutral band are reasonable defaults, but the right thresholds depend on
   the assay's signal-to-noise; the sweep is what gives you robustness, not
   any single choice.
4. **Single-protein test**. This does not generalize across proteins; it's
   a per-assay validation.

---

## Cross-references

| Skill | Why |
|---|---|
| `tooluniverse-mavedb-dms-retrieval` | Upstream: DMS effect matrix |
| `tooluniverse-sae-mutant-tensor-build` | Upstream: SAE tensor |
| `tooluniverse-sae-dms-hotspot-features` | Downstream: interpretive payload (only meaningful if this skill passes) |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/sae_global_drop_vs_dms.md`
Reference scripts: `dms_analysis/scripts/05_validation1_global.py`, `06_validation1_aggregations.py`, `07_validation1_sweep.py`
