---
name: tooluniverse-dms-hotspot-mechanism-interpretation
description: "Given a DMS hotspot (a residue or short cluster where many substitutions disrupt function), explain WHY that residue is functionally critical by combining multiple lines of evidence: SAE feature drops, structural context (binding interface, ligand pocket, core, secondary structure), known UniProt features (active sites, binding sites, PTM sites, disulfides), and evolutionary conservation. The output is a per-hotspot mechanism call: catalytic / ligand-binding / interface / structural-core / PTM / regulatory / unknown."
disable-model-invocation: true
---

# DMS hotspot mechanism interpretation

The core user question: **"This DMS map has a hotspot at residue X — *why* is X
critical?"**

Answering needs more than one source: a hotspot in the ligand pocket means
something different from a hotspot in a catalytic triad, an interface, the
hydrophobic core, or a PTM sequon. This skill synthesizes evidence from
multiple TU tools to call a mechanism.

**Provenance**: Hotspot detection + permutation statistics methodology adapted
from `dms_analysis/skills/sae_hotspot_feature_enrichment.md` in
[ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka Zitnik
lab). The multi-evidence synthesis layer (structural + SAE + UniProt) is added
here.

---

## When to use this skill

- You have a DMS map and want to interpret what your top hotspots represent
  biologically
- You're writing the methods/discussion section of a DMS paper and need
  mechanistic claims per hotspot
- You're comparing DMS hotspots across orthologs and need a per-hotspot
  category to align by

**Not for**:
- Validating a *predictor* against DMS — use
  `tooluniverse-variant-predictor-dms-benchmarking`
- Single-variant interpretation when you have one variant, no DMS — use
  `tooluniverse-protein-sae-variant-interpretation` or
  `tooluniverse-protein-lof-mechanism`
- Finding hotspots in the first place from raw DMS — that's just the top-K
  positions by max effect; this skill takes hotspots as input

---

## Required inputs

| Input | Source | Notes |
|---|---|---|
| DMS effect matrix `(20, n_positions)` | `tooluniverse-mavedb-dms-retrieval` | NaN for unmeasured |
| `disruptive_tail` | DMS retrieval metadata | `"top"` or `"bottom"` |
| Protein metadata | UniProt accession + PDB ID + chain | for the multi-evidence lookups |
| (optional) SAE tensor `(20, n_positions, 16384)` | `ESM_get_sae_features` per mutant | the SAE evidence layer; if absent the skill runs with the other 3 evidence layers |

---

## Workflow

### Step 1: Pick hotspots from the DMS matrix

```python
import numpy as np

# Per-position disruption magnitude
if disruptive_tail == "top":
    dms_per_pos = np.nanmax(dms_matrix, axis=0)   # max destabilization at any allele
elif disruptive_tail == "bottom":
    dms_per_pos = -np.nanmin(dms_matrix, axis=0)  # flip for low-is-bad assays

K = 20
top_positions = sorted(np.argsort(-dms_per_pos)[:K].tolist())

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
print(f"{len(clusters)} hotspot cluster(s): {clusters}")
```

A "cluster" of one is allowed — it just gets less statistical power in the
permutation test, but multi-evidence interpretation still works.

### Step 2: Gather structural evidence per cluster

Annotate the protein structure once, then read fields for each cluster's
positions:

```python
# One-shot structural annotation (cached for the rest of the skill)
struct = Structure_annotate_per_residue(
    pdb_id="6VJJ",                 # pick a structure with the relevant complex
    target_chain="A",
    partner_chains=["B"],          # if there's a binding partner
    ligand_resnames=["GNP", "MG"], # if there's a relevant ligand
    distance_cutoff=5.0,
    include_secondary_structure=True,
)
by_pos = {r["position"]: r for r in struct["data"]["annotations"]}

for cluster in clusters:
    structural_summary = {
        "interface_count": sum(1 for p in cluster if by_pos.get(p, {}).get("region") in ("interface", "both")),
        "ligand_pocket_count": sum(1 for p in cluster if by_pos.get(p, {}).get("region") in ("ligand", "both")),
        "core_count": sum(1 for p in cluster if by_pos.get(p, {}).get("is_core")),
        "ss_elements": [by_pos.get(p, {}).get("ss_element") for p in cluster],
    }
```

### Step 3: Gather UniProt feature evidence per cluster

```python
# UniProt features per position (active sites, binding sites, PTM sites, etc.)
up = UniProt_get_function_by_accession(accession="P01116")
# Parse up["features"] into a per-position lookup
features_by_pos = {}
for feat in up.get("features", []):
    start = int(feat.get("begin", feat.get("position", -1)))
    end = int(feat.get("end", start))
    for p in range(start, end + 1):
        features_by_pos.setdefault(p, []).append({
            "type": feat.get("type"),
            "description": feat.get("description", ""),
        })

for cluster in clusters:
    uniprot_summary = {
        "active_site": [p for p in cluster if any(f["type"] == "Active site" for f in features_by_pos.get(p, []))],
        "binding_site": [p for p in cluster if any(f["type"] == "Binding site" for f in features_by_pos.get(p, []))],
        "modified_residue": [p for p in cluster if any(f["type"] == "Modified residue" for f in features_by_pos.get(p, []))],
        "disulfide_bond": [p for p in cluster if any(f["type"] == "Disulfide bond" for f in features_by_pos.get(p, []))],
        "domain": [f.get("description") for p in cluster for f in features_by_pos.get(p, []) if f.get("type") == "Domain"],
    }
```

### Step 4 (optional, requires SAE tensor): Per-cluster SAE feature ranking

If you have an SAE tensor from `ESM_get_sae_features` runs on this protein's
DMS library, compute which SAE features drop the most at this cluster.

```python
def cluster_sae_features(sae_tensor, wt_vec, cluster_positions, top_n=5):
    """Returns top SAE features by mean drop at cluster, ready for labeling."""
    drops = np.maximum(0.0, wt_vec[None, :, :] - sae_tensor)
    max_drop_per_pos = np.nanmax(drops, axis=0)  # (n_pos, 16384)
    cluster_mean = max_drop_per_pos[cluster_positions].mean(axis=0)
    return np.argsort(-cluster_mean)[:top_n].tolist()

top_features = cluster_sae_features(sae_tensor, wt_vec, cluster_cols, top_n=5)

# Label each via the SAE feature labeler
for f in top_features:
    label = ESM_describe_sae_feature(feature_id=int(f), n_proteins=5)
    print(f"  feature {f}: {label['data'].get('category')} (conf {label['data'].get('confidence')})")
```

The first label call for each feature is slow (~30s, ~10 Forge credits as the
labeler runs SAE on a 10-protein panel); subsequent calls hit cache.

### Step 4-alt: permutation-test the SAE features (optional, more rigorous)

```python
def permutation_pvalues(cluster_positions, max_drop, n_perm=10000, rng=None):
    """Per-feature: is the cluster's mean drop > random equally-sized set?"""
    rng = rng or np.random.default_rng(0)
    n_positions = max_drop.shape[0]
    cluster_size = len(cluster_positions)
    observed = max_drop[cluster_positions].mean(axis=0)
    null_geq = np.zeros(max_drop.shape[1], dtype=np.int32)
    for _ in range(n_perm):
        idx = rng.choice(n_positions, size=cluster_size, replace=False)
        null_geq += (max_drop[idx].mean(axis=0) >= observed).astype(np.int32)
    return (null_geq + 1) / (n_perm + 1)

from statsmodels.stats.multitest import multipletests
p_raw = permutation_pvalues(np.array(cluster_cols), max_drop_per_pos)
_, p_adj, _, _ = multipletests(p_raw, method="fdr_bh")
significant_features = np.where(p_adj < 0.05)[0].tolist()
```

Use the **mean** of `max_drop`, not the max — under this null a maximum-based
statistic returns almost no significant features. Single-position clusters
return no significant features (no statistical power) — fall back to Step 4
descriptive ranking.

### Step 5: Synthesize the mechanism call

For each cluster, combine the 3 (or 4 with SAE) evidence streams:

```python
def call_mechanism(structural, uniprot, sae_labels=None):
    """Return one of: catalytic | ligand-binding | interface |
    structural-core | PTM | regulatory | mixed | unknown."""

    # Direct UniProt evidence wins
    if uniprot["active_site"]:
        return "catalytic"
    if uniprot["binding_site"]:
        return "ligand-binding"
    if uniprot["modified_residue"] and len(uniprot["modified_residue"]) >= len(cluster) // 2:
        return "PTM"

    # Structural evidence
    if structural["ligand_pocket_count"] >= len(cluster) // 2:
        return "ligand-binding"
    if structural["interface_count"] >= len(cluster) // 2:
        return "interface"
    if structural["core_count"] >= len(cluster) // 2:
        return "structural-core"

    # SAE evidence as tiebreaker
    if sae_labels:
        from collections import Counter
        cat_counts = Counter(l for l in sae_labels if l)
        if cat_counts:
            top_cat, n = cat_counts.most_common(1)[0]
            if n >= 2:  # at least 2 of top-5 SAE features agree
                return top_cat  # e.g. "ligand-binding"

    return "unknown"
```

### Step 6: Report

```
Cluster 1 — positions [12, 13]
  Structural: 0/2 interface, 2/2 ligand pocket (GTP), 0/2 core, all in P-loop helix
  UniProt:    Binding site (GTP) at residues 12, 13
              Domain: small GTPase
  SAE top 5:  ligand-binding (×2), secondary-structure (×3)
  → MECHANISM: ligand-binding (GTP P-loop)

Cluster 2 — positions [40, 41]
  Structural: 2/2 interface (chain B = RAF1-RBD)
  UniProt:    no specific annotation
  SAE top 5:  structural-stability (×3), domain (×2)
  → MECHANISM: interface (KRAS-RAF1 binding)
```

---

## Interpretation table — what the mechanism call means downstream

| Mechanism | Implication |
|---|---|
| **catalytic** | Direct enzyme function — mutations abolish activity |
| **ligand-binding** | Substrate / cofactor / ion / nucleotide binding — mutations alter substrate specificity or affinity |
| **interface** | Protein-protein interaction surface — mutations may disrupt complex formation (consider PPI inhibitor design) |
| **structural-core** | Fold stability — mutations destabilize protein (consider rescuing with chaperones; harder to drug) |
| **PTM** | Regulation site (phospho, acetyl, ubiquitin, glycosylation) — mutations alter signaling rather than activity |
| **regulatory** | Allosteric site / autoinhibitory residue — mutations bias conformational equilibrium |
| **mixed** | Multiple evidence types disagree — needs case-by-case analysis |
| **unknown** | No mechanism could be assigned — possibly novel function or wrong reference structure |

---

## Honest limitations

1. **Wrong PDB → wrong call**. If your PDB doesn't include the relevant ligand
   or partner, the structural evidence layer is blind to that mechanism. Pick
   the structure that contains the right complex.
2. **UniProt annotations are sparse for non-model proteins**. Active sites are
   well-curated for canonical enzymes; novel proteins may have no annotated
   features and the skill falls back to structural + SAE only.
3. **Single-position clusters limit statistical evidence**. Descriptive
   ranking still works but permutation p-values can't (n=1).
4. **SAE feature labels are interpretive hints, not ground truth**. Labels
   come from how features activate across UniRef90, not per-protein expert
   curation. Treat "category: ligand-binding" as a hypothesis weight, not a
   proof.
5. **Hotspots ≠ druggable sites**. A catalytic residue is a critical residue
   but not necessarily a good drug target (allosteric pockets often are
   better). This skill explains why a residue is critical, not whether it's a
   good target.
6. **The mechanism call is a synthesis of evidence, not a measurement**.
   Don't quote the category as a fact — quote the evidence and the call as a
   reasoned conclusion.

---

## Cross-references

| Tool / Skill | Role |
|---|---|
| `tooluniverse-mavedb-dms-retrieval` | DMS matrix input |
| `tooluniverse-protein-structural-annotation-pdb` (or `Structure_annotate_per_residue` directly) | Structural evidence |
| `UniProt_get_function_by_accession` | UniProt features (active sites, binding sites, PTMs, disulfides) |
| `ESM_get_sae_features` | SAE tensor for the optional Step 4 |
| `ESM_describe_sae_feature` | Label SAE features in Step 4 |
| `tooluniverse-variant-predictor-dms-benchmarking` | Sibling skill: validate a predictor before trusting its scores |
| `tooluniverse-annotated-dms-heatmap` | Visualize the hotspots + mechanism callouts |
| `alphafold_get_prediction` | pLDDT context if no experimental PDB available |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/sae_hotspot_feature_enrichment.md`
Reference scripts: `dms_analysis/scripts/08_validation2_hotspot_enrichment.py`, `09_validation2_descriptive.py`, `10_validation2_plot_callouts.py`
