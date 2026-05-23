---
name: tooluniverse-annotated-dms-heatmap
description: "Visualize a DMS effect matrix (substitutions × positions) as a heatmap aligned to the protein sequence and to a structural annotation track (interface / ligand-pocket residue colouring, core/surface bars, secondary-structure ribbon). Optional per-hotspot SAE-feature callouts above the heatmap. The standard 'Fig 1-style' DMS panel."
disable-model-invocation: true
---

# Annotated DMS heatmap

Visualize a deep mutational scanning (DMS) effect matrix as a heatmap
aligned to the sequence and to a structural annotation track. Optional
per-hotspot SAE-feature callouts above the heatmap. This is the standard
"Fig 1-style" DMS panel — the figure that ties hotspot SAE callouts to the
biology of the protein.

**Provenance**: Workflow adapted from `dms_analysis/skills/annotated_dms_heatmap.md`
and reference script `10_validation2_plot_callouts.py` in
[ada-f/esmc_sae](https://github.com/ada-f/esmc_sae) (Ada Fang, Marinka
Zitnik lab).

---

## When to use this skill

- Final figure for a DMS × SAE analysis manuscript or report
- Communicating which positions are most disrupted, what biology they
  correspond to, and which SAE features the disruption is concentrated in
- Reproducing a published DMS panel with your own analysis on top

**Not for**:
- Interactive exploration — use a Jupyter notebook with the raw tensor
- Per-variant lookup — use the table outputs from upstream skills

---

## Required inputs

| Input | Source | Notes |
|---|---|---|
| `dms_matrix` shape `(20, n_positions)` | `tooluniverse-mavedb-dms-retrieval` | NaN for unmeasured |
| `amino_acid_order` | same | row order, e.g. `"ACDEFGHIKLMNPQRSTVWY"` |
| `positions` | same | 1-based canonical residue numbers |
| `sequence` | string, 1-letter | on the same numbering as columns |
| `annotation_table` | `tooluniverse-protein-structural-annotation-pdb` | same numbering |
| `colour_scale` | matplotlib cmap or limits | diverging, centred at 0 for ΔΔG |

Optional:
- `callouts`: list of `{cluster_positions, label_lines}` from
  `tooluniverse-sae-dms-hotspot-features`
- `vlim`: symmetric colour limits, e.g. ±3 for ΔΔG in kcal/mol

---

## Prerequisites

```bash
pip install matplotlib  # bundled in the [visualization] extra
```

---

## Workflow

### Step 1: Align everything to one position axis

Heatmap column `p`, sequence letter `p`, every annotation bar covering
residue `p` — all share `x = p`. **This is the single thing to get right**.
Verify with a landmark before drawing:

```python
# Spot-check: sequence letter under a known column matches expected
landmark_col = positions.index(12)  # column for position 12
expected = "G"  # KRAS G12
assert sequence[landmark_col] == expected, f"alignment broken at col {landmark_col}"
```

If you've cross-joined two coordinate systems (MaveDB positions ↔ PDB
positions ↔ UniProt positions) and any join was silently off-by-N, the
whole figure is wrong. Verify here.

### Step 2: Heatmap

```python
import matplotlib.pyplot as plt
import numpy as np

vlim = max(abs(np.nanmin(dms_matrix)), abs(np.nanmax(dms_matrix)))

fig, axes = plt.subplots(
    nrows=4, ncols=1, figsize=(max(8, 0.15 * len(positions)), 6),
    gridspec_kw={"height_ratios": [0.5, 4, 0.3, 0.5]}, sharex=True
)
ax_callouts, ax_heat, ax_seq, ax_anno = axes

# Heatmap — symmetric diverging
im = ax_heat.imshow(
    dms_matrix, aspect="auto", cmap="RdBu_r",
    vmin=-vlim, vmax=vlim,
    extent=(0, len(positions), 20, 0),
)
ax_heat.set_yticks(np.arange(20) + 0.5)
ax_heat.set_yticklabels(list(amino_acid_order))
ax_heat.set_ylabel("Substitution")
```

**Distinguish three cell kinds**:
- Real measurement → coloured
- WT cell (position p, alt_aa = ref_aa[p-1]) → mark with a short dash, set
  to colour-scale centre (NOT "missing")
- Genuinely missing → render as a distinct colour (e.g. light grey)

```python
# Mark WT cells
for col, p in enumerate(positions):
    wt_aa = sequence[col]
    if wt_aa in amino_acid_order:
        row = amino_acid_order.index(wt_aa)
        ax_heat.add_patch(plt.Rectangle((col, row), 1, 1,
                                        fill=False, edgecolor='black',
                                        linewidth=0.5))
```

### Step 3: Sequence strip

```python
ax_seq.set_xlim(0, len(positions))
ax_seq.set_ylim(0, 1)
ax_seq.set_yticks([])
for col, letter in enumerate(sequence):
    ax_seq.text(col + 0.5, 0.5, letter, ha="center", va="center",
                family="monospace", fontsize=8)
ax_seq.set_xticks([])
```

### Step 4: Annotation track

```python
# Map annotation_table to per-column arrays
anno_by_pos = {a["position"]: a for a in annotation_table}
region_arr = [anno_by_pos.get(p, {}).get("region", "other") for p in positions]
core_arr = [anno_by_pos.get(p, {}).get("is_core", False) for p in positions]

region_colors = {
    "interface": "#1f77b4",
    "ligand": "#ff7f0e",
    "both": "#2ca02c",
    "other": "#cccccc",
}
for col, region in enumerate(region_arr):
    ax_anno.add_patch(plt.Rectangle((col, 0.5), 1, 0.5,
                                    facecolor=region_colors[region]))
    # Core: filled square below
    if core_arr[col]:
        ax_anno.add_patch(plt.Rectangle((col, 0.0), 1, 0.5,
                                        facecolor="black"))
ax_anno.set_xlim(0, len(positions))
ax_anno.set_ylim(0, 1)
ax_anno.set_yticks([0.25, 0.75])
ax_anno.set_yticklabels(["core", "region"])
ax_anno.set_xticks(np.arange(0, len(positions), max(1, len(positions)//20)) + 0.5)
ax_anno.set_xticklabels([positions[i] for i in range(0, len(positions), max(1, len(positions)//20))])
ax_anno.set_xlabel("Residue position")
```

Put any **legends above the sequence** so they never collide with the bars.

### Step 5: Optional callouts above the heatmap

```python
if callouts:
    for callout in callouts:
        cluster_cols = [positions.index(p) for p in callout["cluster_positions"]]
        c_left, c_right = min(cluster_cols), max(cluster_cols)
        center = (c_left + c_right) / 2
        # Bracket on the heatmap
        ax_heat.plot([c_left, c_right + 1], [0, 0], "k-", lw=2)
        # Box on the callout row with feature labels
        text = "\n".join(callout["label_lines"])
        ax_callouts.text(center, 0.5, text, ha="center", va="center",
                         fontsize=7, bbox=dict(facecolor="white", edgecolor="black"))
        # Leader line
        ax_callouts.plot([center, center], [0, -0.3], "k-", lw=0.5)
ax_callouts.set_xlim(0, len(positions))
ax_callouts.set_ylim(0, 1)
ax_callouts.axis("off")
```

### Step 6: Save

```python
fig.colorbar(im, ax=ax_heat, label="DMS effect")
plt.savefig("dms_annotated_heatmap.png", dpi=200, bbox_inches="tight")
```

---

## Output

A PNG per assay with rows (top → bottom):
1. Optional callout row with per-hotspot SAE feature boxes
2. Heatmap (20 substitutions × n_positions, WT cells boxed)
3. Sequence strip (monospace single letters)
4. Annotation track (region colours + core bars)

---

## Pitfalls

1. **1–2 residue misalignment between heatmap and annotation track** is a
   common error and visually subtle. The landmark check in Step 1 catches
   it; without that check the figure can be silently wrong.
2. **"Wild-type cell" and "not measured" are different states**. Giving
   them the same colour misleads the reader into seeing missing data as
   neutral.
3. **Reproducing a published panel**: verify *its* track alignment before
   treating it as ground truth. Published DMS panels do carry registration
   errors. (The KRAS Fig 1i in the original paper is shifted +2 relative to
   its own sequence — see the upstream `protein_structural_annotations` skill.)
4. **Long proteins compress columns**. For sequences > 300 residues, split
   into multiple horizontal panels (one panel per domain) rather than
   shrinking column width.

---

## Cross-references

| Skill | Why |
|---|---|
| `tooluniverse-mavedb-dms-retrieval` | DMS matrix input |
| `tooluniverse-protein-structural-annotation-pdb` | Annotation track input |
| `tooluniverse-sae-dms-hotspot-features` | Callout content |

---

## References

Source repo: https://github.com/ada-f/esmc_sae (Ada Fang, Mzitnik Lab)
Reference skill: `dms_analysis/skills/annotated_dms_heatmap.md`
Reference script: `dms_analysis/scripts/10_validation2_plot_callouts.py`
