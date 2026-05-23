---
name: tooluniverse-sae-dms-hotspot-features
description: "At the loss-of-function (LoF) hotspots of a DMS map, identify which SAE features the mutations most disrupt — as a permutation-tested shortlist and a plain descriptive ranking — and label them via ESM_describe_sae_feature. Output is a per-hotspot 'callout' of SAE features that should reflect the protein's known biology (its domains, motifs, catalytic/binding residues). The interpretive payload of the SAE-vs-DMS workflow."
disable-model-invocation: true
---

# SAE features dropped at DMS hotspots

At the loss-of-function (LoF) hotspots of a DMS map, identify *which* SAE
features mutations most disrupt. This is the **interpretive payload** of the
SAE-vs-DMS workflow — after `tooluniverse-sae-dms-global-validation` confirms
the SAE responds to disruptiveness at all, this skill answers "*which*
features, and *where*".

**Provenance**: Workflow adapted from `dms_analysis/skills/sae_hotspot_feature_enrichment.md`
and reference scripts `08_validation2_hotspot_enrichment.py`,
`09_validation2_descriptive.py`, `10_validation2_plot_callouts.py` in
[ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka
Zitnik lab).

---

## When to use this skill

- `tooluniverse-sae-dms-global-validation` passed (p<0.01 across multiple K)
  — only then is the per-hotspot signal load-bearing
- You want to know "at KRAS hotspot G12, which SAE features lose the most
  activation, and what biology do they represent?"
- You're writing the figure that places per-hotspot feature callouts next
  to the structural annotation

**Not for**:
- Whole-protein-level statistics — use `tooluniverse-sae-dms-global-validation`
- Single-variant interpretation — use `tooluniverse-protein-sae-variant-interpretation`

---

## Required inputs

| Input | Source | Notes |
|---|---|---|
| `sae_tensor` shape `(20, n_positions, 16384)` | `tooluniverse-sae-mutant-tensor-build` | WT-diagonal NaN |
| `wt_sae_vector` shape `(16384,)` | same | |
| `dms_matrix` shape `(20, n_positions)` | `tooluniverse-mavedb-dms-retrieval` | |
| `disruptive_tail` | DMS metadata | `"top"` or `"bottom"` |
| top-K hotspot positions | parameter | typical: 10-20 |
| `n_permutations` | parameter | 10,000 default |

---

## Workflow

### Step 1: Per-position drop statistic

For each position, take the **biggest drop any substitution at that position
causes in each feature**:

```python
import numpy as np

# drops: (20, n_positions, 16384)
drops = np.maximum(0.0, wt_sae_vector[None, None, :] - sae_tensor)

# Collapse over alleles (take max per feature, per position)
# Skip NaN cells (WT diagonal, unmeasured)
max_drop = np.nanmax(drops, axis=0)  # shape (n_positions, 16384)
```

### Step 2: Hotspot clusters

Take the top-K positions by max DMS effect; chain adjacent ones (gap ≤ 2)
into domain-level clusters:

```python
# Per-position DMS effect magnitude
if disruptive_tail == "top":
    dms_per_pos = np.nanmax(dms_matrix, axis=0)
elif disruptive_tail == "bottom":
    dms_per_pos = -np.nanmin(dms_matrix, axis=0)

K = 20
top_positions = sorted(np.argsort(-dms_per_pos)[:K])  # sorted ascending

# Chain adjacent positions (gap ≤ 2) into clusters
clusters = []
current = [top_positions[0]]
for p in top_positions[1:]:
    if p - current[-1] <= 2:
        current.append(p)
    else:
        clusters.append(current)
        current = [p]
clusters.append(current)

# Keep top clusters by within-cluster max effect
clusters = sorted(clusters,
                  key=lambda c: max(dms_per_pos[p] for p in c),
                  reverse=True)[:5]
```

### Step 3: Permutation test per cluster, per feature

```python
def permutation_pvalues(cluster_positions, max_drop, n_perm=10000, rng=None):
    """For each feature, observed = mean(max_drop[cluster, f]),
    null = same statistic on random equally-sized sets of positions.
    Returns array of empirical p-values, shape (16384,).
    """
    rng = rng or np.random.default_rng(0)
    n_positions = max_drop.shape[0]
    cluster_size = len(cluster_positions)
    observed = max_drop[cluster_positions].mean(axis=0)  # shape (16384,)

    null_geq = np.zeros(16384, dtype=np.int32)
    for _ in range(n_perm):
        idx = rng.choice(n_positions, size=cluster_size, replace=False)
        null_stat = max_drop[idx].mean(axis=0)
        null_geq += (null_stat >= observed).astype(np.int32)
    return (null_geq + 1) / (n_perm + 1)

# Per-cluster
from statsmodels.stats.multitest import multipletests

cluster_features = {}
for ci, cluster in enumerate(clusters):
    p_raw = permutation_pvalues(np.array(cluster), max_drop, n_perm=10000)
    _, p_adj, _, _ = multipletests(p_raw, method="fdr_bh")
    sig_features = np.where(p_adj < 0.05)[0].tolist()
    cluster_features[ci] = {
        "positions": cluster,
        "p_raw": p_raw,
        "p_adj": p_adj,
        "significant_features": sig_features,
    }
```

**Why mean, not max**: under this null a maximum-based statistic returns
almost no significant features. Use `mean(max_drop)`.

**Why include the cluster in the null pool**: excluding the cluster's own
positions from the null biases the test toward significance.

### Step 4: Descriptive ranking (fast complement)

Independently of the test, rank features by raw `mean(max_drop)` across each
cluster — the fast "what drops most here" view. Don't conflate descriptive
ranking with statistical significance.

```python
descriptive = {}
for ci, cluster in enumerate(clusters):
    cluster_mean = max_drop[np.array(cluster)].mean(axis=0)
    top5_features = np.argsort(-cluster_mean)[:5].tolist()
    descriptive[ci] = {
        "positions": cluster,
        "top5_features": top5_features,
        "top5_mean_drops": [float(cluster_mean[f]) for f in top5_features],
    }
```

### Step 5: Label features via ESM_describe_sae_feature

For each shortlisted feature, call the labeling tool to attach category +
summary:

```python
def label_features(feature_ids):
    labels = {}
    for fid in feature_ids:
        r = ESM_describe_sae_feature(feature_id=int(fid))
        if r.get("status") == "success":
            labels[fid] = {
                "category": r["data"].get("category"),
                "summary": r["data"].get("summary"),
                "votes": r["data"].get("vote_distribution"),
            }
        else:
            labels[fid] = {"error": r.get("error")}
    return labels

# Apply to permutation-significant features
for ci, info in cluster_features.items():
    info["labels"] = label_features(info["significant_features"][:10])

# And to descriptive top-5
for ci, info in descriptive.items():
    info["labels"] = label_features(info["top5_features"])
```

The first call for each new feature is slow (~30s, ~10 Forge credits as the
labeling tool runs SAE on its 10-protein curated panel); subsequent calls
hit the local cache and are instant.

### Step 6: Read against the cluster's known structural role

If you have a structural annotation (from `tooluniverse-protein-structural-annotation-pdb`),
check that the labeled features at each cluster line up with the cluster's
biology: a hotspot in the GTP pocket should call ligand-binding features; a
hotspot at the protein-protein interface should call interface features.

---

## Output

```python
{
    "clusters": [...],  # list of position lists
    "permutation": {
        cluster_id: {
            "positions": [...],
            "p_raw": [...],
            "p_adj": [...],
            "significant_features": [...],
            "labels": {feature_id: {category, summary, votes}},
        }
    },
    "descriptive": {
        cluster_id: {
            "positions": [...],
            "top5_features": [...],
            "top5_mean_drops": [...],
            "labels": {...},
        }
    },
    "n_permutations": 10000,
    "fdr_method": "benjamini_hochberg",
}
```

---

## Interpretation

A good result calls features whose labels **match the known biology of the
cluster's residues**:

- KRAS G12/G13 cluster → ligand-binding / P-loop features
- TP53 R175/R273 cluster → DNA-binding / Zn-coordination features
- Protein-protein interface hotspot → interface / surface-recognition features

If the labels don't match, possibilities:
1. Cluster size = 1 — permutation test has no power; rely on descriptive
   ranking
2. Cluster spans multiple sub-regions with different biology — split it
3. Feature labels are uncategorized for these features — use the raw
   `vote_distribution` from `ESM_describe_sae_feature`

---

## Honest limitations

1. **Single-position clusters return no significant features**. The
   permutation statistic on one position is a single value; the descriptive
   ranking is the only signal available.
2. **Hotspots and SAE features both track domains**. This recovers biology
   that sequence or structure annotation alone would also give. The
   SAE-specific value is *which specific features* light up — the
   sequence/structure prior doesn't tell you that. Pair with
   `tooluniverse-sae-dms-global-validation` so the DMS effect is
   load-bearing.
3. **Feature labels are interpretive hints, not annotations**. The
   `ESM_describe_sae_feature` category is derived from how the feature
   activates across UniRef90, not from per-protein expert curation. A
   feature labeled "Catalytic function" *tends* to fire on catalytic
   residues across proteins — treat as a hypothesis for this protein.
4. **Permutation null pool size matters**. With < 50 DMS positions total
   the permutation distribution is coarse and p-values are inflated.
5. **License**: SAE outputs from Forge are non-commercial / academic per
   the Cambrian Inference Clickthrough License.

---

## Cross-references

| Skill / Tool | Why |
|---|---|
| `tooluniverse-sae-mutant-tensor-build` | Upstream: SAE tensor |
| `tooluniverse-mavedb-dms-retrieval` | Upstream: DMS effect matrix |
| `tooluniverse-sae-dms-global-validation` | Prerequisite: confirms SAE responds at all |
| `ESM_describe_sae_feature` | Atomic labeling tool used in Step 5 |
| `tooluniverse-protein-structural-annotation-pdb` | Step 6: structural prior to read against |
| `tooluniverse-annotated-dms-heatmap` | Downstream: visualize the callouts |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/sae_hotspot_feature_enrichment.md`
Reference scripts: `dms_analysis/scripts/08_validation2_hotspot_enrichment.py`, `09_validation2_descriptive.py`, `10_validation2_plot_callouts.py`
