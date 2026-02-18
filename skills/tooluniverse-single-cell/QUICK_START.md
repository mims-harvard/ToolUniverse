# Quick Start: Single-Cell Genomics Analysis

## Prerequisites

```bash
pip install scanpy anndata leidenalg umap-learn harmonypy gseapy pandas numpy scipy scikit-learn statsmodels pydeseq2
```

## Documentation Structure

This Quick Start provides minimal examples to get started. For detailed workflows:

- **SKILL.md** - High-level overview, decision trees, BixBench patterns
- **references/scanpy_workflow.md** - Complete pipeline (QC → clustering → DE)
- **references/cell_communication.md** - L-R interactions, OmniPath integration
- **references/clustering_guide.md** - Leiden, hierarchical, bootstrap consensus
- **references/marker_identification.md** - Cell type annotation
- **references/troubleshooting.md** - Common errors and solutions
- **scripts/** - Utility scripts (qc_metrics.py, normalize_data.py, find_markers.py)

---

## Example 1: Load and Inspect scRNA-seq Data

### Python SDK

```python
import scanpy as sc
import pandas as pd
import numpy as np

# Load h5ad file
adata = sc.read_h5ad("data.h5ad")
print(f"Shape: {adata.n_obs} cells x {adata.n_vars} genes")
print(f"Obs columns: {list(adata.obs.columns)}")
print(f"Var columns: {list(adata.var.columns)}")

# Load CSV and convert to AnnData
import anndata as ad
df = pd.read_csv("counts.csv", index_col=0)
# If genes are rows, transpose
if df.shape[0] > df.shape[1] * 5:
    df = df.T
adata = ad.AnnData(df)
```

### MCP (Conversational)

```
User: Load the h5ad file in the data folder and tell me what cell types are present.

Claude: [Uses sc.read_h5ad(), inspects adata.obs columns, reports cell types]
```

**See also**: references/scanpy_workflow.md "Data Loading"

---

## Example 2: Per-Cell-Type Differential Expression (bix-33 pattern)

### Python SDK

```python
import scanpy as sc

# Load data
adata = sc.read_h5ad("pbmc_treatment.h5ad")

# Normalize if raw counts
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# DE per cell type between treatment and control
cell_types = adata.obs['cell_type'].unique()
de_results = {}

for ct in cell_types:
    adata_ct = adata[adata.obs['cell_type'] == ct].copy()
    n_treat = (adata_ct.obs['condition'] == 'treatment').sum()
    n_ctrl = (adata_ct.obs['condition'] == 'control').sum()
    if n_treat < 3 or n_ctrl < 3:
        continue

    sc.tl.rank_genes_groups(adata_ct, groupby='condition',
                             groups=['treatment'], reference='control',
                             method='wilcoxon')
    df = sc.get.rank_genes_groups_df(adata_ct, group='treatment')
    n_sig = (df['pvals_adj'] < 0.05).sum()
    de_results[ct] = {'n_sig': n_sig, 'results': df}
    print(f"{ct}: {n_sig} significant DEGs")

# Which cell type has most DEGs?
top_ct = max(de_results, key=lambda x: de_results[x]['n_sig'])
print(f"Most DEGs: {top_ct} ({de_results[top_ct]['n_sig']})")
```

### MCP (Conversational)

```
User: Which immune cell type has the highest number of significantly
differentially expressed genes after AAV9 mini-dystrophin treatment?

Claude: [Loads h5ad, runs per-cell-type DE, identifies CD14 Monocytes]
```

**See also**: SKILL.md "Pattern 1: Per-Cell-Type Differential Expression"

---

## Example 3: Gene Length vs Expression Correlation (bix-22 pattern)

### Python SDK

```python
import scanpy as sc
import pandas as pd
import numpy as np
from scipy import stats
from scipy.sparse import issparse

# Load expression data
adata = sc.read_h5ad("immune_cells.h5ad")

# Load gene annotations (gene length, biotype)
gene_info = pd.read_csv("gene_annotations.tsv", sep='\t', index_col=0)
common = adata.var_names.intersection(gene_info.index)
adata = adata[:, common].copy()
adata.var['gene_length'] = gene_info.loc[common, 'gene_length']
adata.var['gene_type'] = gene_info.loc[common, 'gene_type']

# Filter to protein-coding genes
mask = adata.var['gene_type'] == 'protein_coding'
adata_pc = adata[:, mask].copy()

# Per-cell-type correlation
cell_types = adata_pc.obs['cell_type'].unique()
for ct in cell_types:
    adata_ct = adata_pc[adata_pc.obs['cell_type'] == ct]
    X = adata_ct.X.toarray() if issparse(adata_ct.X) else adata_ct.X
    mean_expr = np.mean(X, axis=0)
    gene_lengths = adata_ct.var['gene_length'].values

    valid = ~np.isnan(gene_lengths) & ~np.isnan(mean_expr)
    r, p = stats.pearsonr(gene_lengths[valid], mean_expr[valid])
    print(f"{ct}: r = {r:.6f}, p = {p:.2e}")
```

**See also**: SKILL.md "Pattern 2: Gene Property vs Expression Correlation"

---

## Example 4: PCA on Expression Matrix (bix-27 pattern)

### Python SDK

```python
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA

# Load expression matrix
df = pd.read_csv("expression_matrix.csv", index_col=0)

# Orient: samples as rows, genes as columns
if df.shape[0] > df.shape[1] * 5:
    df = df.T

# Log10 transform with pseudocount
X = np.log10(df.values + 1)

# Run PCA
n_components = min(X.shape[0], X.shape[1])
pca = PCA(n_components=n_components)
pca.fit(X)

# Variance explained by PC1
print(f"PC1: {pca.explained_variance_ratio_[0]*100:.2f}% variance")
print(f"Cumulative (10 PCs): {sum(pca.explained_variance_ratio_[:10])*100:.2f}%")
```

**See also**: references/clustering_guide.md "PCA for Clustering"

---

## Example 5: Statistical Comparison of Cell Types (bix-31 pattern)

### Python SDK

```python
from scipy import stats

# After running DE per cell type (see Example 2):
# Compare LFCs between CD4/CD8 and other cell types

# Get LFCs for CD4/CD8 cells (combined)
cd4_cd8_lfc = de_results_cd4_cd8['all']['log2FoldChange'].values
other_lfc = de_results_other['all']['log2FoldChange'].values

# Two-sample t-test
t_stat, p_val = stats.ttest_ind(cd4_cd8_lfc, other_lfc)
print(f"t-statistic: {t_stat:.2f}")
print(f"p-value: {p_val:.4e}")
```

**See also**: SKILL.md "Pattern 4: Statistical Comparison Between Cell Types"

---

## Example 6: ANOVA of miRNA Expression Across Cell Types (bix-36 pattern)

### Python SDK

```python
import pandas as pd
import numpy as np
from scipy import stats

# Load miRNA expression data
df = pd.read_csv("mirna_expression.csv", index_col=0)
meta = pd.read_csv("metadata.csv", index_col=0)

# Exclude PBMCs
meta_filtered = meta[meta['cell_type'] != 'PBMC']
df_filtered = df[meta_filtered.index]

# Per-cell-type mean expression
cell_types = meta_filtered['cell_type'].unique()
groups = {}
for ct in cell_types:
    samples = meta_filtered[meta_filtered['cell_type'] == ct].index
    groups[ct] = df_filtered[samples].values.flatten()

# One-way ANOVA
f_stat, p_val = stats.f_oneway(*groups.values())
print(f"F-statistic: {f_stat:.4f}")
print(f"p-value: {p_val:.4e}")
```

**See also**: SKILL.md "Pattern 5: ANOVA Across Cell Types"

---

## Example 7: Full scRNA-seq Pipeline

### Python SDK

```python
import scanpy as sc

# Load raw data
adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")

# QC
adata.var['mt'] = adata.var_names.str.startswith('MT-')
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
adata = adata[adata.obs['pct_counts_mt'] < 20].copy()
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)

# Normalize
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
adata.raw = adata.copy()

# HVG + PCA
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, n_comps=50)

# Cluster
sc.pp.neighbors(adata, n_pcs=30)
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)

# Marker genes
sc.tl.rank_genes_groups(adata, groupby='leiden', method='wilcoxon')
marker_df = sc.get.rank_genes_groups_df(adata, group='0')
print(marker_df.head(10))
```

**See also**: references/scanpy_workflow.md "Complete Pipeline"

---

## Example 8: Batch Correction with Harmony

### Python SDK

```python
import scanpy as sc
import harmonypy

# After PCA
adata = sc.read_h5ad("multi_batch.h5ad")
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, n_comps=50)

# Harmony
ho = harmonypy.run_harmony(adata.obsm['X_pca'][:, :30], adata.obs, 'batch')
adata.obsm['X_pca_harmony'] = ho.Z_corr.T

# Re-cluster on corrected PCs
sc.pp.neighbors(adata, use_rep='X_pca_harmony')
sc.tl.leiden(adata, resolution=0.5)
sc.tl.umap(adata)
```

**See also**: references/scanpy_workflow.md "Batch Correction with Harmony"

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: scanpy` | `pip install scanpy` |
| `ModuleNotFoundError: leidenalg` | `pip install leidenalg` (needed for Leiden clustering) |
| Sparse matrix errors | Use `.toarray()` to convert: `X = adata.X.toarray() if issparse(adata.X) else adata.X` |
| Gene names don't match | Check if names are Ensembl IDs vs symbols; use MyGene for conversion |
| Memory error with large datasets | Use `sc.pp.highly_variable_genes()` to reduce features; subsample cells |
| Orientation wrong | Check: more genes than samples? If `shape[0] >> shape[1]`, transpose |
| NaN in correlation | Filter with `valid = ~np.isnan(x) & ~np.isnan(y)` before computing |
| Too few cells per group | Need >= 3 cells per condition per cell type for DE |

---

## Tool Parameter Quick Reference

| Tool | Key Parameter | Type | Note |
|------|--------------|------|------|
| `HPA_search_genes_by_query` | `query` | string | Search for gene markers |
| `HPA_get_rna_expression_in_specific_tissues` | `ensembl_id`, `tissue_name` | string, string | Tissue-specific expression |
| `MyGene_query_genes` | `query` | string | Gene info lookup |
| `MyGene_batch_query` | `gene_ids` | list | Batch gene info |
| `PANTHER_enrichment` | `gene_list`, `organism`, `annotation_dataset` | comma-string, int, string | Pathway enrichment |
| `STRING_functional_enrichment` | `protein_ids`, `species` | list, int (9606) | Functional enrichment |

---

## Next Steps

After initial analysis:
1. **Deeper DE**: Use `tooluniverse-rnaseq-deseq2` for pseudo-bulk DESeq2
2. **Pathway analysis**: Use `tooluniverse-gene-enrichment` for comprehensive enrichment
3. **Gene function**: Use `tooluniverse-disease-research` for individual gene deep-dives
4. **Network analysis**: Use `tooluniverse-network-pharmacology` for gene interaction networks
