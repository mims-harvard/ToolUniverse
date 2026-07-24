# Complete Scanpy Workflow

Complete reference for single-cell RNA-seq analysis using scanpy, from raw counts to annotated cell types.

---

## Phase 1: Data Loading and Validation

### Load h5ad Files
```python
import scanpy as sc
adata = sc.read_h5ad("data.h5ad")
print(f"Shape: {adata.n_obs} cells x {adata.n_vars} genes")
print(f"Obs columns: {list(adata.obs.columns)}")
print(f"Var columns: {list(adata.var.columns)}")
```

### Load 10X Files
```python
# From directory
adata = sc.read_10x_mtx("filtered_gene_bc_matrices/hg19/")

# From HDF5
adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")
```

### Load CSV/TSV and Convert to AnnData
```python
import anndata as ad
import pandas as pd

df = pd.read_csv("counts.csv", index_col=0)

# Check orientation (genes vs cells)
if df.shape[0] > df.shape[1] * 5:
    print("Transposing: genes were rows")
    df = df.T

adata = ad.AnnData(df)
```

### Attach Metadata
```python
meta = pd.read_csv("metadata.csv", index_col=0, sep='\t')

# Align indices
common = adata.obs_names.intersection(meta.index)
adata = adata[common].copy()

for col in meta.columns:
    adata.obs[col] = meta.loc[common, col]
```

### Attach Gene Annotations
```python
gene_info = pd.read_csv("gene_info.tsv", sep='\t', index_col=0)

common_genes = adata.var_names.intersection(gene_info.index)

for col in ['gene_length', 'gene_type', 'chromosome']:
    if col in gene_info.columns:
        adata.var[col] = gene_info.loc[adata.var_names, col]
```

---

## Phase 2: Quality Control

### Calculate QC Metrics
```python
# Identify mitochondrial genes
adata.var['mt'] = adata.var_names.str.startswith(('MT-', 'mt-'))

# Calculate metrics
sc.pp.calculate_qc_metrics(
    adata, qc_vars=['mt'],
    percent_top=None,
    log1p=False,
    inplace=True
)

# Available metrics:
# - total_counts: Total UMI counts per cell
# - n_genes_by_counts: Number of genes expressed per cell
# - pct_counts_mt: Percentage of counts in mitochondrial genes
```

### Filter Cells
```python
n_before = adata.n_obs

# Minimum genes per cell
sc.pp.filter_cells(adata, min_genes=200)

# Maximum mitochondrial percentage
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()

# Optional: Remove doublets by gene count
# adata = adata[adata.obs['n_genes_by_counts'] < 5000].copy()

# Optional: Minimum UMI counts
# sc.pp.filter_cells(adata, min_counts=500)

n_after = adata.n_obs
print(f"Filtered: {n_before} → {n_after} cells ({n_before - n_after} removed)")
```

### Filter Genes
```python
# Minimum cells per gene (remove rare genes)
sc.pp.filter_genes(adata, min_cells=3)

print(f"After gene filtering: {adata.n_vars} genes")
```

### Doublet Detection (Optional)
```python
# Using scrublet via scanpy
sc.external.pp.scrublet(adata, expected_doublet_rate=0.06)

n_doublets = adata.obs['predicted_doublet'].sum()
print(f"Detected {n_doublets} doublets ({n_doublets/adata.n_obs*100:.1f}%)")

# Remove doublets
adata = adata[~adata.obs['predicted_doublet']].copy()
```

---

## Phase 3: Normalization and Scaling

### Store Raw Counts
```python
# Important: Store raw counts before normalization
adata.raw = adata.copy()
```

### Library-Size Normalization
```python
# Normalize each cell to 10,000 total counts
sc.pp.normalize_total(adata, target_sum=1e4)
```

### Log Transformation
```python
# Natural log (log1p = log(x + 1))
sc.pp.log1p(adata)
```

### Highly Variable Genes
```python
# Find top variable genes
sc.pp.highly_variable_genes(
    adata,
    n_top_genes=2000,
    flavor='seurat_v3'  # Use 'seurat' if already log-transformed
)

print(f"Highly variable genes: {adata.var['highly_variable'].sum()}")
```

### Scale Data
```python
# Z-score scaling
sc.pp.scale(adata, max_value=10)
```

---

## Phase 4: Dimensionality Reduction

### PCA
```python
# Run PCA on highly variable genes
sc.tl.pca(adata, n_comps=50, use_highly_variable=True)

# Variance explained
var_ratio = adata.uns['pca']['variance_ratio']
print(f"PC1: {var_ratio[0]*100:.2f}% variance")
print(f"Top 10 PCs: {sum(var_ratio[:10])*100:.2f}% variance")

# PC coordinates: adata.obsm['X_pca']
# PC loadings: adata.varm['PCs']
```

### UMAP
```python
# Compute neighbors first
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)

# Run UMAP
sc.tl.umap(adata)

# UMAP coordinates: adata.obsm['X_umap']
```

### t-SNE (Alternative)
```python
sc.tl.tsne(adata, n_pcs=30)
# t-SNE coordinates: adata.obsm['X_tsne']
```

---

## Phase 5: Clustering

### Leiden Clustering (Recommended)
```python
# Build neighbor graph (if not done for UMAP)
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=30)

# Leiden clustering
sc.tl.leiden(adata, resolution=0.5, random_state=0)

n_clusters = adata.obs['leiden'].nunique()
print(f"Leiden clustering: {n_clusters} clusters")
```

### Louvain Clustering (Alternative)
```python
sc.tl.louvain(adata, resolution=0.5, random_state=0)
```

### Resolution Parameter
- Higher resolution = More clusters
- Typical range: 0.3 - 1.5
- Start with 0.5, adjust based on biological expectations

---

## Phase 6: Marker Gene Identification

### Find Marker Genes for Each Cluster
```python
# Run DE test for all clusters
sc.tl.rank_genes_groups(
    adata,
    groupby='leiden',
    method='wilcoxon',  # or 't-test', 'logreg'
    n_genes=100,
    corr_method='benjamini-hochberg'
)

# Get results for cluster 0
markers_0 = sc.get.rank_genes_groups_df(adata, group='0')
print(markers_0.head(10))

# Top marker genes per cluster
sc.pl.rank_genes_groups(adata, n_genes=5, sharey=False)
```

---

## Phase 7: Cell Type Annotation

### Marker-Based Annotation
```python
# Known markers
marker_genes = {
    'T cells': ['CD3D', 'CD3E', 'CD8A', 'CD4'],
    'B cells': ['CD19', 'MS4A1', 'CD79A'],
    'Monocytes': ['CD14', 'LYZ', 'S100A9'],
    'NK cells': ['NKG7', 'GNLY', 'KLRB1'],
    'Dendritic cells': ['FCER1A', 'CD1C'],
}

# Score each cluster
from scipy.sparse import issparse
X = adata.X.toarray() if issparse(adata.X) else adata.X
expr_df = pd.DataFrame(X, index=adata.obs_names, columns=adata.var_names)

cluster_scores = {}
for ct, markers in marker_genes.items():
    available_markers = [m for m in markers if m in adata.var_names]
    if available_markers:
        scores = expr_df[available_markers].mean(axis=1)
        cluster_scores[ct] = scores.groupby(adata.obs['leiden']).mean()

# Assign cell types
score_df = pd.DataFrame(cluster_scores)
assignments = score_df.idxmax(axis=1)
adata.obs['cell_type'] = adata.obs['leiden'].map(assignments)
```

### Use ToolUniverse for Marker Discovery
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

# Search HPA for tissue-specific markers
result = tu.tools.HPA_search_genes_by_query(
    query="T cell marker blood"
)
```

---

## Phase 8: Differential Expression Analysis

### Per-Cell-Type DE Between Conditions
```python
cell_types = adata.obs['cell_type'].unique()
de_results = {}

for ct in cell_types:
    # Subset to cell type
    adata_ct = adata[adata.obs['cell_type'] == ct].copy()

    # Check sufficient cells
    n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
    n_ctrl = (adata_ct.obs['condition'] == 'control').sum()

    if n_treat < 3 or n_ctrl < 3:
        print(f"{ct}: Skipped (insufficient cells)")
        continue

    # Run DE
    sc.tl.rank_genes_groups(
        adata_ct,
        groupby='condition',
        groups=['treatment'],
        reference='control',
        method='wilcoxon',
        n_genes=adata_ct.n_vars
    )

    # Get results
    df = sc.get.rank_genes_groups_df(adata_ct, group='treatment')

    # Filter significant
    sig = df[(df['pvals_adj'] < 0.05) & (df['logfoldchanges'].abs() > 0.5)]

    de_results[ct] = {
        'all': df,
        'significant': sig,
        'n_sig': len(sig),
        'n_up': (sig['logfoldchanges'] > 0).sum(),
        'n_down': (sig['logfoldchanges'] < 0).sum(),
    }

    print(f"{ct}: {len(sig)} DEGs ({de_results[ct]['n_up']} up, {de_results[ct]['n_down']} down)")
```

---

## Phase 9: Batch Correction with Harmony

```python
import harmonypy

# After PCA
sc.tl.pca(adata, n_comps=50)

# Run Harmony
ho = harmonypy.run_harmony(
    adata.obsm['X_pca'][:, :30],  # Use first 30 PCs
    adata.obs,
    'batch',  # Batch column name
    random_state=0
)

# Store corrected PCs
adata.obsm['X_pca_harmony'] = ho.Z_corr.T

# Re-compute neighbors and cluster on corrected PCs
sc.pp.neighbors(adata, use_rep='X_pca_harmony', n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)
```

---

## Complete Pipeline Example

```python
import scanpy as sc

# 1. Load
adata = sc.read_10x_h5("data.h5")

# 2. QC
adata.var['mt'] = adata.var_names.str.startswith('MT-')
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)

# 3. Normalize
adata.raw = adata.copy()
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# 4. HVG + Scale
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pp.scale(adata, max_value=10)

# 5. PCA
sc.tl.pca(adata, n_comps=50)

# 6. Cluster
sc.pp.neighbors(adata, n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)

# 7. Markers
sc.tl.rank_genes_groups(adata, groupby='leiden', method='wilcoxon')

# 8. Annotate (manual step)
# 9. DE analysis (per cell type, if conditions present)

# Save
adata.write_h5ad("processed.h5ad")
```

---

## Tips and Best Practices

1. **Always store raw counts** before normalization (`adata.raw = adata.copy()`)
2. **QC thresholds** depend on dataset:
   - min_genes: 200-500
   - pct_counts_mt: 10-20%
   - max_genes: 5000-7000 (doublet filter)
3. **Highly variable genes**: 2000-3000 for most datasets
4. **PCA components**: 30-50 sufficient for most analyses
5. **Resolution tuning**: Start with 0.5, increase for finer clusters
6. **Batch correction**: Use Harmony for multiple batches/samples
7. **DE method**: Wilcoxon (default) good for most cases; t-test faster
8. **Statistical power**: Need >= 3 cells per condition per cell type

---

## See Also

- **clustering_guide.md** - Advanced clustering methods
- **marker_identification.md** - Cell type annotation strategies
- **troubleshooting.md** - Common errors and solutions
