# scRNA-seq Quality Control: Gating Before Downstream Analysis

The QC-gating step decides **which cells (and genes) are real** before any
normalization, clustering, or DE. Bad gating propagates silently: doublets
become fake "intermediate" cell states, ambient RNA makes every cluster express
every marker, and empty droplets inflate cell counts. This doc covers the
per-cell QC metrics, **why** each one flags a problem, how to choose thresholds
from the data (not magic numbers), and the technical artifacts (doublets,
ambient RNA, empty droplets) that per-cell metrics alone do not catch.

> **Honesty note**: every command here runs scanpy/AnnData via Bash/Python.
> If scanpy is not installed, do NOT fabricate numbers. Emit the install plan
> (`pip install scanpy scrublet`) and run `scripts/scrna_qc.py --install-plan`
> to confirm the environment, then stop and report what is missing.

---

## 1. The standard per-cell QC metrics

After `sc.pp.calculate_qc_metrics(adata, qc_vars=['mt','ribo','hb'], ...)`,
each cell (row of `adata.obs`) carries:

| Metric | `.obs` column | What it measures |
|--------|---------------|------------------|
| Genes detected | `n_genes_by_counts` | # genes with >=1 count in the cell |
| Total UMIs | `total_counts` | library size (depth) of the cell |
| Mito fraction | `pct_counts_mt` | % of UMIs from mitochondrial genes |
| Ribo fraction | `pct_counts_ribo` | % of UMIs from ribosomal-protein genes |
| Hemoglobin frac | `pct_counts_hb` | % from hemoglobin genes (RBC contamination) |

Gene flags are set on `adata.var` BEFORE calling `calculate_qc_metrics`:

```python
adata.var['mt']   = adata.var_names.str.upper().str.startswith('MT-')
adata.var['ribo'] = adata.var_names.str.upper().str.startswith(('RPS', 'RPL'))
adata.var['hb']   = adata.var_names.str.upper().str.contains(r'^HB[^P]')  # HBA, HBB...
sc.pp.calculate_qc_metrics(
    adata, qc_vars=['mt', 'ribo', 'hb'],
    percent_top=None,   # REQUIRED for small gene panels (<500), else IndexError
    log1p=False, inplace=True,
)
```

---

## 2. WHY each metric flags a problem (the biology)

- **High `pct_counts_mt` -> dying / stressed cell.** When a cell's membrane
  ruptures during dissociation, cytoplasmic mRNA leaks out but mitochondrial
  transcripts stay trapped inside mitochondria. The surviving captured RNA is
  therefore enriched for mito transcripts. A high mito fraction is a hallmark
  of a broken/apoptotic cell. Typical cutoff 5-20% but **tissue-dependent**:
  cardiomyocytes, hepatocytes, and brown fat are mito-rich at baseline, so a
  10% blanket cutoff would discard healthy cells.

- **Low `n_genes_by_counts` / low `total_counts` -> empty droplet or debris.**
  An empty droplet captures only ambient RNA, so it has few distinct genes and
  low depth. Cells below ~200 genes are usually not real cells.

- **Very high `n_genes_by_counts` / `total_counts` -> doublet.** Two cells in
  one droplet contribute two transcriptomes, roughly doubling both depth and
  gene diversity. Extreme upper-tail cells are doublet-suspicious — but a high
  count alone is weak evidence (a large, transcriptionally active cell also has
  high counts). Use a dedicated doublet caller (Section 4) rather than a hard
  upper gene cap.

- **High `pct_counts_hb` -> red-blood-cell / blood contamination** in a solid
  tissue dissociation. Often filtered in non-blood tissues.

- **`pct_counts_ribo`** is informative but rarely a hard filter: very high ribo
  fraction can indicate low-complexity / stressed cells, and ribo content is
  strongly cell-type-specific (proliferating cells are ribo-high), so flag and
  investigate rather than blindly filter.

---

## 3. Choosing thresholds — distribution-aware, not magic numbers

Hardcoded cutoffs (`mt < 5%`, `n_genes < 2500`) are a starting point, not an
answer. They fail on mito-rich tissues and on shallow vs deep libraries.
Prefer a **data-driven, MAD-based** outlier rule that adapts to the dataset.

### MAD-based outlier detection (recommended)

Flag a cell as an outlier on a metric when it lies more than `nmads` median
absolute deviations from the median. MAD is robust to the very outliers we are
trying to find (unlike mean/SD).

```python
import numpy as np

def is_outlier(adata, metric, nmads=5, upper_only=False):
    M = adata.obs[metric].astype(float)
    med = np.median(M)
    mad = np.median(np.abs(M - med))
    if mad == 0:
        return np.zeros(len(M), dtype=bool)
    lower = med - nmads * mad
    upper = med + nmads * mad
    if upper_only:
        return M > upper
    return (M < lower) | (M > upper)

# Apply on log1p-scaled count metrics (counts are right-skewed)
import scanpy as sc
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], percent_top=None,
                           log1p=True, inplace=True)
adata.obs['outlier'] = (
    is_outlier(adata, 'log1p_total_counts', 5)
    | is_outlier(adata, 'log1p_n_genes_by_counts', 5)
)
# Mito is asymmetric: only the HIGH side is bad. Use a tighter nmads (3) AND a
# biological ceiling so a mito-rich tissue doesn't pass everything.
adata.obs['mt_outlier'] = (
    is_outlier(adata, 'pct_counts_mt', 3, upper_only=True)
    | (adata.obs['pct_counts_mt'] > 20)
)
keep = ~(adata.obs['outlier'] | adata.obs['mt_outlier'])
print(f"Keeping {keep.sum()}/{adata.n_obs} cells")
adata = adata[keep].copy()
```

Guidance:
- `nmads=5` for `total_counts` / `n_genes_by_counts` (catches extreme tails on
  both ends — empty droplets and gross doublets).
- `nmads=3`, upper-only for `pct_counts_mt` (dying cells are one-sided).
- Always pair the MAD rule with a **biological sanity ceiling** on mito
  (e.g. 20% general, higher for mito-rich tissue) so a uniformly degraded
  sample doesn't "pass" just because everything is equally bad.
- **Visualize before committing**: violin/scatter of the three metrics, and a
  `total_counts` vs `pct_counts_mt` scatter (the classic L-shape — dying cells
  sit in the low-count / high-mito corner).

### Always inspect distributions first

```python
sc.pl.violin(adata, ['n_genes_by_counts', 'total_counts', 'pct_counts_mt'],
             jitter=0.4, multi_panel=True)
sc.pl.scatter(adata, x='total_counts', y='pct_counts_mt')
sc.pl.scatter(adata, x='total_counts', y='n_genes_by_counts')
```

---

## 4. Doublet detection (Scrublet / scDblFinder)

Per-cell counts cannot reliably separate a doublet from a large active cell.
Use a simulation-based caller:

```python
# Scrublet via scanpy — run on RAW counts, per-sample (not on merged batches)
sc.pp.scrublet(adata, expected_doublet_rate=0.06)   # scanpy >=1.10
# older scanpy: sc.external.pp.scrublet(adata, expected_doublet_rate=0.06)
n_doub = int(adata.obs['predicted_doublet'].sum())
print(f"{n_doub} predicted doublets ({100*n_doub/adata.n_obs:.1f}%)")
# Often better to FLAG, cluster, then drop — doublets form bridge clusters
adata = adata[~adata.obs['predicted_doublet']].copy()
```

- `expected_doublet_rate` scales with loading: ~0.8% per 1,000 cells recovered
  (10x). 5,000 cells -> ~4%; 10,000 -> ~8%.
- **Run per sample/lane**, before merging — cross-sample "doublets" aren't real.
- **scDblFinder** (R/Bioconductor) is the alternative and often more accurate;
  run via `Rscript` if R is available. Same principle: simulate doublets,
  score each cell, threshold.
- Prefer flag-cluster-drop over hard pre-clustering removal: real doublets
  collapse into recognizable bridge clusters between two parent types.

---

## 5. Ambient RNA awareness (SoupX / DecontX)

Ambient ("soup") RNA is cell-free mRNA released by lysed cells that gets
co-encapsulated into every droplet. Effect: highly expressed genes from one
population bleed into all clusters, smearing marker specificity.

- Per-cell QC metrics do NOT detect ambient contamination — it is a
  count-correction step, not a cell-filtering step.
- **SoupX** (R) estimates the soup profile from empty droplets and subtracts it
  from cell counts. Needs the **raw (unfiltered) + filtered** matrices.
- **DecontX** (celda, R) is a Python-callable-via-R alternative.
- Awareness rule for this skill: if downstream markers look implausibly
  ubiquitous (e.g. hemoglobin in every cluster of a non-blood tissue, or a
  dominant cell type's markers everywhere), suspect ambient RNA and recommend
  SoupX/DecontX correction. Do not silently proceed.

---

## 6. Empty-droplet filtering (knee point / EmptyDrops)

Distinguishing real cells from empty droplets is upstream of per-cell QC.

- **Knee/inflection on the barcode-rank plot**: rank barcodes by total UMI,
  plot rank vs total counts (log-log). The "knee" separates real cells (high
  counts) from the ambient plateau. CellRanger's filtered matrix already
  applies an EmptyDrops-style call.
- **EmptyDrops** (DropletUtils, R) tests each low-count barcode against the
  ambient profile — recovers real small cells that a hard knee cutoff drops.
- If you only have the **filtered** matrix, empty-droplet removal is largely
  already done; still apply `min_genes` (~200) and `min_counts` as a backstop.
- If you have the **raw** matrix, run EmptyDrops (or the knee heuristic) before
  per-cell QC.

```python
# Knee heuristic (when only raw counts available, no DropletUtils)
import numpy as np
tot = np.asarray(adata.X.sum(1)).ravel()
order = np.argsort(tot)[::-1]
ranked = tot[order]
# crude knee: largest drop in log-counts among the top barcodes
log_counts = np.log10(ranked + 1)
knee = np.argmax(np.diff(log_counts[:5000]) * -1) if len(ranked) > 1 else 0
print(f"Approx knee at rank {knee}, threshold ~{ranked[knee]:.0f} UMIs")
```

---

## 7. Recommended order of operations

1. (raw matrix only) Empty-droplet call — EmptyDrops or knee. Skip if you have
   the CellRanger filtered matrix.
2. `calculate_qc_metrics` with `mt`/`ribo`/`hb` flags (`percent_top=None`).
3. Inspect distributions (violin + count-vs-mito scatter).
4. Gate cells: MAD-based outliers on counts/genes + mito (3 MAD upper, capped),
   plus `min_genes ~200`, `min_cells ~3` for genes.
5. Doublet detection (Scrublet/scDblFinder) **per sample** — flag, optionally
   cluster, then drop.
6. (optional) Ambient correction (SoupX/DecontX) if markers look smeared.
7. Proceed to normalization (`references/scanpy_workflow.md` Phase 3+).

**Thresholds are dataset-specific.** Report the cutoffs used and how many cells
each step removed. Never report a filtered cell count without the gates applied.

---

## See also
- `references/scanpy_workflow.md` — Phase 2 inline QC + full pipeline
- `scripts/scrna_qc.py` — run-if-available helper (computes metrics + MAD
  gating from an .h5ad; prints an install plan if scanpy is absent)
- `scripts/qc_metrics.py` — existing filter/scrublet helpers
