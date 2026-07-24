# Troubleshooting Guide

Common errors and solutions for single-cell analysis.

---

## Installation Issues

### `ModuleNotFoundError: scanpy`
```bash
pip install scanpy anndata
```

### `ModuleNotFoundError: leidenalg`
Leiden clustering requires leidenalg package:
```bash
pip install leidenalg
```

### `ModuleNotFoundError: umap`
UMAP requires umap-learn:
```bash
pip install umap-learn
```

### `ModuleNotFoundError: harmonypy`
Batch correction requires Harmony:
```bash
pip install harmonypy
```

---

## Data Loading Issues

### Wrong Matrix Orientation
**Problem**: Genes and samples/cells swapped

**Solution**: Check and transpose
```python
# AnnData expects: cells as rows, genes as columns
if df.shape[0] > df.shape[1] * 5:
    print("Transposing: genes were rows")
    df = df.T
adata = ad.AnnData(df)
```

### Index Mismatch
**Problem**: Metadata doesn't align with expression

**Solution**: Find common indices
```python
common = adata.obs_names.intersection(meta.index)
adata = adata[common].copy()
for col in meta.columns:
    adata.obs[col] = meta.loc[common, col]
```

### Gene Name Mismatch
**Problem**: Gene names in different formats (Ensembl vs Symbol)

**Solution**: Convert IDs
```python
from tooluniverse import ToolUniverse
tu = ToolUniverse()
tu.load_tools()

result = tu.tools.MyGene_batch_query(
    gene_ids=['ENSG00000141510', 'ENSG00000139618'],
    fields='symbol,ensembl.gene'
)
# Extract symbols from result
```

---

## Sparse Matrix Issues

### `TypeError: can't multiply sequence`
**Problem**: Operating on sparse matrix incorrectly

**Solution**: Convert to dense
```python
from scipy.sparse import issparse

X = adata.X.toarray() if issparse(adata.X) else adata.X
```

### Memory Error
**Problem**: Dataset too large to convert to dense

**Solution**: Use sparse operations
```python
# Good: Works on sparse
mean_expr = np.array(adata.X.mean(axis=0)).flatten()

# Bad: Converts entire matrix to dense
# mean_expr = adata.X.toarray().mean(axis=0)
```

---

## QC and Filtering Issues

### No mitochondrial genes found
**Problem**: Gene names don't start with "MT-"

**Solution**: Check prefix
```python
# Check gene name format
print(adata.var_names[:10])

# Try different prefixes
adata.var['mt'] = adata.var_names.str.startswith(('MT-', 'mt-', 'Mt-'))

# Or manually specify
mt_genes = ['MT-CO1', 'MT-CO2', 'MT-ND1', ...]  # Add all MT genes
adata.var['mt'] = adata.var_names.isin(mt_genes)
```

### All cells filtered out
**Problem**: QC thresholds too stringent

**Solution**: Adjust thresholds
```python
# Check distributions first
print(adata.obs['n_genes_by_counts'].describe())
print(adata.obs['pct_counts_mt'].describe())

# Adjust thresholds
sc.pp.filter_cells(adata, min_genes=100)  # Lower from 200
adata = adata[adata.obs['pct_counts_mt'] < 25].copy()  # Higher from 20
```

---

## Clustering Issues

### `ValueError: n_neighbors must be less than n_samples`
**Problem**: Too few cells for neighbor graph

**Solution**: Reduce n_neighbors
```python
# Default is 15, reduce for small datasets
sc.pp.neighbors(adata, n_neighbors=min(15, adata.n_obs - 1))
```

### Only one cluster
**Problem**: Resolution too low

**Solution**: Increase resolution
```python
# Default is 1.0, increase for more clusters
sc.tl.leiden(adata, resolution=1.5)  # or 2.0
```

### Too many clusters
**Problem**: Resolution too high

**Solution**: Decrease resolution
```python
sc.tl.leiden(adata, resolution=0.3)  # or 0.5
```

---

## Differential Expression Issues

### `ValueError: Not enough cells`
**Problem**: < 3 cells per condition

**Solution**: Skip cell types with insufficient cells
```python
n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
n_ctrl = (adata_ct.obs['condition'] == 'control').sum()

if n_treat < 3 or n_ctrl < 3:
    print(f"Skipping {cell_type}: insufficient cells")
    continue
```

### NaN values in results
**Problem**: Gene not expressed or zero variance

**Solution**: Filter before analysis
```python
# Filter lowly expressed genes
sc.pp.filter_genes(adata, min_cells=3)

# Remove genes with zero variance
from sklearn.feature_selection import VarianceThreshold
selector = VarianceThreshold(threshold=0)
X_filtered = selector.fit_transform(X)
```

---

## Statistical Issues

### NaN in correlation
**Problem**: NaN values in data

**Solution**: Filter NaN before computing
```python
valid = ~np.isnan(gene_lengths) & ~np.isnan(mean_expr)
r, p = stats.pearsonr(gene_lengths[valid], mean_expr[valid])
```

### Inf values in log transform
**Problem**: log(0) = -inf

**Solution**: Use log1p or pseudocount
```python
# Good: log1p(x) = log(x + 1)
sc.pp.log1p(adata)

# Good: log(x + pseudocount)
X_log = np.log10(X + 1)

# Bad: log(x) directly
# X_log = np.log10(X)  # Will produce -inf for zeros
```

---

## Performance Issues

### Memory error on large datasets
**Problem**: Dataset too large to fit in memory

**Solution**: Subsample or use HVG
```python
# Option 1: Subsample cells
sc.pp.subsample(adata, fraction=0.5)

# Option 2: Use only highly variable genes
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
adata = adata[:, adata.var['highly_variable']].copy()
```

### Slow clustering
**Problem**: Large dataset (>100k cells)

**Solution**: Reduce PCs or subsample
```python
# Use fewer PCs
sc.pp.neighbors(adata, n_pcs=20)  # instead of 30

# Or subsample for exploration
adata_sample = sc.pp.subsample(adata, fraction=0.1, copy=True)
# Analyze adata_sample first
```

---

## ToolUniverse Integration Issues

### API timeout
**Problem**: ToolUniverse API call times out

**Solution**: Reduce query size or retry
```python
# Split large queries
batch_size = 50
for i in range(0, len(gene_list), batch_size):
    batch = gene_list[i:i+batch_size]
    result = tu.tools.MyGene_batch_query(gene_ids=batch)
```

### ID conversion fails
**Problem**: Gene IDs not recognized

**Solution**: Try different ID types
```python
# Try Ensembl ID
result = tu.tools.MyGene_query_genes(query="ENSG00000141510")

# Try gene symbol
result = tu.tools.MyGene_query_genes(query="TP53")

# Try with species
result = tu.tools.ensembl_lookup_gene(
    gene_id="ENSG00000141510",
    species="homo_sapiens"
)
```

---

## OmniPath / Cell Communication Issues

### No interactions found
**Problem**: Gene names don't match database

**Solution**: Check gene name format
```python
# OmniPath uses gene symbols (not Ensembl IDs)
# Convert first if needed
result = tu.tools.STRING_map_identifiers(
    protein_ids=['ENSG00000141510'],
    species=9606
)
# Use preferredName from result
```

### Empty communication matrix
**Problem**: Expression thresholds too stringent

**Solution**: Reduce thresholds
```python
expressed_lr = filter_expressed_lr_pairs(
    adata, lr_pairs,
    min_frac=0.02,  # Lower from 0.05
    min_mean=0.01   # Lower from 0.05
)
```

---

## Batch Correction Issues

### Harmony not converging
**Problem**: Batch effects too strong

**Solution**: Adjust Harmony parameters
```python
# Increase max iterations
ho = harmonypy.run_harmony(
    adata.obsm['X_pca'],
    adata.obs,
    'batch',
    max_iter_harmony=20  # Increase from default 10
)
```

### Overcorrection
**Problem**: Biological variation removed

**Solution**: Use fewer PCs or weaker correction
```python
# Use fewer PCs
ho = harmonypy.run_harmony(
    adata.obsm['X_pca'][:, :20],  # Instead of :30
    adata.obs,
    'batch'
)
```

---

## File Format Issues

### h5ad version mismatch
**Problem**: "Cannot read h5ad file"

**Solution**: Update anndata
```bash
pip install --upgrade anndata
```

### 10X format changed
**Problem**: Features file instead of genes file

**Solution**: Specify file names
```python
# CellRanger v3+
adata = sc.read_10x_mtx(
    "filtered_feature_bc_matrix/",
    var_names='gene_symbols',
    cache=True
)
```

---

## Tips

1. **Always check data shape**: Cells vs genes orientation
2. **Check for NaN/Inf**: Before statistical tests
3. **Visualize before filtering**: Check QC metric distributions
4. **Save intermediate results**: After time-consuming steps
5. **Use try/except**: For robust per-cell-type analysis

---

## Debugging Checklist

- [ ] Data loaded correctly (check shape, obs, var)
- [ ] Matrix oriented correctly (cells as rows)
- [ ] Metadata aligned with expression data
- [ ] No NaN/Inf values in expression
- [ ] QC thresholds appropriate for dataset
- [ ] Sufficient cells per condition (>= 3)
- [ ] Gene names match between data and annotations
- [ ] Sparse matrix handled correctly
- [ ] Random seed set for reproducibility

---

## See Also

- **scanpy_workflow.md** - Standard pipeline
- **clustering_guide.md** - Clustering troubleshooting
- **cell_communication.md** - OmniPath API issues
