---

name: tooluniverse-residue-functional-mechanism-interpretation
description: "Given a set of residues in a protein, explain WHY they are functionally critical by combining structural context (binding interface, ligand pocket, core, secondary structure), UniProt features (active sites, binding sites, PTM sites, disulfides), optional SAE feature evidence, and optional DMS data. Accepts residues from any source: DMS hotspots (top-K by max effect), ClinVar recurrent variants, literature-reported hot regions, evolutionarily conserved positions, or user-curated lists. Returns a per-cluster mechanism call: catalytic / ligand-binding / interface / structural-core / PTM / regulatory / unknown."
---

# Residue functional mechanism interpretation

The core user question: **"Why are these residues functionally critical?"**

Answering needs more than one source: a residue in the ligand pocket means
something different from one in a catalytic triad, an interface, the
hydrophobic core, or a PTM sequon. This skill synthesizes evidence from
multiple TU tools to call a mechanism for each residue (or cluster of
adjacent residues).

The residues can come from **any source** — this skill is agnostic to where
they came from:

| Residue source | Typical call pattern |
|---|---|
| **DMS map hotspots** | Use Step 1 (optional) to detect top-K by max effect, then continue |
| **ClinVar recurrent variants** | Pull recurrent positions from ClinVar, pass directly as `user_provided_positions` |
| **Literature hot regions** | Paste positions from a paper's Fig 1, pass directly |
| **Evolutionarily conserved residues** | Filter by conservation score, pass top-N positions |
| **Druggable site residues** | From a binding-site predictor, pass directly |
| **Clinician's question** | "Why does mutation at R175 keep showing up in tumors?" — pass `[175]` |

---

## When to use this skill

- You have a list of residues (from anywhere) and need to explain *why* they
  matter biologically
- You're writing the methods/discussion section of a paper and need
  mechanistic claims per residue or cluster
- You're comparing residue sets across orthologs and need a per-residue
  category to align by

**Not for**:
- Validating a *predictor* against DMS — use
  `tooluniverse-variant-predictor-dms-validation`
- Single-variant **SAE feature decomposition** when you want to see which
  ESMC features changed — use `tooluniverse-protein-sae-variant-interpretation`
- Single-variant **LoF mechanism synthesis** for one variant in isolation
  — use `tooluniverse-protein-lof-mechanism`

The single-variant skills focus on one mutation's signature; this skill
focuses on *which residues matter and why*.

---

## Required inputs (choose one entry path)

**Path A — Residues supplied directly** (covers ClinVar / literature /
custom positions):

| Input | Notes |
|---|---|
| `user_provided_positions: List[int]` | 1-based canonical residue positions |
| Protein metadata | UniProt accession + PDB ID + chain |
| (optional) DMS matrix | If supplied, used to enrich each cluster with effect-size context |
| (optional) SAE tensor | If supplied, gives SAE feature evidence as a 4th layer |

**Path B — Detect hotspots from a DMS map** (original use case):

| Input | Source | Notes |
|---|---|---|
| DMS effect matrix `(20, n_positions)` | `MaveDB_get_effect_matrix` | NaN for unmeasured |
| `disruptive_tail` | DMS retrieval metadata | `"top"` or `"bottom"` |
| Protein metadata | UniProt accession + PDB ID + chain | for the multi-evidence lookups |
| (optional) SAE evidence | `ESM_get_region_sae_features` for one contiguous cluster (1 Forge call), OR a precomputed full DMS SAE tensor from `ESM_get_sae_features` per mutant | the SAE evidence layer; see Step 4 for which path |

In Path B the skill runs Step 1 to detect hotspots; in Path A it skips Step
1 entirely and goes straight to Step 2 (gather evidence).

---

## Workflow

### Step 0 (MANDATORY if user names specific positions): Premise check

If the user says "explain why residue/cluster X is a hotspot", do NOT take
that as a given. Verify it's actually a hotspot in THIS DMS first — users
import biological knowledge from other contexts that may not match what the
specific assay measured.

```python
# Per-position disruption magnitude (same formula as Step 1)
if disruptive_tail == "top":
    dms_per_pos = np.nanmax(dms_matrix, axis=0)
elif disruptive_tail == "bottom":
    dms_per_pos = -np.nanmin(dms_matrix, axis=0)

# Where do the user-named positions actually rank?
ranks = (-dms_per_pos).argsort().argsort()  # 0 = highest
for user_pos in user_named_positions:
    rank = int(ranks[pos_index[user_pos]])
    pct = 100 * (1 - rank / len(dms_per_pos))
    print(f"  pos {user_pos}: rank {rank+1}/{len(dms_per_pos)}, "
          f"top {pct:.0f}% by max effect")
```

**Decision rule:**
- If named position is in top 25% by max effect → premise confirmed, proceed.
- If named position is in top 50% but not 25% → premise weakly supported;
  proceed but note the rank in your report.
- **If named position is below top 50% → REPORT THIS MISMATCH TRANSPARENTLY**
  at the top of your answer before continuing with the mechanism analysis.

Concrete example: the user asks "why is KRAS G12/G13 a folding hotspot in
this DMS?" The data say G12 ranks 105/187 (top 56%) and G13 ranks 124/187
(top 66%) by max ΔΔG — they are NOT folding hotspots in this AbundancePCA
assay (even though they ARE famous oncogenic positions). The skill's job
is to surface that contradiction up front, then proceed with a mechanism
analysis for those residues (their oncogenic effect is via GTPase
abolishment, not fold disruption — and that's a genuinely useful answer to
the user's actual scientific question, just not the one they literally asked).

### Step 1 (Path B only): Detect hotspots from the DMS matrix

**Skip this step entirely if the user already provided positions (Path A).**
In Path A the residue list IS the input; jump straight to clustering at the
bottom of this section.

```python
import numpy as np

if user_provided_positions:
    # Path A — residues from any source (ClinVar / literature / custom)
    positions_to_analyze = sorted(set(user_provided_positions))
else:
    # Path B — detect from DMS matrix
    if disruptive_tail == "top":
        dms_per_pos = np.nanmax(dms_matrix, axis=0)   # max destabilization at any allele
    elif disruptive_tail == "bottom":
        dms_per_pos = -np.nanmin(dms_matrix, axis=0)  # flip for low-is-bad assays

    K = 20
    positions_to_analyze = sorted(np.argsort(-dms_per_pos)[:K].tolist())

# Chain adjacent positions (gap ≤ 2) into clusters — shared by both paths
clusters = []
current = [positions_to_analyze[0]]
for p in positions_to_analyze[1:]:
    if p - current[-1] <= 2:
        current.append(p)
    else:
        clusters.append(current)
        current = [p]
clusters.append(current)
print(f"{len(clusters)} cluster(s): {clusters}")
```

A "cluster" of one is allowed — it just gets less statistical power in the
permutation test, but multi-evidence interpretation still works.

**Path A workflow contracts** (what's available vs not):
| Evidence layer | Path A (user residues) | Path B (DMS hotspots) |
|---|---|---|
| Structural (Step 2) | ✓ always | ✓ always |
| UniProt features (Step 3) | ✓ always | ✓ always |
| SAE per-feature labels (Step 4, descriptive) | ✓ if SAE tensor supplied | ✓ if SAE tensor supplied |
| SAE permutation test (Step 4-alt) | ✗ — needs DMS-derived `max_drop` baseline; not meaningful for residues with no DMS context | ✓ if SAE tensor supplied |
| DMS effect-size context | ✓ if DMS matrix supplied (enrichment only) | ✓ always |
| Mechanism synthesis (Step 5) | ✓ always | ✓ always |

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

### Step 4 (optional): Per-cluster SAE feature ranking

Two paths depending on whether you already have a full DMS SAE tensor:

**Path A — no precomputed tensor (most cases): use the region tool directly.**
If the cluster is a contiguous range (or you can pad to one), `ESM_get_region_sae_features` aggregates SAE features over the range in a single Forge call:
```python
region = ESM_get_region_sae_features(
    sequence=ref_sequence,
    start_position=min(cluster_positions),
    end_position=max(cluster_positions),
    top_k_features=5,
)
top_features = [f["feature_id"] for f in region["data"]["top_features"]]
```
This is the right default — 1 Forge call vs 20 × cluster-size for the DMS-tensor path. For non-contiguous clusters, run once per contiguous sub-range and union the top-K.

**Path B — you already have a precomputed SAE tensor** from a DMS sweep (e.g. the variant-predictor-dms-validation pipeline left one on disk): compute drops directly without re-calling Forge.
```python
def cluster_sae_features(sae_tensor, wt_vec, cluster_positions, top_n=5):
    """Returns top SAE features by mean drop at cluster, ready for labeling."""
    drops = np.maximum(0.0, wt_vec[None, :, :] - sae_tensor)
    max_drop_per_pos = np.nanmax(drops, axis=0)  # (n_pos, 16384)
    cluster_mean = max_drop_per_pos[cluster_positions].mean(axis=0)
    return np.argsort(-cluster_mean)[:top_n].tolist()

top_features = cluster_sae_features(sae_tensor, wt_vec, cluster_cols, top_n=5)
```

Label each top feature via the SAE feature labeler:
```python
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

### Step 7: Visualize — annotated DMS heatmap with hotspot callouts

The publication-style figure: DMS effect heatmap, sequence strip, structural
annotation track, with per-hotspot mechanism callouts above the heatmap.

**Align everything to one position axis.** Heatmap column `p`, sequence
letter `p`, every annotation bar covering residue `p` — all share `x = p`.
Verify a landmark before drawing:

```python
landmark_col = positions.index(12)  # column for KRAS pos 12
assert sequence[landmark_col] == "G", f"alignment broken at col {landmark_col}"
```

A 1-2 residue misalignment between heatmap and annotation track is a common,
visually subtle error. If you've cross-joined two coordinate systems and any
join was off-by-N, the whole figure is silently wrong. Verify here.

**Heatmap + sequence + annotation track + callouts:**

```python
import matplotlib.pyplot as plt
import numpy as np

vlim = max(abs(np.nanmin(dms_matrix)), abs(np.nanmax(dms_matrix)))

fig, axes = plt.subplots(
    nrows=4, ncols=1, figsize=(max(8, 0.15 * len(positions)), 6),
    gridspec_kw={"height_ratios": [0.5, 4, 0.3, 0.5]}, sharex=True,
)
ax_callouts, ax_heat, ax_seq, ax_anno = axes

# Heatmap — symmetric diverging (RdBu_r); center on 0 for ΔΔG-style data
im = ax_heat.imshow(
    dms_matrix, aspect="auto", cmap="RdBu_r",
    vmin=-vlim, vmax=vlim,
    extent=(0, len(positions), 20, 0),
)
ax_heat.set_yticks(np.arange(20) + 0.5)
ax_heat.set_yticklabels(list(amino_acid_order))
ax_heat.set_ylabel("Substitution")

# Mark WT cells (box, no fill) — distinguish "WT" from "not measured"
for col, p in enumerate(positions):
    wt_aa = sequence[col]
    if wt_aa in amino_acid_order:
        row = amino_acid_order.index(wt_aa)
        ax_heat.add_patch(plt.Rectangle(
            (col, row), 1, 1, fill=False, edgecolor='black', linewidth=0.5,
        ))

# Sequence strip — one monospace letter per column
ax_seq.set_xlim(0, len(positions))
ax_seq.set_ylim(0, 1)
ax_seq.set_yticks([])
for col, letter in enumerate(sequence):
    ax_seq.text(col + 0.5, 0.5, letter, ha="center", va="center",
                family="monospace", fontsize=8)

# Annotation track — region colors (top half) + core bar (bottom half)
anno_by_pos = {a["position"]: a for a in struct["data"]["annotations"]}
region_colors = {"interface": "#1f77b4", "ligand": "#ff7f0e",
                 "both": "#2ca02c", "other": "#cccccc"}
for col, p in enumerate(positions):
    a = anno_by_pos.get(p, {})
    ax_anno.add_patch(plt.Rectangle(
        (col, 0.5), 1, 0.5, facecolor=region_colors.get(a.get("region", "other"), "#cccccc"),
    ))
    if a.get("is_core"):
        ax_anno.add_patch(plt.Rectangle((col, 0.0), 1, 0.5, facecolor="black"))
ax_anno.set_xlim(0, len(positions))
ax_anno.set_ylim(0, 1)
ax_anno.set_yticks([0.25, 0.75])
ax_anno.set_yticklabels(["core", "region"])
ax_anno.set_xlabel("Residue position")

# Callout row — per-hotspot mechanism boxes linked to clusters by brackets
for cluster, mechanism, top_features in hotspot_results:
    cluster_cols = [positions.index(p) for p in cluster if p in positions]
    if not cluster_cols:
        continue
    c_left, c_right = min(cluster_cols), max(cluster_cols)
    center = (c_left + c_right) / 2
    ax_heat.plot([c_left, c_right + 1], [0, 0], "k-", lw=2)
    label_lines = [f"MECHANISM: {mechanism}"] + [f"  {fl}" for fl in top_features[:3]]
    ax_callouts.text(center, 0.5, "\n".join(label_lines),
                     ha="center", va="center", fontsize=7,
                     bbox=dict(facecolor="white", edgecolor="black"))
    ax_callouts.plot([center, center], [0, -0.3], "k-", lw=0.5)
ax_callouts.set_xlim(0, len(positions))
ax_callouts.set_ylim(0, 1)
ax_callouts.axis("off")

fig.colorbar(im, ax=ax_heat, label="DMS effect (ΔΔG kcal/mol)")
plt.savefig("dms_hotspots_annotated.png", dpi=200, bbox_inches="tight")
```

**Three cell-color rules to get right:**
- Real measurement → diverging colour
- WT cell → boxed (the black outline above), value-cell colour = centre
- Not measured → distinct colour (e.g. light grey, not white — white reads
  as "neutral" against the diverging palette)

**Long proteins**: for >300 residues, split into multiple horizontal panels
(one panel per domain) rather than shrinking column width — the per-residue
detail disappears below ~3 pixels per column.

**Reproducing a published panel**: verify *its* track alignment before
treating it as ground truth. Published DMS panels do carry registration
errors (the KRAS Fig 1i in the original paper is shifted +2 relative to its
own sequence — see `tooluniverse-protein-structural-annotation-pdb` pitfalls).

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
| `MaveDB_get_effect_matrix` | DMS matrix input |
| `tooluniverse-protein-structural-annotation-pdb` (or `Structure_annotate_per_residue` directly) | Structural evidence |
| `UniProt_get_function_by_accession` | UniProt features (active sites, binding sites, PTMs, disulfides) |
| `ESM_get_region_sae_features` | Step 4 Path A — aggregate SAE features over a contiguous cluster in 1 Forge call (preferred) |
| `ESM_get_sae_features` | Step 4 Path B — only if you already have a precomputed full DMS SAE tensor |
| `ESM_describe_sae_feature` | Label SAE features in Step 4 |
| `tooluniverse-variant-predictor-dms-validation` | Sibling skill: validate a predictor before trusting its scores |
| (heatmap visualization is now Step 7 of this skill) | annotated DMS panel with per-hotspot callouts |
| `alphafold_get_prediction` | pLDDT context if no experimental PDB available |

